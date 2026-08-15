from pathlib import Path

from app.models.texture_types import TextureType


class TextureDetector:

    @staticmethod
    def detect_texture_type(path):

        name = Path(path).stem.lower()

        if name.endswith("_c"):
            return TextureType.COLOR

        if name.endswith("_n"):
            return TextureType.NORMAL

        if name.endswith("_ao"):
            return TextureType.AO

        return TextureType.UNKNOWN