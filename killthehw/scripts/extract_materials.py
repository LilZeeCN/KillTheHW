#!/usr/bin/env python3
"""Extract initial text and media; never mark semantic or visual review complete."""
import argparse
import json
import posixpath
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from _common import digest, load_job, local_path, write_json

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def xml_paths(node, path=""):
    """Keep sibling indices, including table/row/cell hierarchy, in locators."""
    counts = {}
    for child in node:
        tag = child.tag.split("}")[-1]
        counts[tag] = counts.get(tag, 0) + 1
        current = f"{path}/{tag}[{counts[tag]}]"
        yield child, current
        yield from xml_paths(child, current)


def paragraph_text(node, tags):
    pieces = []
    for child in node:
        if child.tag in tags:
            pieces.append(child.text or "")
        elif child.tag.split("}")[-1] in {"tab", "br"}:
            pieces.append(" ")
        elif child.tag.split("}")[-1] != "p":
            pieces.append(paragraph_text(child, tags))
    return "".join(pieces)


def extract_ooxml(source, output, kind):
    lines, warnings, media = [], [], []
    content_chars = 0
    with ZipFile(source) as archive:
        if kind == "xlsx":
            shared = []
            if "xl/sharedStrings.xml" in archive.namelist():
                tree = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = ["".join(x.itertext()) for x in tree.findall("s:si", NS)]
            relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            targets = {x.get("Id"): x.get("Target") for x in relations}
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            for sheet in workbook.findall("s:sheets/s:sheet", NS):
                target = targets[sheet.get(f"{{{NS['r']}}}id")]
                part = (target.lstrip("/") if target.startswith("/") else
                        posixpath.normpath(posixpath.join("xl", target)))
                lines.append(f"\n## worksheet: {sheet.get('name')} ({part})\n")
                tree = ET.fromstring(archive.read(part))
                for cell in tree.findall(".//s:sheetData/s:row/s:c", NS):
                    value = cell.findtext("s:v", default="", namespaces=NS)
                    if cell.get("t") == "s":
                        value = shared[int(value)]
                    elif cell.get("t") == "inlineStr":
                        value = "".join(t.text or "" for t in cell.findall(".//s:t", NS))
                    formula = cell.find("s:f", NS)
                    if formula is not None:
                        value = f"formula={formula.text or '[shared/array formula; inspect workbook]'}; cached={value}"
                    content_chars += len(value.strip())
                    lines.append(f"[{cell.get('r')}] {value}")
            warnings.append("Values are raw OOXML; formula caches may be stale. Inspect styles, merged cells, charts, hidden sheets and recalculate in a spreadsheet engine.")
        else:
            prefix = "word/" if kind == "docx" else "ppt/"
            parts = sorted(n for n in archive.namelist() if n.startswith(prefix) and n.endswith(".xml"))
            for part in parts:
                tree = ET.fromstring(archive.read(part))
                paragraphs = []
                tags = {f"{{{NS['w']}}}t", f"{{{NS['w']}}}delText", f"{{{NS['a']}}}t"}
                for node, locator in xml_paths(tree):
                    if node.tag in {f"{{{NS['w']}}}p", f"{{{NS['a']}}}p"}:
                        value = paragraph_text(node, tags).strip()
                        if value:
                            content_chars += len(value)
                            paragraphs.append(f"[{locator}] {value}")
                if paragraphs:
                    lines.extend([f"\n## {part}\n", *paragraphs])
            warnings.append("Raw paragraph order is not rendered layout. Inspect formulas, tables, text boxes, charts, comments, revisions and embedded objects in the original. Deleted and current text may both appear.")
            if kind == "pptx":
                warnings.append("Slide part numbers are not guaranteed presentation order; inspect the deck and speaker notes.")
        for member in archive.namelist():
            if "/media/" in member and not member.endswith("/"):
                target = output / "media" / f"{len(media) + 1:03d}-{Path(member).name}"
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(archive.read(member))
                media.append({"archive_part": member, "file": str(target.relative_to(output))})
        if media:
            warnings.append("Media resources have not been interpreted or mapped to questions; view the original layout.")
    return "\n".join(lines), warnings, media, content_chars


def extract_one(root, item):
    source = Path(item["path"])
    if digest(source) != item["sha256"]:
        raise ValueError("Source changed; compare requirements and reset review before updating its hash")
    output = local_path(root, f"extracted/{item['id']}")
    output.mkdir(parents=True, exist_ok=True)
    kind = item["kind"]
    warnings, media = [], []
    if kind == "text":
        text = source.read_text(encoding="utf-8-sig")
        content_chars = len(text.strip())
        text = "\n".join(f"[line {i}] {line}" for i, line in enumerate(text.splitlines(), 1))
    elif kind == "pdf":
        binary = shutil.which("pdftotext")
        if not binary:
            raise ValueError("pdftotext unavailable; use a host PDF reader or convert locally")
        result = subprocess.run([binary, "-layout", "-enc", "UTF-8", str(source), "-"],
                                capture_output=True, timeout=120)
        if result.returncode:
            raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
        pages = result.stdout.decode("utf-8").split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
        content_chars = sum(len(page.strip()) for page in pages)
        text = "\n\n".join(f"## PDF page {i}\n\n{page}" for i, page in enumerate(pages, 1))
        short = [i for i, page in enumerate(pages, 1) if len(page.strip()) < 40]
        warnings.append(f"All task-relevant pages require visual review, including text-rich pages. Low-text pages: {short}; consider OCR.")
    elif kind in {"docx", "pptx", "xlsx"}:
        text, warnings, media, content_chars = extract_ooxml(source, output, kind)
    else:
        return {"status": "needs_host_reader", "source_sha256": item["sha256"],
                "warnings": ["Read/convert with an available host tool; this input has not been read."]}
    content = output / "content.txt"
    content.write_text(text, encoding="utf-8")
    if not content_chars:
        warnings.append("No text extracted; inspect the source visually or use OCR.")
    return {"status": "text_extracted" if content_chars else "needs_host_reader",
            "content_chars": content_chars,
            "source_sha256": item["sha256"], "text": str(content.relative_to(root)),
            "text_sha256": digest(content), "visual_review_required": kind != "text",
            "warnings": warnings, "media": media}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir")
    parser.add_argument("--input", dest="input_id")
    args = parser.parse_args()
    try:
        root, job = load_job(args.job_dir)
        selected = [x for x in job["inputs"] if not args.input_id or x["id"] == args.input_id]
        if not selected:
            raise ValueError("No matching input")
        for item in selected:
            try:
                item["extraction"] = extract_one(root, item)
            except (OSError, ValueError, KeyError, IndexError, ET.ParseError, BadZipFile,
                    subprocess.TimeoutExpired) as error:
                item["extraction"] = {"status": "error", "error": str(error)}
        write_json(root / "job.json", job)
        print(json.dumps([{ "id": x["id"], **x["extraction"]} for x in selected],
                         ensure_ascii=False, indent=2))
        return 1 if any(x["extraction"]["status"] != "text_extracted" for x in selected) else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
