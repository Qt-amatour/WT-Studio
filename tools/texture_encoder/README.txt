WT Studio bundled texture encoder

Required runtime file:
    tools\texture_encoder\texconv.exe

WT Studio runtime policy:
- WT Studio uses only this bundled DirectXTex texconv executable.
- External NVIDIA Texture Tools installations are not searched.
- Programs found through PATH are not used.
- Missing texconv.exe disables BC1/BC3 export with a clear error.
- TGA and uncompressed ARGB DDS export remain internal to WT Studio.
- BC7 is supported for import/reference only and is not a WT Studio 1.0
  game export format.

Diagnostics:
    check_texture_engine.bat
    validate_dds.bat

DirectXTex is third-party software distributed under the MIT License.
See:
    tools\texture_encoder\LICENSE_DirectXTex.txt
    THIRD_PARTY_NOTICES.txt
