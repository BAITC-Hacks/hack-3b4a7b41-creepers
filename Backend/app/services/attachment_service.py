"""Bounded, in-memory extraction. Uploaded instructions never trigger cart tools."""
from io import BytesIO
from pathlib import PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

LIMIT = 6000


def extract_text(filename: str, content: bytes) -> str:
    suffix = PurePosixPath(filename).suffix.lower()
    try:
        if suffix == ".pdf" and content.startswith(b"%PDF"):
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                return ""
            # Only text PDFs; scanning/OCR is not silently implied.
            result = []
            for page in reader.pages[:10]:
                stream = page.get_contents()
                if stream and len(stream.get_data()) > 2 * 1024 * 1024:
                    continue
                result.append((page.extract_text() or "")[:LIMIT])
            return "\n".join(result)[:LIMIT].strip()
        if suffix not in {".docx", ".xlsx"} or not content.startswith(b"PK"):
            return ""
        with ZipFile(BytesIO(content)) as archive:
            if len(archive.infolist()) > 1000 or sum(item.file_size for item in archive.infolist()) > 20 * 1024 * 1024:
                return ""
            def root(name):
                return ElementTree.fromstring(archive.read(name))
            def texts(element):
                return " ".join(node.text or "" for node in element.iter() if node.tag.rsplit("}", 1)[-1] == "t")
            if suffix == ".docx":
                return "\n".join(texts(node) for node in root("word/document.xml").iter() if node.tag.endswith("}p"))[:LIMIT].strip()
            strings = [texts(node) for node in root("xl/sharedStrings.xml")] if "xl/sharedStrings.xml" in archive.namelist() else []
            lines = []
            for name in sorted(n for n in archive.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))[:5]:
                for row in root(name).iter():
                    if not row.tag.endswith("}row"):
                        continue
                    cells = []
                    for cell in row:
                        # Formula values are untrusted cached text, never evaluated.
                        if cell.attrib.get("t") == "inlineStr":
                            cells.append(texts(cell))
                        else:
                            value = next((node.text or "" for node in cell if node.tag.endswith("}v")), "")
                            cells.append(strings[int(value)] if cell.attrib.get("t") == "s" and value.isdigit() and int(value) < len(strings) else value)
                    lines.append(" | ".join(cells))
                    if sum(map(len, lines)) >= LIMIT:
                        return "\n".join(lines)[:LIMIT]
            return "\n".join(lines)[:LIMIT].strip()
    except (BadZipFile, KeyError, ValueError, OSError, ElementTree.ParseError):
        return ""
    except Exception:
        # Malformed PDFs are untrusted input. Never return parser internals.
        return ""
