import re, json, sys, pathlib
import pdfplumber

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

# ---- Update these names to the actual downloaded filenames in raw_pdfs/ ----
SHOPPING_LIST_PDF = (
    ROOT / "raw_pdfs" / "woodmans-waukesha-shopping-list-13.pdf"
)  # Waukesha "Printable Shopping List"
STORE_MAP_PDF = (
    ROOT / "raw_pdfs" / "woodmans-waukesha-store-map-13.pdf"
)  # Waukesha "Store Map"

AISLE_HEADER_RE = re.compile(r"^\s*Aisle\s+(\d+)\s*$", re.I)
BULLET_RE = re.compile(r"^\s*[-•]\s*(.+?)\s*$")

DEPARTMENT_HINTS = [
    "Produce",
    "Bakery",
    "Frozen",
    "Dairy",
    "Liquor",
    "Meat",
    "Deli",
    "Seafood",
    "Health & Beauty",
]


def extract_shopping_list(pdf_path: pathlib.Path) -> dict:
    """Return {'1': [...], '2': [...], 'Produce': [...], ...}"""
    out = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            i = 0
            current_aisle = None
            while i < len(lines):
                m = AISLE_HEADER_RE.match(lines[i])
                if m:
                    current_aisle = m.group(1)
                    out.setdefault(current_aisle, [])
                    i += 1
                    # collect bullets until next "Aisle" header
                    while i < len(lines) and not AISLE_HEADER_RE.match(lines[i]):
                        b = BULLET_RE.match(lines[i])
                        if b:
                            label = b.group(1)
                            label = re.sub(
                                r"\s*/\s*", " / ", label
                            )  # normalize slashes a bit
                            out[current_aisle].append(label.lower())
                        i += 1
                    continue
                i += 1
    for k in list(out.keys()):
        out[k] = sorted(set(out[k]), key=str)
    return out


def extract_departments_from_map(pdf_path: pathlib.Path) -> list[str]:
    """Grab department words from the map text. If text is limited, fall back to common ones."""
    depts = set()
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = (page.extract_text() or "").lower()
                for hint in DEPARTMENT_HINTS:
                    if hint.lower() in text:
                        depts.add(hint)
    except Exception:
        pass
    for hint in ["Produce", "Bakery", "Frozen", "Dairy"]:
        depts.add(hint)
    return sorted(depts)


def build_layout(aisle_dict: dict, departments: list[str]) -> dict:
    numbered = sorted([int(k) for k in aisle_dict.keys() if k.isdigit()])
    numbered = [str(k) for k in numbered]
    front = [d for d in ["Produce", "Bakery"] if d in departments]
    back = [d for d in ["Frozen", "Dairy"] if d in departments]
    middle = [d for d in departments if d not in set(front + back)]
    route_order = front + numbered + middle + back
    return {
        "entrance": "front",
        "route_order": route_order,
        "coords": {},  # optional: fill later like {"12":[x,y]}
    }


def main():
    if not SHOPPING_LIST_PDF.exists() or not STORE_MAP_PDF.exists():
        sys.exit(
            "Put the two PDFs in raw_pdfs/ and update filenames at the top of this script."
        )
    aisles = extract_shopping_list(SHOPPING_LIST_PDF)
    departments = extract_departments_from_map(STORE_MAP_PDF)
    layout = build_layout(aisles, departments)

    (DATA / "waukesha_aisles.keywords.json").write_text(json.dumps(aisles, indent=2))
    (DATA / "waukesha_layout.json").write_text(json.dumps(layout, indent=2))

    print("Wrote:")
    print(" -", DATA / "waukesha_aisles.keywords.json")
    print(" -", DATA / "waukesha_layout.json")


if __name__ == "__main__":
    main()
