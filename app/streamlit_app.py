import streamlit as st
from rapidfuzz import process, fuzz
import json, re, math
from pathlib import Path

st.set_page_config(page_title="Woodman's Waukesha Aisle Finder", layout="wide")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
KEYWORDS_JSON = DATA_DIR / "waukesha_aisles.keywords.json"
LAYOUT_JSON   = DATA_DIR / "waukesha_layout.json"

@st.cache_data
def load_data():
    with open(KEYWORDS_JSON) as f:
        aisles = json.load(f)
    with open(LAYOUT_JSON) as f:
        layout = json.load(f)
    corpus_terms, corpus_aisles = [], []
    for aisle, kws in aisles.items():
        for kw in kws:
            corpus_terms.append(kw)
            corpus_aisles.append(aisle)
    return aisles, layout, corpus_terms, corpus_aisles

def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s/+-]", "", s)
    return re.sub(r"\s+", " ", s)

def best_match(item: str, terms, aisles):
    if not terms:
        return None, None, 0
    q = normalize(item)
    match, score, idx = process.extractOne(q, terms, scorer=fuzz.WRatio)
    return aisles[idx], match, int(score)

def order_stops(stops, layout):
    coords = layout.get("coords") or {}
    if coords and all(s in coords for s in stops):
        # nearest-neighbor from a sensible start
        start = None
        ro = layout.get("route_order", [])
        for cand in ["Produce","Bakery"]:
            if cand in stops and cand in coords:
                start = cand; break
        if start is None:
            for s in ro:
                if s in stops and s in coords:
                    start = s; break
        start = start or stops[0]
        route = [start]
        remaining = set(stops) - {start}
        def dist(a,b):
            ax,ay = coords[a]; bx,by = coords[b]
            return math.hypot(ax-bx, ay-by)
        while remaining:
            last = route[-1]
            nxt = min(remaining, key=lambda s: dist(last, s))
            route.append(nxt)
            remaining.remove(nxt)
        return route
    ro = layout.get("route_order", [])
    ordered = [s for s in ro if s in stops]
    tail = [s for s in stops if s not in ordered]
    return ordered + tail

def main():
    st.title("Woodman's Waukesha Aisle Finder")

    if not KEYWORDS_JSON.exists() or not LAYOUT_JSON.exists():
        st.warning("Missing data JSONs. Put the PDFs in raw_pdfs/ and run the parser to generate them.")
        st.stop()

    aisles, layout, terms, aisles_for_terms = load_data()

    items_text = st.text_area("Paste your items (one per line):", height=220,
                              placeholder="bananas\nramen\ncake mix\ncoffee filters\nyogurt")
    items = [ln.strip() for ln in items_text.splitlines() if ln.strip()]

    if st.button("Find aisles"):
        rows = []
        for it in items:
            a, kw, score = best_match(it, terms, aisles_for_terms)
            rows.append({"Item": it, "Aisle/Area": a or "Unknown", "Matched keyword": kw or "", "Confidence": score})

        st.subheader("Matches")
        st.dataframe(rows, use_container_width=True)

        by_aisle = {}
        for r in rows:
            by_aisle.setdefault(r["Aisle/Area"], []).append(r["Item"])
        stops = [k for k in by_aisle.keys() if k != "Unknown"]
        ordered_stops = order_stops(stops, layout)

        st.subheader("Suggested walking route")
        for s in ordered_stops:
            st.markdown(f"**{s}**: " + ", ".join(by_aisle[s]))
        if "Unknown" in by_aisle:
            st.markdown("**Unknown**: " + ", ".join(by_aisle["Unknown"]))

        st.download_button(
            "Download CSV",
            data="Item,Aisle,Confidence\n" + "\n".join(f"{r['Item']},{r['Aisle/Area']},{r['Confidence']}" for r in rows),
            file_name="woodmans_waukesha_list.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()
