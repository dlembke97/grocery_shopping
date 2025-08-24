import json
import math
import re
from pathlib import Path

import streamlit as st
from rapidfuzz import fuzz, process
from app.router import solve_route, render_path

st.set_page_config(page_title="Woodman's Waukesha Aisle Finder", layout="wide")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
KEYWORDS_JSON = DATA_DIR / "waukesha_aisles.keywords.json"
LAYOUT_JSON = DATA_DIR / "waukesha_layout.json"
SECTION_JSON = DATA_DIR / "store_sections.keywords.json"
NAV_JSON = DATA_DIR / "nav.json"
NAV_MASK = DATA_DIR / "navmask.png"

@st.cache_data
def load_data():
    with open(KEYWORDS_JSON) as f:
        aisles = json.load(f)
    with open(LAYOUT_JSON) as f:
        layout = json.load(f)
    with open(SECTION_JSON) as f:
        sections = json.load(f)
    corpus_terms, corpus_aisles = [], []
    for aisle, kws in aisles.items():
        for kw in kws:
            corpus_terms.append(kw)
            corpus_aisles.append(aisle)
    section_terms, section_names = [], []
    for sec, kws in sections.items():
        for kw in kws:
            section_terms.append(kw)
            section_names.append(sec)
    return aisles, layout, corpus_terms, corpus_aisles, section_terms, section_names

def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s/+-]", "", s)
    return re.sub(r"\s+", " ", s)

def best_match(item: str, terms, aisles, score_cutoff: int = 75):
    """Return the best aisle match for ``item`` or ``None`` if below cutoff."""
    if not terms:
        return None, None, 0
    q = normalize(item)
    result = process.extractOne(q, terms, scorer=fuzz.WRatio, score_cutoff=score_cutoff)
    if result is None:
        return None, None, 0
    match, score, idx = result
    return aisles[idx], match, int(score)

def main():
    st.title("Woodman's Waukesha Aisle Finder")

    if not KEYWORDS_JSON.exists() or not LAYOUT_JSON.exists():
        st.warning("Missing data JSONs. Put the PDFs in raw_pdfs/ and run the parser to generate them.")
        st.stop()

    aisles, layout, terms, aisles_for_terms, section_terms, section_names = load_data()

    items_text = st.text_area(
        "Paste your items (one per line):",
        height=220,
        placeholder="bananas\nramen\ncake mix\ncoffee filters\nyogurt",
    )
    items = [ln.strip() for ln in items_text.splitlines() if ln.strip()]

    if st.button("Find aisles"):
        rows = []
        for it in items:
            a, kw, score = best_match(it, terms, aisles_for_terms)
            if a is None:
                a, kw, score = best_match(it, section_terms, section_names, score_cutoff=60)
            rows.append({"Item": it, "Aisle/Area": a or "Unknown", "Matched keyword": kw or "", "Confidence": score})

        st.subheader("Matches")
        st.dataframe(rows, use_container_width=True)

        by_aisle = {}
        for r in rows:
            by_aisle.setdefault(r["Aisle/Area"], []).append(r["Item"])
        stops = sorted(k for k in by_aisle.keys() if k != "Unknown")

        img = None
        if NAV_JSON.exists() and NAV_MASK.exists():
            with open(NAV_JSON) as f:
                nav = json.load(f)
            if "Entrance" in nav.get("stops", {}):
                start = "Entrance"
            elif "Produce" in nav.get("stops", {}):
                start = "Produce"
            else:
                start = stops[0] if stops else "Entrance"
            ordered_stops = solve_route(stops, start)
            img = render_path(ordered_stops)
        else:
            st.warning(
                "Navigation files missing. Run:
"
                "pipenv run python scripts/rasterize_map.py
"
                "pipenv run python scripts/build_navmesh.py"
            )
            ordered_stops = stops

        st.subheader("Suggested walking route")
        for s in ordered_stops:
            st.markdown(f"**{s}**: " + ", ".join(by_aisle[s]))
        if "Unknown" in by_aisle:
            st.markdown("**Unknown**: " + ", ".join(by_aisle["Unknown"]))
        if img is not None:
            st.image(img)

        st.download_button(
            "Download CSV",
            data="Item,Aisle,Confidence\n" + "\n".join(
                f"{r['Item']},{r['Aisle/Area']},{r['Confidence']}" for r in rows
            ),
            file_name="woodmans_waukesha_list.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()
