# vmf zip

## install vpk

```
pip install vpk
```

## example: packing up cs textures for a gmod map

This will create a new folder called "export" that contains all the counter-strike textures found for your map.

passing the garrysmod root with -i allows the tool to verify textures aren't "missing" while still writing "found" textures to output.

```
python main.py -v -f -o export \
    -m "./map.vmf" \
    -r "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Source\cstrike" \
    -i "C:\Program Files (x86)\Steam\steamapps\common\GarrysMod"
```

## usage

```sh
usage: main.py [-h] [-f] [-v] [-m MAP] [-r ROOT] [-i IGNORE] [-o OUTPUT]

options:
  -h, --help            show this help message and exit
  -f, --force           force overwrite existing files
  -v, --verbose         verbose output
  -m MAP, --map MAP     path to your VMF map file
  -r ROOT, --root ROOT  path to your resource root, ex: "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Source\cstrike"
  -i IGNORE, --ignore IGNORE
                        IGNORE FILES FOUND IN path to your resource root, ex: "C:\Program Files (x86)\Steam\steamapps\common\GarrysMod"
  -o OUTPUT, --output OUTPUT
                        Output path
```
