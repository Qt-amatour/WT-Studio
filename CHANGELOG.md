# Changelog

## 0.9.0 — Initial public release

### Core workflow

- DDS/TGA source texture import.
- Automatic `_c`, `_n`, and `_ao` recognition with manual type override.
- PBR texture splitting for external editing.
- DirectX/OpenGL normal-map convention options.
- Texture preview with zoom, fit, channel preview, and texture information.
- BC7 DDS source support.

### DDS Materials

- Material-based assembly workflow.
- TGA export.
- DDS ARGB 8.8.8.8 export.
- DDS BC1 export.
- DDS BC3 export.
- Bundled DirectXTex `texconv.exe`.
- BC7 game export intentionally disabled.

### BLK Editor

- Open and edit the original War Thunder user-skin BLK in place.
- SET and REPLACE rules.
- Automatic REPLACE lock for `_n` and `_ao` source rules.
- Add/remove texture and camo rules.
- Texture-rule ordering with move up/down controls.
- Camo rule kept at the top.
- Empty-BLK save protection.
- Preservation of existing rules that are not intentionally reassigned.
- External editor coexistence tested with Notepad++.

### NEW ASSETS

- Separate workflow for TGA source textures intended for Asset Viewer.
- Color (`_c`) asset creation with optional alpha/mask.
- Packed Normal (`_n`) asset creation.
- Ambient Occlusion (`_ao`) single-channel TGA export.
- DirectX/OpenGL normal convention handling.
- Independent NEW ASSETS output path.
- Project persistence through `.wts`.

### Projects and UI

- `.wts` project save/load.
- Project Library categories.
- Quick Start window.
- Help window with persistent "Don't show automatically again" option.
- Custom dark frameless UI.
- Window move/maximize/restore/minimize behavior.
- Native-style Windows application icon plus internal WT Studio branding.
- Session working/output path policy.
- UserSkins path configuration.
- Workflow tooltips and operation messages.

### Validation before release

- Current automated suite: 31 tests.
- Standalone Windows x64 release workflow validated.
- Final release candidate tested by multiple users without a reproduced
  release-blocking issue.

### Known limitations

- BC7 is accepted as input but cannot be exported as a game DDS format.
- `.wts` projects reference external files rather than embedding them.
- WT Studio does not scan the War Thunder installation or Asset Viewer
  automatically.
