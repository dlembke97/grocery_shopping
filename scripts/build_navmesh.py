import json
import os
import pathlib
from typing import List

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STORE_IMG = DATA / "store_map.png"
NAVMASK_IMG = DATA / "navmask.png"
NAV_JSON = DATA / "nav.json"
KEYWORDS_JSON = DATA / "waukesha_aisles.keywords.json"
LAYOUT_JSON = DATA / "waukesha_layout.json"

CANNY_LOW = 50
CANNY_HIGH = 150
MORPH_KERNEL = 9
MIN_COMPONENT_AREA = 500
PEAK_MIN_DIST = 40
ENTRANCE_EDGE = os.getenv("ENTRANCE_EDGE", "bottom")  # top|bottom|left|right


def load_keywords() -> List[int]:
    with open(KEYWORDS_JSON) as f:
        data = json.load(f)
    ids = sorted(int(k) for k in data.keys() if k.isdigit())
    return ids


def determine_direction(nums: List[int]) -> int:
    if not LAYOUT_JSON.exists():
        return 1
    with open(LAYOUT_JSON) as f:
        layout = json.load(f)
    ro = layout.get("route_order", [])
    first_num = next((int(s) for s in ro if s.isdigit()), nums[0])
    if first_num == nums[-1]:
        return -1
    return 1


def preprocess(img: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    edges = cv2.Canny(blur, CANNY_LOW, CANNY_HIGH)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (MORPH_KERNEL, MORPH_KERNEL))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    _, mask = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY)
    walkable = cv2.bitwise_not(mask)
    # remove tiny obstacle specks
    inv = 255 - walkable
    n, labels, stats, _ = cv2.connectedComponentsWithStats(inv)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < MIN_COMPONENT_AREA:
            inv[labels == i] = 0
    walkable = 255 - inv
    return walkable


def find_corridors(mask: np.ndarray, expected: int) -> List[int]:
    obstacles = (mask == 0).astype(np.uint8)
    profile = obstacles.sum(axis=0).astype(np.float32)
    profile = cv2.GaussianBlur(profile, (51, 1), 0)
    mins = []
    last = -1e9
    for x in range(1, profile.shape[0] - 1):
        if profile[x] < profile[x - 1] and profile[x] < profile[x + 1]:
            if x - last >= PEAK_MIN_DIST:
                mins.append(x)
                last = x
    if len(mins) != expected:
        print(
            f"Warning: expected {expected} corridors, detected {len(mins)}; using even spacing"
        )
        mins = np.linspace(0, mask.shape[1] - 1, expected + 2)[1:-1].astype(int).tolist()
    return mins


def column_max(dist: np.ndarray, x: int) -> int:
    col = dist[:, x]
    return int(np.argmax(col))


def find_edge_point(dist: np.ndarray, mask: np.ndarray, edge: str) -> tuple[int, int]:
    h, w = mask.shape
    margin_y = max(1, h // 20)
    margin_x = max(1, w // 20)
    best = (-1, -1)
    bestd = -1.0
    if edge in ("top", "bottom"):
        ys = range(0, margin_y) if edge == "top" else range(h - margin_y, h)
        for y in ys:
            for x in range(w):
                if mask[y, x]:
                    d = dist[y, x]
                    if d > bestd:
                        bestd = d
                        best = (x, y)
    else:
        xs = range(0, margin_x) if edge == "left" else range(w - margin_x, w)
        for x in xs:
            for y in range(h):
                if mask[y, x]:
                    d = dist[y, x]
                    if d > bestd:
                        bestd = d
                        best = (x, y)
    return best


def nearest_walkable(mask: np.ndarray, dist: np.ndarray, x: int, y: int) -> tuple[int, int]:
    h, w = mask.shape
    if mask[min(max(y, 0), h - 1), min(max(x, 0), w - 1)]:
        return (min(max(x, 0), w - 1), min(max(y, 0), h - 1))
    best = (x, y)
    bestd = -1.0
    for r in range(1, 20):
        for ny in range(max(0, y - r), min(h, y + r + 1)):
            for nx in range(max(0, x - r), min(w, x + r + 1)):
                if mask[ny, nx]:
                    d = dist[ny, nx]
                    if d > bestd:
                        bestd = d
                        best = (nx, ny)
        if bestd >= 0:
            break
    return best


def main() -> None:
    if NAVMASK_IMG.exists() and NAV_JSON.exists():
        print("Navmesh already built; remove files to rebuild")
        return
    if not STORE_IMG.exists():
        raise SystemExit("Run rasterize_map.py first")

    img = cv2.imread(str(STORE_IMG), cv2.IMREAD_GRAYSCALE)
    mask = preprocess(img)
    cv2.imwrite(str(NAVMASK_IMG), mask)

    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 3)
    aisle_ids = load_keywords()
    corridors = find_corridors(mask, len(aisle_ids))
    direction = determine_direction(aisle_ids)
    ordered_ids = aisle_ids if direction == 1 else list(reversed(aisle_ids))
    ordered_corridors = corridors if direction == 1 else list(reversed(corridors))

    stops: dict[str, list[int]] = {}
    for aid, x in zip(ordered_ids, ordered_corridors):
        y = column_max(dist, x)
        stops[str(aid)] = [int(x), int(y)]

    entrance = find_edge_point(dist, mask, ENTRANCE_EDGE)
    stops["Entrance"] = list(entrance)
    # Departments near entrance edge; tweak manually later if needed
    prod = nearest_walkable(mask, dist, entrance[0] + 50, entrance[1])
    stops["Produce"] = list(prod)
    bak = nearest_walkable(mask, dist, entrance[0] + 100, entrance[1])
    stops["Bakery"] = list(bak)

    opp_edge = {
        "top": "bottom",
        "bottom": "top",
        "left": "right",
        "right": "left",
    }[ENTRANCE_EDGE]
    frozen = find_edge_point(dist, mask, opp_edge)
    stops["Frozen"] = list(frozen)
    dairy = nearest_walkable(mask, dist, frozen[0] + 100, frozen[1])
    stops["Dairy"] = list(dairy)

    data = {
        "image_path": str(STORE_IMG),
        "mask_path": str(NAVMASK_IMG),
        "pixel_scale": 1.0,
        "stops": stops,
        "meta": {"notes": "auto-generated", "version": 1},
    }
    NAV_JSON.write_text(json.dumps(data, indent=2))

    print(f"Detected {len(corridors)} corridors -> {len(aisle_ids)} aisles")
    print(f"Wrote {NAVMASK_IMG} and {NAV_JSON}")


if __name__ == "__main__":
    main()
