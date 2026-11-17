"""Extract the species sheets of the "Manual de arborización para el departamento del Tolima"
(Cortolima – Jardín Botánico San Jorge, 2017) into JSON, keeping the text verbatim.

Usage:
    python3 scripts/manual_tolima/extract.py MANUAL.pdf > entries.json
    python3 scripts/manual_tolima/extract.py MANUAL.pdf --report   # unknown bold prefixes

Needs poppler's ``pdftohtml``. How the sheets (pp. 142-255) are laid out:

- Each sheet starts with a title in capitals, bold, 18-21 pt, usually centered (e.g.
  "FICUS BENJAMINA"; "HAYUELO ROSADO" spans two lines). Authors in capitals on the name
  line ("H.B. & K.", "(LAM.) DE WIT") use similar fonts, so a title line must have no
  lowercase and not share its line with "Nombre Científico".
- Word lays the text out as two "newspaper" columns: between two titles it runs down the
  left column, then down the right one.
- The header ("Nombre Científico", "Familia", "Sinónimos", "Nombre común", "Lugar de origen",
  "Procedencia", …) and the section headings ("Descripción", "Hojas", "Flores", …) are bold
  runs at the start of a line, sometimes followed by text on the same line.

Output per sheet: title, pages, scientific name (the line's text, author included), the
header as ``[{label, value}]`` and the sections as ``[{title, text}]``, both in the manual's
order and with the manual's own wording. Lines are joined with spaces (the PDF breaks them
only for layout); paragraphs (a gap of more than 28 px, a normal line being ~18 px) are
separated by a blank line (``\n\n``); bold runs are kept as ``**…**``; nothing is reworded or
corrected. Sheets without a scientific name (editorial notes such as "FALTA FOTO") are dropped.
"""

import json
import re
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET

FIRST_PAGE, LAST_PAGE = 142, 255
MID = 459  # half of the 918 px page width used by pdftohtml
MARGIN = 150  # items left of this start a line in the left column


