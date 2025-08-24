.PHONY: nav build run

nav:
	pipenv run python scripts/rasterize_map.py
	pipenv run python scripts/build_navmesh.py

build:
	pipenv run python scripts/parse_waukesha_pdfs_v2.py --debug || true
	$(MAKE) nav

run:
	pipenv run streamlit run app/streamlit_app.py
