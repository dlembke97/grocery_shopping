import re, json, sys, pathlib
import pdfplumber

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

# ---- Update this name to the actual downloaded filename in raw_pdfs/ ----
STORE_PDF = ROOT / "raw_pdfs" / "woodmans-waukesha-store-map-13.pdf"  # map p1, directory p2

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


def extract_aisle_directory(pdf_path: pathlib.Path) -> dict:
    """Parse page 2 directory into {"1": ["item", ...], "MEAT": [...], ...}."""
    out: dict[str, list[str]] = {}
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 2:
            return out
        page = pdf.pages[1]
        words = page.extract_words(use_text_flow=True)
        current: list[str] = []
        skip = {"open", "hours", "days", "week", "welcome", "waukesha", "to", "store", "directory"}
        for w in words:
            token = w["text"]
            low = token.lower()
            if low in skip:
                continue
            if re.search(r"\d", token) and not re.fullmatch(r"[0-9A-Z,]+", token):
                continue
            if re.fullmatch(r"[0-9A-Z,]+", token):
                item = " ".join(current).strip()
                if item:
                    for aisle in token.split(","):
                        aisle = aisle.strip()
                        out.setdefault(aisle, []).append(item.lower())
                current = []
            else:
                current.append(token)
    for k in list(out.keys()):
        out[k] = sorted(set(out[k]))
    return out


def extract_departments_from_map(pdf_path: pathlib.Path) -> list[str]:
    """Grab department words from the map (first page)."""
    depts = set()
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]  # first page is the store map
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
    if not STORE_PDF.exists():
        sys.exit(
            "Put the store PDF in raw_pdfs/ and update the filename at the top of this script."
        )
    aisles = extract_aisle_directory(STORE_PDF)
    departments = extract_departments_from_map(STORE_PDF)
    layout = build_layout(aisles, departments)

    (DATA / "waukesha_aisles.keywords.json").write_text(json.dumps(aisles, indent=2))
    (DATA / "waukesha_layout.json").write_text(json.dumps(layout, indent=2))

    print("Wrote:")
    print(" -", DATA / "waukesha_aisles.keywords.json")
    print(" -", DATA / "waukesha_layout.json")


if __name__ == "__main__":
    main()