def norm(s):
    """Lowercase, no accents, no trailing colon, single spaces: for matching labels only."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip(" :.")


# Header labels (normalized) -> canonical key. The label shown is the manual's own.
LABELS = {
    "nombre cientifico": "scientific_name",
    "familia": "family",
    "sinonimos": "synonyms",
    "sinonimo": "synonyms",
    "sinonimia": "synonyms",
    "nombre comun": "common_names",
    "nombre comum": "common_names",
    "nombres comunes": "common_names",
    "nombre vulgar": "common_names",
    "nombre": "common_names",
    "nombres vulgares": "common_names",
    "lugar de origen": "origin",
    "procedencia": "origin",
    "origen": "origin",
}
HEADINGS = {
    "distribucion geografica", "distribucion geografica natural", "distribucion", "descripcion", "hojas", "hoja", "flores", "flor",
    "frutos", "fruto", "flores y frutos", "frutos y semillas", "fruto y semillas", "frutos y semilla",
    "fruto y semilla", "fruta y semilla", "frutosy semillas", "semillas",
    "semilla", "inflorescencia", "inflorescencias", "localizacion recomendada", "propagacion",
    "usos", "fenologia", "tallo", "raiz", "raices", "corteza", "ecologia", "habitat",
    "observaciones", "floracion",
}


def load(pdf):
    xml = subprocess.run(
        ["pdftohtml", "-xml", "-i", "-q", "-f", str(FIRST_PAGE), "-l", str(LAST_PAGE), "-stdout", pdf],
        check=True, capture_output=True, text=True,
    ).stdout
    root = ET.fromstring(re.sub(r"<!DOCTYPE[^>]*>", "", xml))
    fonts, pages = {}, []
    for page in root.iter("page"):
        for fs in page.iter("fontspec"):
            fonts[fs.get("id")] = (int(fs.get("size")), fs.get("family"))
        items = []
        for t in page.iter("text"):
            text = "".join(t.itertext())
            if not text.strip():
                continue
            size, family = fonts[t.get("font")]
            if size <= 10 and text.strip() == "2":
                text = "²"  # superscript of m² (a small "2" in the PDF)
            items.append({
                "top": int(t.get("top")), "left": int(t.get("left")), "width": int(t.get("width")), "size": size,
                "bold": "Bold" in family or t.find(".//b") is not None,
                "italic": "Italic" in family or t.find(".//i") is not None,
                "text": text,
            })
        pages.append((int(page.get("number")), items))
    return pages


def lines_of(items, tol=8):
    """Group items into lines (same top ± tol px; the name line drifts up to 6 px), each
    sorted left to right. Body lines are 18 px apart."""
    out = []
    for it in sorted(items, key=lambda i: (i["top"], i["left"])):
        if out and abs(out[-1][0]["top"] - it["top"]) <= tol:
            out[-1].append(it)
        else:
            out.append([it])
    return [sorted(l, key=lambda i: i["left"]) for l in out]


def join(items):
    """Concatenate items, adding a space where the PDF leaves a gap without one."""
    out = ""
    for prev, i in zip([None] + items, items):
        t = i["text"]
        if prev and out and not out[-1].isspace() and not t[:1].isspace() and t != "²" \
                and i["left"] > prev["left"] + prev["width"] + 1:
            out += " "
        out += t
    return out


def title_lines(items):
    """Sheet titles as (top of first line, bottom limit, text). A title line is bold, at least
    18 pt, without lowercase and without "Nombre"; consecutive ones (< 40 px) are one title."""
    out = []
    for line in lines_of(items):
        text = re.sub(r"\s+", " ", join(line)).strip()
        if (all(i["bold"] and i["size"] >= 18 for i in line) and len(text) >= 3
                and not re.search(r"[a-záéíóúñ]", text) and "NOMBRE" not in text.upper()
                and re.search(r"[A-ZÁÉÍÓÚÑ]{3}", text)):
            top = min(i["top"] for i in line)
            if out and top - out[-1][1] < 40:
                out[-1] = (out[-1][0], top, out[-1][2] + " " + text)
            else:
                out.append((top, top, text))
    return out


def stream(pages):
    """Yield (page, 'title', text) and (page, 'line', items) in reading order."""
    for number, items in pages:
        # Footnotes: from a footnote number (small, at the start of a line) to the page end.
        notes = [i["top"] for i in items if i["size"] <= 11 and i["text"].strip().isdigit() and i["left"] < MARGIN]
        if notes:
            items = [i for i in items if i["top"] < min(notes) - 4]
        titles = title_lines(items)
        cuts = [(-1, -1, None)] + titles + [(10**6, 10**6, None)]
        for (_, a, title), (b, _, _) in zip(cuts, cuts[1:]):
            if title:
                yield number, "title", title
            region = [i for i in items if a + 6 < i["top"] < b - 6 and not is_stray(number, i)]
            # The scientific name and its author run across the page: everything from the
            # "Nombre Científico" line down to the "Familia" line belongs to the left column.
            name = [i["top"] for i in region if norm(i["text"]).startswith("nombre") and i["left"] < MARGIN
                    and "cient" in norm(join([j for j in region if abs(j["top"] - i["top"]) <= 8]))]
            fam = [i["top"] for i in region if norm(i["text"]).startswith(("familia", "sinonimo")) and i["left"] < MARGIN]
            lo = min(name) - 8 if name else None
            hi = min([t for t in fam if lo is not None and t > lo] or [lo or 0]) - 4 if name else None
            # Only the name's own fonts (>= 17 pt): the right column's body text (15 pt) may
            # start beside a long name.
            full = lambda i: lo is not None and lo <= i["top"] <= hi and i["size"] >= 17
            for col in ([i for i in region if i["left"] < MID or full(i)],
                        [i for i in region if i["left"] >= MID and not full(i)]):
                for line in lines_of(col):
                    yield number, "line", line


# Text on a sheet page that is not part of any sheet (left over from editing).
STRAY = {(224, "CASUARINÁCEAS")}


def is_stray(page, item):
    return (page, item["text"].strip()) in STRAY


def split_prefix(line):
    """(bold text at the start of the line, the rest as items)."""
    k = 0
    while k < len(line) and (line[k]["bold"] or not line[k]["text"].strip()):
        k += 1
    return join(line[:k]), line[k:]


def render(items):
    """Text with bold runs inside ``**``."""
    marked = []
    for i in items:
        t = i["text"]
        if i["bold"] and t.strip():
            t = (" " if t[:1].isspace() else "") + f"**{t.strip()}** "
        marked.append({**i, "text": t})
    return join(marked)


PARA = "\u2029"  # paragraph mark while joining lines


def tidy(s):
    """Collapse whitespace and merge adjacent bold runs: '**a** **b**' -> '**a b**'.
    Paragraph marks become blank lines."""
    s = re.sub(r"[^\S\u2029]+", " ", s).strip()
    s = re.sub(r"\s*\u2029[\s\u2029]*", PARA, s).strip(PARA + " ")
    while "** **" in s:
        s = s.replace("** **", " ")
    s = s.replace("****", "")
    s = re.sub(r" +([,.;:])", r"\1", s)
    return "\n\n".join(p.strip() for p in s.split(PARA))


def classify(prefix):
    """('label', key, label) | ('heading', title) | None for a line's bold prefix.

    The prefix may carry the value too ("Familia: Moraceae" all in bold): it is split on the
    first colon, or after the longest known label it starts with.
    """
    p = re.sub(r"\s+", " ", prefix).strip()
    if not p:
        return None
    head, sep, tail = p.partition(":")
    for cand in ([head] if sep else []) + [p]:
        n = norm(cand)
        if n in LABELS:
            return ("label", LABELS[n], cand.strip(), tail.strip() if sep and cand is head else "")
        if n in HEADINGS:
            return ("heading", cand.strip(" :"), tail.strip() if sep and cand is head else "")
    # "Familia Moraceae" without colon: longest known label at the start.
    for lab in sorted(LABELS, key=len, reverse=True):
        if norm(p).startswith(lab + " "):
            words = len(lab.split())
            parts = p.split(" ")
            return ("label", LABELS[lab], " ".join(parts[:words]), " ".join(parts[words:]))
    return None


def sheets(pdf, report=None):
    cur = None
    for page, kind, payload in stream(load(pdf)):
        if kind == "title":
            if cur:
                yield cur
            cur = {"title": payload, "pages": [page, page], "header": [], "sections": [], "target": None}
            continue
        if cur is None:
            continue
        cur["pages"][1] = page
        top = min(i["top"] for i in payload)
        gap = top - cur.get("last_top", top)
        cur["last_top"] = top
        prefix, rest = split_prefix(payload)
        c = classify(prefix)
        target = cur["target"]
        if (c is None and target is not None and cur["sections"] and target is cur["sections"][-1]["parts"]
                and not "".join(target).strip() and norm(prefix).startswith("geografica")):
            # "Distribución" / "geográfica" split over two lines.
            cur["sections"][-1]["title"] += " " + prefix.strip(" :")
            target.append(render(rest))
            continue
        if c is None and not prefix.strip():
            # Plain (not bold) label at the start of the line: "Nombre común: ficus …".
            m = re.match(r"\s*([^:]{3,25}):(.*)$", join(payload))
            if m and norm(m.group(1)) in LABELS:
                c = ("label", LABELS[norm(m.group(1))], m.group(1).strip(), m.group(2))
                rest = []
        if c and c[0] == "label":
            _, key, label, inline = c
            label = re.sub(r"\s+", " ", label).strip(" :")
            cur["header"].append({"key": key, "label": label, "parts": [inline, render(rest)]})
            cur["target"] = cur["header"][-1]["parts"]
        elif c and c[0] == "heading":
            _, title, inline = c
            cur["sections"].append({"title": title, "parts": [inline, render(rest)]})
            cur["target"] = cur["sections"][-1]["parts"]
        else:
            if report is not None and prefix.strip() and len(prefix.strip()) < 45:
                report.append((page, cur["title"], prefix.strip()))
            if cur["target"] is not None:
                # A new paragraph inside the same column (not across a column or page break).
                # A paragraph ends with "." or ":"; a larger gap after anything else is text
                # flowing around a photo.
                ends = re.sub(r"[\s*]+$", "", "".join(cur["target"]))[-1:] in (".", ":")
                cur["target"].append((PARA if 28 < gap < 120 and ends else "") + render(payload))
    if cur:
        yield cur


def finish(e):
    # "Familia" + ": Arecaceae" in separate runs leaves the colon at the start of the value.
    header = [{"key": h["key"], "label": h["label"], "value": tidy(" ".join(h["parts"])).lstrip(": ")}
              for h in e["header"]]
    get = lambda k: next((h["value"] for h in header if h["key"] == k and h["value"]), "")
    return {
        "title": e["title"],
        "pages": e["pages"],
        # A trailing number is a footnote call ("de Laub. 31"), not part of the name.
        "scientific_name": re.sub(r"\s+\d+$", "", get("scientific_name").replace("**", "").strip(" :")),
        "family": get("family").replace("**", ""),
        "header": [{"label": h["label"], "value": h["value"].replace("**", "")}
                   for h in header if h["key"] != "scientific_name" and h["value"]],
        "sections": [{"title": s["title"], "text": t} for s in e["sections"] if (t := tidy(" ".join(s["parts"])))],
    }


if __name__ == "__main__":
    report = [] if "--report" in sys.argv else None
    out = [finish(e) for e in sheets(sys.argv[1], report)]
    out = [e for e in out if e["scientific_name"]]
    if report is not None:
        for r in report:
            print(*r, sep=" | ")
    else:
        json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
