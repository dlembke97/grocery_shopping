import os
import pathlib
import fitz

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_PDF = ROOT / "raw_pdfs" / "store-map-13.pdf"
OUT_IMG = ROOT / "data" / "store_map.png"
DPI = 250


def main() -> None:
    """Rasterize the store map PDF into a PNG image.

    The PDF may contain multiple pages but we only care about the first one.
    If the output image already exists the script exits quietly so it can be
    re-run without side effects.
    """
    if OUT_IMG.exists():
        print(f"{OUT_IMG} already exists, skipping")
        return
    if not RAW_PDF.exists():
        raise SystemExit(f"Missing PDF: {RAW_PDF}")

    OUT_IMG.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(RAW_PDF) as doc:
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=DPI)
        pix.save(OUT_IMG)
    print(f"Wrote {OUT_IMG}")


if __name__ == "__main__":
    main()
