"""Rendier-silhouet (mm, y omhoog). Kijkt naar rechts."""
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union
from shapely import affinity

def ell(cx, cy, rx, ry, rot=0):
    e = affinity.scale(Point(cx, cy).buffer(1, 64), rx, ry)
    return affinity.rotate(e, rot, origin=(cx, cy))

def tube(pts, w):
    return LineString(pts).buffer(w / 2, 32)

# poten (voor/achter, twee per kant licht verspringend)
poten = [tube([(66, 36), (67, 4)], 9), tube([(54, 36), (53, 4)], 9),
         tube([(28, 36), (27, 4)], 9), tube([(14, 36), (13, 4)], 9)]
lijf = ell(40, 44, 30, 15)
hals = tube([(62, 48), (80, 70)], 16)
kop = ell(88, 74, 13, 9, -15)
snuit = tube([(92, 70), (106, 66)], 11)
staart = tube([(12, 48), (3, 55)], 9)
# geweien: twee takken, beam + tines
gew_a = [tube([(80, 82), (74, 96), (66, 106)], 9), tube([(74, 95), (62, 94)], 6.5), tube([(71, 100), (74, 112)], 9)]
gew_b = [tube([(90, 82), (96, 96), (104, 106)], 9), tube([(96, 95), (108, 94)], 6.5), tube([(99, 100), (96, 112)], 6.5)]
oor = ell(78, 82, 4, 8, 25)
kroon = ell(82, 78, 9, 8)

def silhouet():
    u = unary_union(poten + [lijf, hals, kop, snuit, staart, kroon] + gew_a + gew_b)
    return u.buffer(2.0, 32).buffer(-2.0, 32)
