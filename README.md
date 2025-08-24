# Woodman's Waukesha Aisle Finder

Find aisles for your grocery list and get a fast walking route through the Waukesha store.

## Project layout

- `raw_pdfs/` – store map PDF (`store-map-13.pdf`) with the map on page 1 and an aisle directory on page 2
- `scripts/parse_waukesha_pdfs.py` – extracts aisle keywords and a rough layout JSON
- `scripts/rasterize_map.py` – rasterizes the map PDF to `data/store_map.png`
- `scripts/build_navmesh.py` – builds a navigation mask and stop coordinates
- `data/` – generated JSON and PNG files used by the app
- `app/router.py` – A* routing utilities
- `app/streamlit_app.py` – Streamlit interface for searching items

## Setup

Install dependencies using [Pipenv](https://pipenv.pypa.io/):

```bash
pipenv --python 3.11
pipenv install
```

## Generate map and navigation data

1. Download the Waukesha store map PDF and save it as `raw_pdfs/store-map-13.pdf`.
2. Parse aisle keywords and rasterize the map:

   ```bash
   pipenv run python scripts/parse_waukesha_pdfs.py
   pipenv run python scripts/rasterize_map.py
   pipenv run python scripts/build_navmesh.py
   ```

   These commands write `data/waukesha_aisles.keywords.json`, `data/waukesha_layout.json`,
   `data/store_map.png`, `data/navmask.png`, and `data/nav.json`.
   You can run `make build` to execute the whole sequence or `make nav` to rebuild the map assets.

## Run the app

```bash
pipenv run streamlit run app/streamlit_app.py
```

