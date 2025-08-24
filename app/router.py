import json
import math
import heapq
import pathlib
from typing import Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NAV_JSON_PATH = DATA / "nav.json"
NAVMASK_PATH = DATA / "navmask.png"
DIST_CACHE_PATH = DATA / "dist_cache.json"

_NEIGHBORS = [
    (-1, -1), (0, -1), (1, -1),
    (-1, 0),          (1, 0),
    (-1, 1),  (0, 1),  (1, 1),
]

_nav_data = None
_nav_mask = None
_dist_cache: Dict[Tuple[str, str], float] = {}


def _load() -> None:
    global _nav_data, _nav_mask, _dist_cache
    if _nav_data is not None:
        return
    if not NAV_JSON_PATH.exists() or not NAVMASK_PATH.exists():
        raise FileNotFoundError("Navmesh files not found")
    with open(NAV_JSON_PATH) as f:
        _nav_data = json.load(f)
    _nav_mask = cv2.imread(str(NAVMASK_PATH), cv2.IMREAD_GRAYSCALE)
    if DIST_CACHE_PATH.exists():
        with open(DIST_CACHE_PATH) as f:
            _dist_cache = json.load(f)


def _heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _astar(start: Tuple[int, int], goal: Tuple[int, int]) -> Tuple[float, List[Tuple[int, int]]]:
    _load()
    h, w = _nav_mask.shape
    start = (int(round(start[0])), int(round(start[1])))
    goal = (int(round(goal[0])), int(round(goal[1])))
    open_set = [(0 + _heuristic(start, goal), 0, start)]
    came: Dict[Tuple[int, int], Tuple[int, int]] = {}
    gscore = {start: 0}
    while open_set:
        _, g, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came:
                current = came[current]
                path.append(current)
            path.reverse()
            return g, path
        cx, cy = current
        for dx, dy in _NEIGHBORS:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            if _nav_mask[ny, nx] == 0:
                continue
            step = math.hypot(dx, dy)
            ng = g + step
            if ng < gscore.get((nx, ny), float("inf")):
                gscore[(nx, ny)] = ng
                came[(nx, ny)] = current
                f = ng + _heuristic((nx, ny), goal)
                heapq.heappush(open_set, (f, ng, (nx, ny)))
    return float("inf"), []


def shortest_distance(a_label: str, b_label: str) -> float:
    _load()
    key = tuple(sorted([a_label, b_label]))
    if key in _dist_cache:
        return _dist_cache[key]
    stops = _nav_data["stops"]
    dist, _ = _astar(tuple(stops[a_label]), tuple(stops[b_label]))
    _dist_cache[key] = dist
    with open(DIST_CACHE_PATH, "w") as f:
        json.dump(_dist_cache, f, indent=2)
    return dist


def solve_route(stops: List[str], start: str) -> List[str]:
    _load()
    stops = list(dict.fromkeys(stops))
    if start not in stops:
        stops.insert(0, start)
    route = [start]
    remaining = set(stops) - {start}
    while remaining:
        last = route[-1]
        nxt = min(remaining, key=lambda s: shortest_distance(last, s))
        route.append(nxt)
        remaining.remove(nxt)
    # single 2-opt pass
    for i in range(1, len(route) - 2):
        for j in range(i + 1, len(route) - 1):
            a, b, c, d = route[i - 1], route[i], route[j], route[j + 1]
            if (
                shortest_distance(a, b) + shortest_distance(c, d)
                > shortest_distance(a, c) + shortest_distance(b, d)
            ):
                route[i:j + 1] = reversed(route[i:j + 1])
    return route


def render_path(labels: List[str]) -> Image.Image:
    _load()
    img = Image.open(_nav_data["image_path"]).convert("RGB")
    draw = ImageDraw.Draw(img)
    stops = _nav_data["stops"]
    for i in range(len(labels) - 1):
        _, path = _astar(tuple(stops[labels[i]]), tuple(stops[labels[i + 1]]))
        if path:
            draw.line(path, fill=(255, 0, 0), width=3)
    for lab in labels:
        x, y = stops[lab]
        r = 4
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(0, 0, 255))
        draw.text((x + r + 2, y - r - 2), lab, fill=(0, 0, 0))
    return img
