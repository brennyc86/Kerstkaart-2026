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

def boog(cx, cy, r, a0, a1, w=0.25, n=48):
    pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * t / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * t / n))) for t in range(n + 1)]
    return LineString(pts).buffer(w / 2, 4)

def maak_kunst(outline, P, itemsF, copB, backpads, vias, fps, ctx):
    from shapely.geometry import MultiPoint
    oog, knop, neus, jst = ctx['oog'], ctx['knop'], ctx['neus'], ctx['jst']
    F = []
    # ---------- voorkant: het oog (chip = pupil), wimpers, wenkbrauw
    F.append(boog(oog[0], oog[1], 3.25, 0, 360, 0.25, 72))
    for a in (30, 52, 74, 96, 118, 140):
        r0, r1 = 3.9, 5.4 if a not in (52, 96) else 6.0
        F.append(LineString([(oog[0] + r0 * math.cos(math.radians(a)), oog[1] + r0 * math.sin(math.radians(a))),
                             (oog[0] + r1 * math.cos(math.radians(a)), oog[1] + r1 * math.sin(math.radians(a)))]).buffer(0.13, 4))
    F.append(boog(oog[0], oog[1], 7.3, 40, 135, 0.3))
    # neus: ring om knop + LED
    nx, ny = (knop[0] + neus[0]) / 2, (knop[1] + neus[1]) / 2
    F.append(boog(nx, ny, 4.5, 0, 360, 0.25, 72))
    # JST: polariteit
    j1, j2 = ctx['jst1'], ctx['jst2']
    F.append(gecentreerd('+', j1[0] + 1.0, j1[1] + 1.35, 1.3, False))
    F.append(gecentreerd('-', j2[0] + 1.0, j2[1] - 1.35, 1.3, False))
    F.append(gecentreerd('BAT', j1[0] - 1.4, j1[1] + 2.9, 1.0, False))
    # kerstboodschap in het lijf
    ruim = outline.buffer(-1.6)
    def fit(s, cx, cy, maxw, hoogte, spiegel=False):
        while hoogte > 0.8:
            t = gecentreerd(s, cx, cy, hoogte, spiegel)
            bb = t.bounds
            if bb[2] - bb[0] <= maxw and ruim.contains(t): return t
            hoogte *= 0.95
        return gecentreerd(s, cx, cy, hoogte, spiegel)
    msg1 = fit(BOODSCHAP[0], 45.0, 41.6, 26.5, 3.9)
    msg2 = fit(BOODSCHAP[1], 45.0, 37.2, 26.5, 2.7)
    F += [msg1, msg2]
    # sneeuwvlokken en sterren in vrije plekken
    kopergebied = itemsF.buffer(1.3)
    vrij = outline.buffer(-2.0).difference(kopergebied).difference(unary_union([msg1.buffer(1.0), msg2.buffer(1.0)] + F[:-2]).buffer(1.0))
    plaatsen = []
    import random
    rnd = random.Random(2026)
    minx, miny, maxx, maxy = outline.bounds
    kand = [(rnd.uniform(minx, maxx), rnd.uniform(miny, maxy)) for _ in range(6000)]
    for (x, y) in kand:
        r = rnd.choice((1.1, 1.4, 1.8))
        if vrij.contains(Point(x, y).buffer(r + 0.3)) and all(math.hypot(x - a, y - b) > 6.0 for a, b, _ in plaatsen):
            plaatsen.append((x, y, r))
        if len(plaatsen) >= 16: break
    for i, (x, y, r) in enumerate(plaatsen):
        F.append(vlok(x, y, r, 8 * i) if i % 3 else ster(x, y, r * .9))

    # ---------- achterkant: labels, boodschap + naam, sneeuwvlokken (gespiegeld, leesbaar bij omdraaien)
    g = []
    def links(s, xr, y, h):      # tekst eindigt (in bordcoordinaten) bij xr en loopt naar kleinere x
        t = gecentreerd(s, 0, 0, h, True); b = t.bounds
        return affinity.translate(t, xr - b[2], y)
    def rechts(s, xl, y, h):
        t = gecentreerd(s, 0, 0, h, True); b = t.bounds
        return affinity.translate(t, xl - b[0], y)
    for x, y, w, h, n, lab in backpads:
        if lab == 'UPDI': g.append(links('UPDI 4k7', x - 3.6 - 1.9, y, 0.8))
        elif lab in ('VCC', 'GND'): g.append(gecentreerd(lab, x, y - h / 2 - 2.6, 0.8, True))
        elif lab == 'HV': g.append(links('HV: UPDI direct', x - 1.6, y, 0.8))
        elif lab == 'BT+': g.append(rechts('+ batterij', x + 4.6, y, 1.2))
        elif lab == 'BT-': g.append(rechts('- batterij', x + 4.6, y, 1.2))
    ruim_B = outline.buffer(-1.6)
    def fitB(s, cx, cy, maxw, h):
        while h > 0.8:
            t = gecentreerd(s, cx, cy, h, True); bb = t.bounds
            if bb[2] - bb[0] <= maxw and ruim_B.contains(t): return t
            h *= 0.95
        return gecentreerd(s, cx, cy, h, True)
    for t in (fitB(BOODSCHAP[0], 42.0, 41.0, 24.0, 3.4), fitB(BOODSCHAP[1], 42.0, 36.8, 24.0, 2.4), fitB(ONDERTITEL, 42.0, 32.6, 24.0, 1.6)):
        g.append(t)
    for (x, y, r, a) in ((52.5, 46.0, 1.7, 20), (30, 30.0, 1.6, 10), (56.5, 31.5, 1.5, 0)):
        v = vlok(x, y, r, a)
        if ruim_B.contains(v): g.append(v)
    return {'F': unary_union(F), 'B': unary_union(g)}
