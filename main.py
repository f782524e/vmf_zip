#!/usr/bin/env python
#
# Creates a zip file with all the resources used by a VMF map file.
#
# make sure to
#   pip install vpk
#
# before running!
#
import os
import os.path
import sys
import argparse
import shutil
import vpk

# defaults probably won't work for anyone but me
MAP_PATH = "map.vmf"
CSTRIKE_PATH = "\"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Source\cstrike\""
GMOD_PATH = "\"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\""

# there might be other keywords we need to worry about
VMF_KEYWORDS = [
    '"material"',
    '"texture"',
    '"model"',
]

VMT_KEYWORDS = ['"$bumpmap"']


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f", "--force", action="store_true", help="force overwrite existing files"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument(
        "-m", "--map", help="path to your VMF map file"
    )
    parser.add_argument(
        "-r",
        "--root",
        action="append",
        help=f"path to your resource root, ex: {CSTRIKE_PATH}",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        action="append",
        help=f"IGNORE FILES FOUND IN path to your resource root, ex: {GMOD_PATH}",
    )
    parser.add_argument("-o", "--output", help="Output path")
    args = parser.parse_args()

    if not args.map:
        print("error: no map specified, try passing -m")
        print()
        print("     " + " ".join(sys.argv) + " -m mymap.vmf")
        sys.exit(1)
    
    if not args.root:
        args.root = []
    if not args.ignore:
        args.ignore = []
    
    return args


def recursive_listdir(root):
    for path, dirs, files in os.walk(root):
        for file in files:
            yield os.path.join(path, file)


def find_all_vpk_dir(root):
    for file in recursive_listdir(root):
        if file.endswith("dir.vpk"):
            yield file


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        print(f"[*] created directory {path}")


# assumes f is a file-like object with binary encoding
def parse_resources(f, keywords):
    seen = set()
    while line := f.readline():
        line = line.decode("utf-8")
        if any([m in line for m in keywords]):
            parts = line.split('"')
            texname = parts[3]
            if texname in seen:
                continue
            seen.add(texname.lower())
    return seen


def find_resources_vmf(vmf_path):
    with open(vmf_path, "rb") as f:
        return parse_resources(f, VMF_KEYWORDS)


def find_resources_vmt(vmt_f):
    return parse_resources(vmt_f, VMT_KEYWORDS)


def noext(path):
    return os.path.splitext(path)[0]


def ext(path):
    return os.path.splitext(path)[1]


def is_vmt(path):
    return ext(path) == ".vmt"


def path_matches_resource(path, resource):
    return noext(path.lower()).endswith(noext(resource.lower())) or (
        # sometimes paths have 2 extensions
        noext(noext(path.lower())).endswith(noext(resource.lower()))
    )


def export_path(args, vpk_file, vpk_path, output_path):
    mkdir(output_path)

    pak_fd = vpk_file[vpk_path]

    # split and recombine filepaths to help windows with mixed slashes
    containing_dir = os.path.split(os.path.dirname(vpk_path))
    if containing_dir:
        d = os.path.join(output_path, *containing_dir)
        mkdir(d)

    write_path = os.path.join(output_path, vpk_path)
    if os.path.exists(write_path) and not args.force:
        print()
        print(f"[!] file already exists: {vpk_path}")
        print("     run with -f to overwrite")
        print()
        print("     " + " ".join(sys.argv) + " -f")
        print()
    else:
        with open(os.path.join(output_path, vpk_path), "wb") as f:
            data = pak_fd.read()
            f.write(data)
            if args.verbose:
                print(f"[+] wrote {vpk_path}")


class VPKTable:
    def __init__(self, args):
        self.args = args
        self.ignore_dirs = {}
        all_roots = args.root + args.ignore
        if not all_roots:
            print("error: no roots specified, try passing -r or -i")
            sys.exit(1)
        table = {}
        for root in all_roots:
            vpk_dirs = list(find_all_vpk_dir(root))
            if len(vpk_dirs) == 0:
                print(f"error: could not find any vpk dirs in \"{root}\"")
                sys.exit(1)
            for vpk_dir in vpk_dirs:
                if root in args.ignore:
                    self.ignore_dirs[vpk_dir] = True
                table[vpk_dir] = set()
                if vpk_dir is None:
                    raise Exception(f"error: could not find vpk_dir in {root}")
                else:
                    vpk_path = os.path.join(root, vpk_dir)
                    with vpk.open(vpk_path) as pak:
                        for path in pak:
                            table[vpk_dir].add(path)
        self.table = table

    @property
    def stats(self):
        _s = {}
        _s["vpk_count"] = 0
        _s["path_count"] = 0
        for vpk_path, paths in self.table.items():
            _s["vpk_count"] += 1
            _s["path_count"] += len(paths)
        return _s

    def _search(self, resource):
        count = 0
        for vpk_path, paths in self.table.items():
            for path in paths:
                if path_matches_resource(path, resource):
                    count += 1
                    yield vpk_path, path
        if count == 0:
            yield None, None

    # same thing as _search except it will open vmt files and resolve their resources as well.
    def _search_children(self, resource):
        for vpk_path, path in self._search(resource):
            if self.args.verbose and vpk_path:
                print(f"  {path}  ({vpk_path})")
            yield vpk_path, path
            if path and is_vmt(path):
                with vpk.open(vpk_path) as subpak:
                    vmt_f = subpak[path]
                    vmt_resources = find_resources_vmt(vmt_f)
                    for r in vmt_resources:
                        yield from self._search(r)

    def search(self, resource):
        if self.args.verbose:
            print(f"{resource}")
        return list(self._search_children(resource))

    def pretty_stats(self):
        s = self.stats
        print(f"[*] vpk count: {s['vpk_count']}")
        print(f"[*] vpk path count: {s['path_count']}")


def main():
    args = parse_args()

    # build a list of paths to find
    try:
        resources = find_resources_vmf(args.map)
    except FileNotFoundError:
        print(f"error: could not find map file: {args.map}")
        return

    if not args.verbose and not args.output:
        print("note: no output specified, this will only print errors")
        print("print all resources:")
        print("  " + " ".join(sys.argv) + " -v")
        print("write files to folder and zip:")
        print("  " + " ".join(sys.argv) + " -o out")
        print()
        print("errors:")

    # build a table of paths to search
    table = VPKTable(args)

    if args.verbose:
        print(f"[*] vmf resource count: {len(resources)}")
        table.pretty_stats()
        print()

    outputs = []
    for resource in resources:
        results = table.search(resource)
        for vpk_dir_path, path in results:
            if path is None:
                print(f"error: could not find {resource}")
            elif args.output:
                outputs.append((vpk_dir_path, path))
    if args.output:
        for vpk_dir_path, path in outputs:
            if vpk_dir_path not in table.ignore_dirs:
                export_path(args, vpk.open(vpk_dir_path), path, args.output)
            else:
                if args.verbose:
                    print(f"[*] ignoring {path}")

        output_filename = args.output
        dir_name = args.output
        shutil.make_archive(output_filename, "zip", dir_name)
        if args.verbose:
            print(f"[*] zipped: {output_filename}.zip")


if __name__ == "__main__":
    main()
