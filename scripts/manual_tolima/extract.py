"""Extract the species sheets of the "Manual de arborización para el departamento del Tolima"
(Cortolima – Jardín Botánico San Jorge, 2017) into JSON, keeping the text verbatim.

Usage:
    python3 scripts/manual_tolima/extract.py MANUAL.pdf > entries.json

Needs poppler's ``pdftohtml``. The sheets (pp. 142-255) are laid out by Word as two
"newspaper" columns: inside each block between two sheet titles the text runs down the left
column, then down the right one. Titles are centered, bold and in capitals. Lines are joined
with spaces (the PDF breaks them only for layout); bold runs inside paragraphs are kept as
``**…**``; nothing is reworded or corrected.
"""

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

FIRST_PAGE, LAST_PAGE = 142, 255
MID = 459  # half of the 918 px page width used by pdftohtml
HEADINGS = {
    "distribución geográfica", "descripción", "hojas", "flores", "frutos", "flores y frutos",
    "fruto", "flor", "inflorescencia", "inflorescencias", "localización recomendada",
    "semillas", "semilla", "tallo", "raíz", "raices", "raíces", "usos", "fenología",
    "propagación", "observaciones", "corteza", "copa", "fuste", "ecología", "hábitat",
}
LABELS = ["Nombre Científico", "Nombre científico", "Familia", "Sinónimos", "Sinonimos", "Sinónimo",
          "Nombres comunes", "Nombre común", "Nombre Común", "Nombre comun", "Lugar de origen", "Origen"]


def load(pdf):
    xml = subprocess.run(
        ["pdftohtml", "-xml", "-i", "-q", "-f", str(FIRST_PAGE), "-l", str(LAST_PAGE), "-stdout", pdf],
        check=True, capture_output=True, text=True,
    ).stdout
    xml = re.sub(r"<!DOCTYPE[^>]*>", "", xml)
    root = ET.fromstring(xml)
    fonts = {}
    pages = []
    for page in root.iter("page"):
        for fs in page.iter("fontspec"):
            fonts[fs.get("id")] = (int(fs.get("size")), "Bold" in fs.get("family"))
        items = []
        for t in page.iter("text"):
            text = "".join(t.itertext())
            if not text.strip():
                continue
            size, bold_font = fonts[t.get("font")]
            bold = bold_font or t.find(".//b") is not None
            items.append({"top": int(t.get("top")), "left": int(t.get("left")), "width": int(t.get("width")),
                          "size": size, "bold": bold, "text": text})
        pages.append((int(page.get("number")), items))
    return pages


def is_title(it):
    t = it["text"].strip()
    return it["bold"] and it["left"] > 150 and len(t) >= 3 and not re.search(r"[a-záéíóúñ]", t) and re.search(r"[A-Z]", t)


def lines_of(items):
    """Group items into lines (same top ±3 px), each a list of items sorted left to right."""
    out = []
    for it in sorted(items, key=lambda i: (i["top"], i["left"])):
        if out and abs(out[-1][0]["top"] - it["top"]) <= 3:
            out[-1].append(it)
        else:
            out.append([it])
    return [sorted(l, key=lambda i: i["left"]) for l in out]


def blocks(pages):
    """Yield (page, kind, payload): ('title', text) or ('line', items) in reading order."""
    for number, items in pages:
        titles = sorted({it["top"] for it in items if is_title(it)})
        cuts = [-1] + titles + [10**6]
        for a, b in zip(cuts, cuts[1:]):
            if a in titles:
                yield number, "title", " ".join(i["text"].strip() for i in items if i["top"] == a and is_title(i))
            region = [i for i in items if a < i["top"] < b and not (i["top"] == a)]
            region = [i for i in region if not is_title(i)]
            for col in ([i for i in region if i["left"] < MID], [i for i in region if i["left"] >= MID]):
                for line in lines_of(col):
                    yield number, "line", line


def render(line):
    """Line text with bold runs inside ``**``; also whether the whole line is bold."""
    parts, all_bold = [], all(i["bold"] for i in line if i["text"].strip())
    for i in line:
        t = i["text"]
        if i["bold"] and t.strip():
            lead = " " if t[:1].isspace() else ""
            t = f"{lead}**{t.strip()}** "
        parts.append(t)
    return "".join(parts), all_bold


def tidy(s):
    """Collapse whitespace and merge adjacent bold runs: '**a** **b**' -> '**a b**'."""
    s = re.sub(r"\s+", " ", s).strip()
    while "** **" in s:
        s = s.replace("** **", " ")
    s = s.replace("****", "")
    # '**word ,**' -> '**word**,' : keep punctuation outside, no space before it.
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    return s


def split_header(text):
    """'Nombre Científico: X Familia: Y Nombre común: Z …' -> {label: value}."""
    pat = "|".join(re.escape(l) for l in sorted(LABELS, key=len, reverse=True))
    found = {}
    for m in re.finditer(rf"({pat})\s*:\s*(.*?)(?=(?:{pat})\s*:|$)", text):
        found[m.group(1)] = m.group(2).strip().strip("*").strip()
    return found


def entries(pdf):
    cur = None
    for page, kind, payload in blocks(load(pdf)):
        if kind == "title":
            if cur:
                yield cur
            cur = {"title": tidy(payload), "pages": [page], "header": [], "sections": []}
            continue
        if cur is None:
            continue
        if page not in cur["pages"]:
            cur["pages"].append(page)
        text, all_bold = render(payload)
        plain = tidy(text.replace("**", ""))
        key = plain.rstrip(":. ").lower()
        if all_bold and key in HEADINGS:
            cur["sections"].append({"title": plain.rstrip(":. "), "lines": []})
        elif cur["sections"]:
            cur["sections"][-1]["lines"].append(text)
        else:
            cur["header"].append(text)
    if cur:
        yield cur


def finish(e):
    header = tidy(" ".join(l.replace("**", "") for l in e["header"]))
    fields = split_header(header)
    sections = []
    for s in e["sections"]:
        body = tidy(" ".join(s["lines"]))
        if body:
            sections.append({"title": s["title"], "text": body})
    return {
        "title": e["title"],
        "pages": [min(e["pages"]), max(e["pages"])],
        "scientific_name": fields.get("Nombre Científico") or fields.get("Nombre científico", ""),
        "family": fields.get("Familia", ""),
        "synonyms": fields.get("Sinónimos") or fields.get("Sinonimos") or fields.get("Sinónimo", ""),
        "common_names": next((fields[k] for k in ("Nombres comunes", "Nombre común", "Nombre Común", "Nombre comun") if k in fields), ""),
        "origin": fields.get("Lugar de origen") or fields.get("Origen", ""),
        "header_raw": header,
        "sections": sections,
    }


if __name__ == "__main__":
    json.dump([finish(e) for e in entries(sys.argv[1])], sys.stdout, ensure_ascii=False, indent=1)
