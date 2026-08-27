"""Parse raw HTTP content into a small intermediate representation."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class ParsedDocument:
    content_type: str
    title: str = ""
    text: str = ""
    links: list[str] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    data: object | None = None
    media: dict[str, object] | None = None
    parse_warnings: list[str] = field(default_factory=list)


class _HTMLCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self.tables: list[list[list[str]]] = []
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        if tag == "table" and self._current_table is None:
            self._current_table = []
        elif tag == "tr" and self._current_table is not None and self._current_row is None:
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None and self._current_cell is None:
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            self._current_row.append(re.sub(r"\s+", " ", " ".join(self._current_cell)).strip())
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None and self._current_table is not None:
            if self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._current_table is not None:
            if self._current_row:
                self._current_table.append(self._current_row)
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
        else:
            self.text_parts.append(data)
        if self._current_cell is not None:
            self._current_cell.append(data)


def _balanced_json_after(source: str, marker: str) -> object | None:
    start = source.find(marker)
    if start < 0:
        return None
    opening = source.find("{", start)
    if opening < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(opening, min(len(source), opening + 5_000_000)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(source[opening:index + 1])
                except json.JSONDecodeError:
                    return None
    return None


def extract_media_metadata(source: str) -> dict[str, object] | None:
    """Extract public media metadata and caption-track URLs from HTML pages."""
    media: dict[str, object] = {}
    meta_patterns = {
        "title": r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
        "description": r'(?is)<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
        "thumbnail_url": r'(?is)<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']',
        "video_url": r'(?is)<meta[^>]+property=["\']og:video:url["\'][^>]+content=["\'](.*?)["\']',
    }
    for field_name, pattern in meta_patterns.items():
        match = re.search(pattern, source)
        if match:
            media[field_name] = html.unescape(match.group(1)).strip()
    player = _balanced_json_after(source, "ytInitialPlayerResponse")
    if isinstance(player, dict):
        details = player.get("videoDetails") if isinstance(player.get("videoDetails"), dict) else {}
        microformat_root = player.get("microformat") if isinstance(player.get("microformat"), dict) else {}
        microformat = microformat_root.get("playerMicroformatRenderer") if isinstance(microformat_root.get("playerMicroformatRenderer"), dict) else {}
        for key in ("videoId", "title", "shortDescription", "author", "channelId", "lengthSeconds", "viewCount", "keywords"):
            if details.get(key) is not None:
                media[key] = details[key]
        for key in ("publishDate", "uploadDate", "category", "isFamilySafe", "availableCountries"):
            if microformat.get(key) is not None:
                media[key] = microformat[key]
        captions = player.get("captions") if isinstance(player.get("captions"), dict) else {}
        renderer = captions.get("playerCaptionsTracklistRenderer") if isinstance(captions.get("playerCaptionsTracklistRenderer"), dict) else {}
        tracks = []
        for track in renderer.get("captionTracks", []) if isinstance(renderer.get("captionTracks"), list) else []:
            if isinstance(track, dict) and isinstance(track.get("baseUrl"), str):
                tracks.append({"base_url": html.unescape(track["baseUrl"]), "language_code": track.get("languageCode"), "name": track.get("name")})
        if tracks:
            media["caption_tracks"] = tracks[:10]
    return media or None


def extract_caption_text(source: str) -> str:
    """Convert YouTube timed-text XML into readable transcript text."""
    values = []
    for match in re.finditer(r"(?is)<text[^>]*>(.*?)</text>", source):
        value = re.sub(r"<[^>]+>", " ", match.group(1))
        value = html.unescape(value).strip()
        if value:
            values.append(value)
    return re.sub(r"\s+", " ", " ".join(values)).strip()[:200_000]


def parse(raw: bytes, content_type: str) -> ParsedDocument:
    """Parse raw bytes; malformed or unsupported content returns warnings, not exceptions."""
    normalized_type = (content_type or "").lower().split(";", 1)[0].strip()
    decoded = raw.decode("utf-8", errors="replace")
    media = extract_media_metadata(decoded)
    if normalized_type in {"application/json", "application/ld+json"} or decoded.lstrip().startswith(("{", "[")):
        try:
            return ParsedDocument(content_type="application/json", data=json.loads(decoded), text=decoded, media=media)
        except json.JSONDecodeError as error:
            return ParsedDocument(
                content_type=normalized_type or "application/json",
                text=decoded,
                media=media,
                parse_warnings=[f"malformed JSON: {error.msg}"],
            )
    if normalized_type in {"text/html", "application/xhtml+xml"} or re.search(r"<html|<body|<title", decoded, re.I):
        collector = _HTMLCollector()
        try:
            collector.feed(decoded)
        except Exception as error:  # HTMLParser can stop on malformed input.
            return ParsedDocument(
                content_type=normalized_type or "text/html",
                text=re.sub(r"\s+", " ", decoded).strip(),
                parse_warnings=[f"malformed HTML: {error}"],
            )
        text = re.sub(r"\s+", " ", " ".join(collector.text_parts)).strip()
        entities = []
        for match in re.finditer(r"\b(?:[A-Z][A-Za-z0-9&.-]*)(?:\s+(?:[A-Z][A-Za-z0-9&.-]*)){0,1}\b", text):
            value = match.group(0).strip(".,:;!?()")
            if len(value) > 1 and value not in {"The", "This", "That", "AgentWeb"}:
                entities.append(value)
        return ParsedDocument(
            content_type=normalized_type or "text/html",
            title=re.sub(r"\s+", " ", " ".join(collector.title_parts)).strip(),
            text=text,
            links=list(dict.fromkeys(collector.links)),
            tables=collector.tables,
            entities=list(dict.fromkeys(entities)),
            media=media,
        )
    if normalized_type == "application/pdf" or raw.startswith(b"%PDF"):
        return ParsedDocument(
            content_type="application/pdf",
            text=decoded,
            parse_warnings=["PDF layout parsing is not available in the dependency-free MVP"],
        )
    return ParsedDocument(content_type=normalized_type or "text/plain", text=decoded, media=media)
