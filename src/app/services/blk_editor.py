from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class BLKEditorError(Exception):
    pass


def requires_replace_texture_rule(value: str) -> bool:
    """Return True for WT texture sources that must use replace_tex."""
    cleaned = str(value).strip().strip('"').rstrip("*").strip()
    lowered = cleaned.casefold()

    for extension in (".dds", ".tga", ".png"):
        if lowered.endswith(extension):
            lowered = lowered[:-len(extension)]
            break

    return lowered.endswith(("_n", "_ao"))


class BLKEntryType(Enum):
    REPLACE = "replace_tex"
    SET = "set_tex"

    @property
    def display_name(self) -> str:
        return {
            BLKEntryType.REPLACE: "Replace",
            BLKEntryType.SET: "Set",
        }[self]


@dataclass(slots=True)
class BLKTextureEntry:
    entry_type: BLKEntryType
    from_value: str = ""
    to_value: str = ""
    has_param: bool = True
    is_camo: bool = False
    original_block: str = ""

    def normalize(self) -> None:
        self.from_value = self.from_value.strip()
        self.to_value = self.to_value.strip()

        if "_camo_" in self.from_value.casefold():
            self.is_camo = True

        if self.is_camo:
            self.entry_type = BLKEntryType.REPLACE
            self.has_param = False
        else:
            if requires_replace_texture_rule(self.from_value):
                self.entry_type = BLKEntryType.REPLACE
            self.has_param = True


@dataclass(slots=True)
class BLKDocument:
    path: Path
    original_text: str
    name_value: str = "user"
    entries: list[BLKTextureEntry] = field(default_factory=list)
    newline: str = "\n"
    text_segments: list[str] = field(default_factory=list)


