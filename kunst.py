"""Silkscreen-kunst: kerstboodschap (achterkant), sneeuwvlokken (voorkant), pad-labels."""
import math
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely import affinity
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

BOODSCHAP = ['Zalig Kerstfeest', 'en een gelukkig 2027']
ONDERTITEL = 'Brendan  -  Kerstkaart 2026'
FONT = FontProperties(family='DejaVu Sans', weight='bold')

def tekst_geom(s, hoogte, font=FONT):
    """tekst als shapely-geometrie, linksonder op (0,0); hoogte = hoofdletterhoogte in mm"""
    tp = TextPath((0, 0), s, size=10, prop=font)
    polys = [Polygon(p) for p in tp.to_polygons() if len(p) > 2]
    g = None
    for p in sorted(polys, key=lambda p: -p.area):      # even-odd: gaten in letters
        p = p.buffer(0)
        g = p if g is None else g.symmetric_difference(p)
    sc = hoogte / 7.3          # hoofdletter 'H' is ~7.3 hoog bij size 10
    return affinity.scale(g, sc, sc, origin=(0, 0))

def gecentreerd(s, cx, cy, hoogte, spiegel):
    g = tekst_geom(s, hoogte)
    b = g.bounds
    g = affinity.translate(g, -(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2)
    if spiegel: g = affinity.scale(g, -1, 1, origin=(0, 0))
    return affinity.translate(g, cx, cy)

def vlok(cx, cy, r, hoek=0):
    arms = []
    for k in range(6):
        a = math.radians(hoek + 60 * k)
        d = (math.cos(a), math.sin(a)); n = (-d[1], d[0])
        arms.append(LineString([(cx, cy), (cx + d[0] * r, cy + d[1] * r)]))
        for t, l in ((0.55, 0.38), (0.8, 0.25)):
            bx, by = cx + d[0] * r * t, cy + d[1] * r * t
            for sgn in (1, -1):
                arms.append(LineString([(bx, by), (bx + (d[0] * .6 + n[0] * sgn * .8) * r * l, by + (d[1] * .6 + n[1] * sgn * .8) * r * l)]))
    return unary_union(arms).buffer(0.16, 4)

def ster(cx, cy, r):
    pts = []
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.42
        a = math.radians(90 + 36 * k)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return Polygon(pts)

def maak_kunst(outline, P, copF, copB, backpads, vias, fps):
    # ---------- achterkant: boodschap (gespiegeld zodat hij leesbaar is als je de kaart omdraait)
    xmid = 47.5
    g = []
    ruimte_B = outline.buffer(-3.0).difference(unary_union([box(x - w / 2 - 1, y - h / 2 - 1, x + w / 2 + 1, y + h / 2 + 1) for x, y, w, h, n, l in backpads]))
    ruim = outline.buffer(-1.6)
    def fit(s, cx, cy, maxw, hoogte):
        while hoogte > 0.8:
            t = gecentreerd(s, cx, cy, hoogte, True)
            bb = t.bounds
            if bb[2] - bb[0] <= maxw and ruim.contains(t): return t
            hoogte *= 0.95
        return gecentreerd(s, cx, cy, hoogte, True)
    XC = 41.8
    t1 = fit(BOODSCHAP[0], XC, 44.0, 29.0, 5.0)
    t2 = fit(BOODSCHAP[1], XC, 39.3, 29.0, 3.4)
    t3 = fit(ONDERTITEL, XC, 34.8, 26.0, 1.9)
    for t in (t1, t2, t3): g.append(t)
    # sneeuwvlokken rond de tekst
    for (x, y, r, a) in ((29.5, 31.5, 2.0, 10), (54.5, 31.0, 1.8, 25), (51.5, 47.0, 1.5, 0), (37.5, 30.2, 1.4, 15), (45.5, 30.0, 1.5, 30)):
        v = vlok(x, y, r, a)
        if ruimte_B.contains(v): g.append(v)
    # labels bij de achterpads (versprongen zodat ze niet over elkaar lopen)
    for x, y, w, h, n, lab in backpads:
        if lab == 'UPDI': g.append(gecentreerd(lab, x, y + h / 2 + 0.85, 0.8, True))
        elif lab in ('VCC', 'GND'): g.append(gecentreerd(lab, x, y - h / 2 - 0.85, 0.8, True))
        elif lab == 'HV': g.append(gecentreerd(lab + ' (UPDI)', x + 3.6, y - 0.9, 0.8, True))
        elif lab == 'BT+': g.append(gecentreerd(lab, x, y - w / 2 - 1.1, 1.2, True))
        elif lab == 'BT-': g.append(gecentreerd(lab, x, y + w / 2 + 1.1, 1.2, True))
    B = unary_union(g)

    # ---------- voorkant: sneeuwvlokken en sterren in vrije plekken + jaartal
    kopergebied = copF.buffer(1.3)
    vrij = outline.buffer(-2.0).difference(kopergebied)
    F = []
    plaatsen = []
    import random
    rnd = random.Random(2026)
    kand = []
    minx, miny, maxx, maxy = outline.bounds
    for _ in range(4000):
        x, y = rnd.uniform(minx, maxx), rnd.uniform(miny, maxy)
        if vrij.contains(Point(x, y)): kand.append((x, y))
    for (x, y) in kand:
        r = rnd.choice((1.1, 1.4, 1.8))
        if vrij.contains(Point(x, y).buffer(r + 0.3)) and all(math.hypot(x - a, y - b) > 5.5 for a, b, _ in plaatsen):
            plaatsen.append((x, y, r))
        if len(plaatsen) >= 16: break
    for i, (x, y, r) in enumerate(plaatsen):
        F.append(vlok(x, y, r, 8 * i) if i % 3 else ster(x, y, r * .9))
    return {'F': unary_union(F) if F else Point(0, 0).buffer(0), 'B': B}
