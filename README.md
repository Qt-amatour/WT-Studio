# WT Studio 0.9.1

WT Studio is an independent Windows desktop toolkit for preparing War Thunder
user-skin textures and related BLK configuration files.

It is designed around an external-editing workflow: source textures are
imported into WT Studio, converted into editable PBR maps, edited in tools such
as Substance Painter or Photoshop, then assembled back into textures suitable
for the game.

WT Studio does **not** scan the War Thunder installation or Asset Viewer
automatically. Source DDS/TGA files must be exported from Asset Viewer or
created by the in-game UserSkins workflow and then imported explicitly.

## Main workflows

### PBR Workflow

Import original DDS/TGA textures and split packed texture data into editable
PBR PNG maps.

Recognized texture suffixes include:

- `_c` — color/albedo
- `_n` — packed normal/PBR texture
- `_ao` — ambient occlusion

BC7 DDS files are supported as source material.

The normal-map workflow can export an OpenGL-oriented working normal map when
needed. The standard War Thunder target remains DirectX.

### DDS Materials

Build final materials from edited PBR maps.

Current game-export formats:

- TGA
- DDS ARGB 8.8.8.8
- DDS BC1
- DDS BC3

BC7 remains supported as input. The experimental War Thunder-style BC7 encoder is retained internally for future compatibility testing, but BC7 is not exposed as a game-export format because the current UserSkins test did not resolve the exported texture in game.

For packed `_n` materials, WT Studio can accept either DirectX or OpenGL RGB
normal-map sources and converts the Y convention when required.

### BLK Editor

Open and edit the original `.blk` file created for the user skin.

The editor supports:

- SET and REPLACE texture rules
- automatic REPLACE enforcement for `_n` and `_ao` source rules
- material selection from the current WT Studio project
- adding and removing rules
- changing the order of texture rules
- saving the existing BLK file in place

A BLK cannot be saved with zero texture rules. Removing all rules is still
allowed while editing; closing without saving restores the original file.

### NEW ASSETS

Create lossless TGA source textures intended for new/modded content that will
be processed through Asset Viewer.

Supported asset types:

- Color (`_c`)
- Packed Normal (`_n`)
- Ambient Occlusion (`_ao`)

NEW ASSETS uses its own export directory and is intentionally separate from
the UserSkins DDS Materials workflow.

### WTS projects

WT Studio project files use the `.wts` extension.

A WTS file stores project configuration, selected options, material setup and
paths to referenced files. It does not embed or archive the texture files
themselves.

## First start

1. Launch `WT Studio.exe`.
2. Optionally set `Path to UserSkins` from the Edit menu.
3. Start from Quick Start or create/open a project.
4. Use **Import Source Textures** to select DDS/TGA source files exported from
   Asset Viewer or created in a UserSkins folder.

A clean installation starts without a saved UserSkins path. WT Studio stores
that preference per Windows user account after you set it.

## Standalone build

The Windows release is self-contained and does not require Python, VS Code,
NVIDIA Texture Tools, or a separate DirectXTex installation.

WT Studio bundles Microsoft's DirectXTex `texconv.exe` for supported DDS
encoding.

## Building from source

Build environment:

- Windows x64
- Python 3.13 x64

Install build dependencies:

```powershell
python -m pip install -r requirements-build.txt
```

Run the automated tests:

```powershell
python -m unittest discover -s tests -v
```

Create the release build:

```powershell
build_windows_release.bat
```

The build process creates a standalone application and the final archive:

```text
release\WT_Studio_0.9.1_Windows_x64.zip
```

## Current release status

WT Studio 0.9.1 is the current release.

Version 0.9.1 is a focused maintenance update to the initial 0.9.0 public
release. It adds maximized startup behavior, fixes Project Sidebar
show/hide persistence across minimize/restore, and retains the experimental
BC7 export mechanism internally while keeping BC7 disabled as a game-export
profile until War Thunder UserSkins compatibility is confirmed.

## Notes and limitations

- Imported source files are read from their existing locations.
- Exported files are created only when an export operation is requested.
- The BLK editor modifies the original opened BLK in place when saved.
- Keep backups of important skin projects and original BLK files.
- Moving or renaming files referenced by a `.wts` project can break those
  stored paths.
- BC7 game export is currently disabled. The experimental BC7 encoder and legacy War Thunder-style DDS container code remain in the source for future compatibility testing.

## Independence / trademark notice

WT Studio is an independent community project and is not affiliated with,
endorsed by, or supported by Gaijin Entertainment.

War Thunder and related names and marks belong to their respective owners.

## License

WT Studio source code is released under the MIT License. See `LICENSE`.

Bundled third-party components retain their own licenses. See
`THIRD_PARTY_NOTICES.txt` and the license files distributed with those
components.


## Development note

The latest public stable release remains **WT Studio 0.9.0**. This source package is the release candidate for 0.9.1.