class BLKEditor:
    NAME_RE = re.compile(
        r'(?m)^(?P<indent>[ \t]*)name:t[ \t]*=[ \t]*"(?P<value>[^"]*)"'
    )

    BLOCK_RE = re.compile(
        r'(?ms)^[ \t]*(?P<kind>set_tex|replace_tex)[ \t]*\{'
        r'(?P<body>.*?)'
        r'^[ \t]*\}'
    )

    VALUE_RE_TEMPLATE = (
        r'(?m)^[ \t]*{key}:t[ \t]*=[ \t]*"(?P<value>[^"]*)"'
    )

    def load(self, path: str | Path) -> BLKDocument:
        file_path = Path(path)

        if file_path.suffix.casefold() != ".blk":
            raise BLKEditorError(
                "Selected file is not a .blk file."
            )

        if not file_path.exists() or not file_path.is_file():
            raise BLKEditorError(
                f"BLK file does not exist: {file_path}"
            )

        raw = file_path.read_bytes()
        text = raw.decode(
            "utf-8",
            errors="surrogateescape",
        )

        name_match = self.NAME_RE.search(text)

        if name_match is None:
            raise BLKEditorError(
                'The selected BLK does not contain name:t="...".'
            )

        newline = self._detect_newline(text)
        matches = list(self.BLOCK_RE.finditer(text))

        entries: list[BLKTextureEntry] = []
        segments: list[str] = []
        cursor = 0

        for match in matches:
            segments.append(
                text[cursor:match.start()]
            )

            body = match.group("body")
            kind = match.group("kind")

            from_value = self._read_value(
                body,
                "from",
            ) or ""

            to_value = self._read_value(
                body,
                "to",
            ) or ""

            entry = BLKTextureEntry(
                entry_type=(
                    BLKEntryType.SET
                    if kind == "set_tex"
                    else BLKEntryType.REPLACE
                ),
                from_value=from_value,
                to_value=to_value,
                has_param=(
                    self._read_value(
                        body,
                        "param",
                    )
                    is not None
                ),
                is_camo=(
                    "_camo_"
                    in from_value.casefold()
                ),
                original_block=match.group(0),
            )

            entry.normalize()
            entries.append(entry)
            cursor = match.end()

        segments.append(
            text[cursor:]
        )

        return BLKDocument(
            path=file_path,
            original_text=text,
            name_value=name_match.group("value"),
            entries=entries,
            newline=newline,
            text_segments=segments,
        )

    def save_in_place(
        self,
        document: BLKDocument,
    ) -> None:
        path = document.path

        if not document.entries:
            raise BLKEditorError(
                "A BLK must contain at least one texture rule before it "
                "can be saved. Add a Texture Rule or Camo Rule first."
            )

        if not path.exists():
            raise BLKEditorError(
                "The original BLK file no longer exists. "
                "WT Studio will not create a replacement."
            )

        current_text = path.read_bytes().decode(
            "utf-8",
            errors="surrogateescape",
        )

        if current_text != document.original_text:
            raise BLKEditorError(
                "The BLK changed on disk after it was opened. "
                "Reload it before saving."
            )

        text = self._rebuild_document(
            document
        )

        name_match = self.NAME_RE.search(text)

        if (
            name_match is None
            or name_match.group("value")
            != document.name_value
        ):
            raise BLKEditorError(
                "Safety check failed: name:t would be changed."
            )

        encoded = text.encode(
            "utf-8",
            errors="surrogateescape",
        )

        with path.open("r+b") as target:
            target.seek(0)
            target.write(encoded)
            target.truncate()

        refreshed = self.load(path)

        document.original_text = refreshed.original_text
        document.entries = refreshed.entries
        document.text_segments = refreshed.text_segments
        document.newline = refreshed.newline
        document.name_value = refreshed.name_value

    def _rebuild_document(
        self,
        document: BLKDocument,
    ) -> str:
        entries = list(document.entries)

        camo = [
            entry
            for entry in entries
            if entry.is_camo
        ]

        regular = [
            entry
            for entry in entries
            if not entry.is_camo
        ]

        ordered = camo[:1] + regular

        original_rule_count = max(
            0,
            len(document.text_segments) - 1,
        )

        if len(ordered) == original_rule_count:
            pieces: list[str] = []

            for index, entry in enumerate(ordered):
                pieces.append(
                    document.text_segments[index]
                )
                pieces.append(
                    self._serialize_entry(
                        entry,
                        document.newline,
                    )
                )

            pieces.append(
                document.text_segments[-1]
            )

            return "".join(pieces)

        prefix = (
            document.text_segments[0]
            if document.text_segments
            else document.original_text
        )

        # With zero original rule blocks load() produces exactly one text
        # segment containing the whole BLK. Reusing that same segment as both
        # prefix and suffix would duplicate protected content such as
        # name:t="user" when the first new rule is later added.
        suffix = (
            ""
            if original_rule_count == 0
            else (
                document.text_segments[-1]
                if document.text_segments
                else ""
            )
        )

        blocks = (
            document.newline
            + document.newline
        ).join(
            self._serialize_entry(
                entry,
                document.newline,
            )
            for entry in ordered
        )

        if blocks:
            if (
                prefix
                and not prefix.endswith(
                    ("\r\n", "\n", "\r")
                )
            ):
                prefix += document.newline

            if (
                suffix
                and not suffix.startswith(
                    ("\r\n", "\n", "\r")
                )
            ):
                blocks += document.newline

        return prefix + blocks + suffix

    def _serialize_entry(
        self,
        entry: BLKTextureEntry,
        newline: str,
    ) -> str:
        entry.normalize()

        if (
            entry.original_block
            and self._block_matches_entry(
                entry.original_block,
                entry,
            )
        ):
            return entry.original_block

        lines = [
            f"{entry.entry_type.value}{{",
            f'  from:t="{entry.from_value}"',
            f'  to:t="{entry.to_value}"',
        ]

        if not entry.is_camo:
            lines.append(
                '  param:t="camo_skin_tex"'
            )

        lines.append("}")

        return newline.join(lines)

    def _block_matches_entry(
        self,
        block: str,
        entry: BLKTextureEntry,
    ) -> bool:
        match = self.BLOCK_RE.search(block)

        if match is None:
            return False

        body = match.group("body")
        kind = match.group("kind")

        block_type = (
            BLKEntryType.SET
            if kind == "set_tex"
            else BLKEntryType.REPLACE
        )

        from_value = self._read_value(
            body,
            "from",
        ) or ""

        to_value = self._read_value(
            body,
            "to",
        ) or ""

        has_param = (
            self._read_value(
                body,
                "param",
            )
            is not None
        )

        return (
            block_type is entry.entry_type
            and from_value == entry.from_value
            and to_value == entry.to_value
            and (
                (
                    entry.is_camo
                    and not has_param
                )
                or (
                    not entry.is_camo
                    and has_param
                )
            )
        )

    @staticmethod
    def _detect_newline(
        text: str,
    ) -> str:
        if "\r\n" in text:
            return "\r\n"

        if "\n" in text:
            return "\n"

        if "\r" in text:
            return "\r"

        return "\r\n"

    @classmethod
    def _read_value(
        cls,
        body: str,
        key: str,
    ) -> str | None:
        pattern = re.compile(
            cls.VALUE_RE_TEMPLATE.format(
                key=re.escape(key)
            )
        )

        match = pattern.search(body)

        if match is None:
            return None

        return match.group("value")
