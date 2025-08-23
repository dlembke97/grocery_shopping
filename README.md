# Woodman's Waukesha Aisle Finder

Find aisles for your grocery list and get a fast walking route through the Waukesha store.

## Project layout

- `raw_pdfs/` – store PDF (`woodmans-waukesha-store-map-13.pdf`) with the map on page 1 and an aisle directory on page 2
- `scripts/parse_waukesha_pdfs.py` – extracts aisle keywords and a rough layout JSON
- `data/` – generated JSON files used by the app
- `app/streamlit_app.py` – simple Streamlit interface for searching items

## Setup

Install dependencies using [Pipenv](https://pipenv.pypa.io/):

```bash
pipenv --python 3.11
pipenv install
```

## Generate the data JSONs

1. Download `woodmans-waukesha-store-map-13.pdf` and place it in `raw_pdfs/`.
2. Run the parser:

```bash
pipenv run python scripts/parse_waukesha_pdfs.py
```

This writes `data/waukesha_aisles.keywords.json` and `data/waukesha_layout.json`.

## Run the app

```bash
pipenv run streamlit run app/streamlit_app.py
```

