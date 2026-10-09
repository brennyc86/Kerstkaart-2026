"""Kerstkaart 2026 (rendier) - volledige generator.

Maakt: Gerbers + boorbestand (JLCPCB-klaar), BOM, CPL, KiCad-PCB en render.
Alle onderdelen gebruiken de echte KiCad-bibliotheek-footprints (map footprints/).
Coordinaten: echte mm, y omhoog, oorsprong linksonder.
"""
import math, os, re, sys, json, zipfile
from collections import OrderedDict
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, box
from shapely.ops import unary_union, nearest_points
from shapely import affinity
from shape import silhouet
from ketting import keten, S
from sexp import parse, dump, Q
from kunst import maak_kunst

CLR, EDGE, TW = 0.2, 0.4, 0.25
OUT = 'productie'
os.makedirs(OUT, exist_ok=True)

outline = affinity.scale(silhouet(), S, S, origin=(0, 0)).simplify(0.05)
inner_led = outline.buffer(-1.9)

# ------------------------------------------------------------------ board / DRC
class Board:
    def __init__(s): s.items = []            # (geom, net, laag, soort)
    def vrij(s, geom, net, lagen):
        if not outline.buffer(-EDGE).contains(geom): return False
        for g, n, l, k in s.items:
            if k == 'keep' or (n and n == net): continue
            if l in lagen and g.distance(geom) < CLR: return False
        return True
    def add(s, geom, net, laag, kind): s.items.append((geom, net, laag, kind))

B = Board()
nets = OrderedDict([('GND', 1), ('VCC', 2)])
def net(n):
    if n and n not in nets: nets[n] = len(nets) + 1
    return n

tracks, vias, fps, backpads = [], [], [], []

def track(pts, netn, laag='F', w=TW):
    net(netn)
    for a, b in zip(pts, pts[1:]): tracks.append((a, b, w, laag, netn))
    B.add(LineString(pts).buffer(w / 2, 8), netn, laag, 'track')

def via(x, y, netn):
    net(netn); vias.append((x, y, netn))
    g = Point(x, y).buffer(0.3, 16)
    B.add(g, netn, 'F', 'via'); B.add(g, netn, 'B', 'via')

# ------------------------------------------------------------------ footprints uit bibliotheek
FPDIR = 'footprints'
_cache = {}
def lib(naam):
    if naam not in _cache: _cache[naam] = parse(open(f'{FPDIR}/{naam}.kicad_mod').read())
    return _cache[naam]

def kids(node, key): return [c for c in node if isinstance(c, list) and c and c[0] == key]
def kid(node, key):
    k = kids(node, key); return k[0] if k else None
def num(v): return float(v)

def pad_defs(naam):
    """[(nr, lx, ly(y-omhoog), w, h)] - custom pads worden vervangen door normale pennen"""
    res = []
    for p in kids(lib(naam), 'pad'):
        nr = p[1]; at = kid(p, 'at'); sz = kid(p, 'size')
        if p[3] == 'np_thru_hole': continue
        w, h = num(sz[1]), num(sz[2])
        lx, ly = num(at[1]), -num(at[2])
        if p[3] == 'custom': w, h = (0.8, 0.2) if abs(abs(lx) - 1.45) < .01 else (0.2, 0.8)
        res.append((nr, lx, ly, w, h))
    return res

def rot(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)

def pad_geoms(naam, x, y, th):
    out = []
    for nr, lx, ly, w, h in pad_defs(naam):
        g = affinity.rotate(box(lx - w / 2, ly - h / 2, lx + w / 2, ly + h / 2), math.degrees(th), origin=(0, 0))
        out.append((nr, affinity.translate(g, x, y), rot((lx, ly), th)))
    return out

def place(ref, naam, x, y, th, netmap, val, lcsc, reg=True):
    """Zet footprint; netmap {padnr: net}. Geeft {padnr: (x,y)} van padcentra."""
    centers = {}
    for nr, g, c in pad_geoms(naam, x, y, th):
        n = netmap.get(nr, '')
        net(n)
        if reg: B.add(g, n, 'F', 'pad')
        centers.setdefault(nr, (x + c[0], y + c[1]))
    fps.append(dict(ref=ref, lib=naam, x=x, y=y, th=th, netmap=netmap, val=val, lcsc=lcsc))
    return centers

# ------------------------------------------------------------------ onderdelen
QFN, LEDF, RF, CF, SWF, JSTF = ('VQFN-20-1EP_3x3mm_P0.4mm_EP1.7x1.7mm', 'LED_SK6812_EC15_1.5x1.5mm', 'R_0603_1608Metric',
                                'C_0603_1608Metric', 'SW_SPST_B3U-1000P', 'JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal')
from ketting import OOG_MM, KNOP_MM, NEUS_MM
CX, CY = OOG_MM
def qp(n):   # padcentrum van QFN-pen n (1..20), y omhoog
    if n <= 5: return (CX - 1.45, CY + 0.8 - (n - 1) * 0.4)
    if n <= 10: return (CX - 0.8 + (n - 6) * 0.4, CY - 1.45)
    if n <= 15: return (CX + 1.45, CY - 0.8 + (n - 11) * 0.4)
    return (CX + 0.8 - (n - 16) * 0.4, CY + 1.45)


import heapq
_vg = None
def poly_path(a, b):
    """kortste pad binnen het bord (zichtbaarheidsgraaf over de bochtpunten)"""
    global _vg
    pol = outline.buffer(-0.9).simplify(0.15)
    if _vg is None:
        _vg = [c for ring in [pol.exterior] + list(pol.interiors) for c in ring.coords[:-1]] if pol.geom_type == 'Polygon' else []
    pts = [a, b] + _vg
    area = pol.buffer(0.02)
    def ok(p, q): return area.contains(LineString([p, q]))
    dist = {0: 0.0}; prev = {}; pq = [(0.0, 0)]; done = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in done: continue
        done.add(u)
        if u == 1: break
        for v in range(len(pts)):
            if v in done or v == u: continue
            if not ok(pts[u], pts[v]): continue
            nd = d + math.dist(pts[u], pts[v])
            if nd < dist.get(v, 1e9): dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
    if 1 not in prev and 1 not in done: return None
    path = [1]
    while path[-1] != 0: path.append(prev[path[-1]])
    return [pts[i] for i in reversed(path)]

def route_free(a, b, netn, w=0.2, laag='F', wp=()):
    """kortste geldige route a->b (rechte lijn, knikken, omwegen); waarschuwt als niets past"""
    for r in routes(a, b, list(wp)):
        ln = LineString(r).buffer(w / 2, 8)
        if B.vrij(ln, netn, [laag]):
            track(r, netn, laag, w); return r
    print('WAARSCHUWING: geen route voor', netn, a, b)
    r = [a, b]; track(r, netn, laag, w); return r

def routes(a, b, wp):
    yield [a] + wp + [b]
    dx, dy = b[0] - a[0], b[1] - a[1]
    for mid in ((b[0], a[1]), (a[0], b[1])): yield [a] + wp + [mid, b]
    L = math.hypot(dx, dy) or 1
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    for off in (2, -2, 4, -4, 6, -6, 9, -9, 13, -13): yield [a] + wp + [(mx - dy / L * off, my + dx / L * off), b]
    m = min(abs(dx), abs(dy))
    if m > 0.3:
        yield [a] + wp + [(a[0] + math.copysign(m, dx), a[1] + math.copysign(m, dy)), b]
        yield [a] + wp + [(b[0] - math.copysign(m, dx), b[1] - math.copysign(m, dy)), b]
    D = 1.4
    diag = [(D, D), (D, -D), (-D, D), (-D, -D)]
    for da in diag:                                   # eerst diagonaal weg van het pad (draai-om bij tak-uiteinden)
        yield [a, (a[0] + da[0], a[1] + da[1])] + wp + [b]
    for db in diag:
        yield [a] + wp + [(b[0] + db[0], b[1] + db[1]), b]
    for da in diag:
        for db in diag:
            yield [a, (a[0] + da[0], a[1] + da[1])] + wp + [(b[0] + db[0], b[1] + db[1]), b]
    vp = poly_path(a, b)
    if vp: yield vp

# U1 = oog van Rudolf. pen 3 GND, 4 VCC, 8 PA7 (knop), 15 PC0 (data), 19 UPDI/PA0, 21 = EP (GND)
place('U1', QFN, CX, CY, 0, {'3': 'GND', '4': 'VCC', '8': 'BTN', '15': 'DATA0', '19': 'UPDI0', '21': 'GND'},
      'ATtiny1616-MNR (VQFN-20)', 'C507118')
track([qp(3), (CX - 0.5, CY)], 'GND', w=0.2)
track([qp(3), (CX - 2.3, CY), (CX - 3.1, CY + 0.9), (CX - 3.1, CY + 1.6)], 'GND', w=0.2)
track([qp(4), (CX - 2.4, CY - 0.4), (CX - 3.0, CY - 1.0)], 'VCC', w=0.2)
via(CX - 3.0, CY - 1.0, 'VCC')
c1 = place('C1', CF, CX - 4.8, CY - 0.4, 0, {'1': 'GND', '2': 'VCC'}, '100nF 0603', 'C14663')
track([(CX - 3.0, CY - 1.0), c1['2']], 'VCC', w=0.2)
r1 = place('R1', RF, CX + 4.725, CY + 0.8, 0, {'1': 'DATA0', '2': 'DATA1'}, '330R 0603', 'C23138')
track([qp(15), r1['1']], 'DATA0', w=0.2)
DATA_START = r1['2']
r2 = place('R2', RF, CX - 0.4, CY + 4.8, math.pi / 2, {'1': 'UPDI0', '2': 'UPDI_R'}, '4.7k 0603', 'C23162')
track([qp(19), r2['1']], 'UPDI0', w=0.2)
# knopje = neus van Rudolf (Omron B3U-1000P)
sw = place('SW1', SWF, KNOP_MM[0], KNOP_MM[1], 0, {'1': 'BTN', '2': 'GND'}, 'B3U-1000P', 'C231329')
def gnd_via_bij(p, afstanden=(1.0, 1.3, 1.6, 2.0, 2.5)):
    """GND-via vlak bij een GND-aansluiting, met korte spoor"""
    for dist in afstanden:
        for k_ in range(48):
            ang = k_ * math.pi / 24
            e = (p[0] + math.cos(ang) * dist, p[1] + math.sin(ang) * dist)
            if B.vrij(Point(e).buffer(0.3, 16), 'GND', ['F', 'B']) and B.vrij(LineString([p, e]).buffer(0.125, 8), 'GND', ['F']):
                track([p, e], 'GND', w=0.25); via(e[0], e[1], 'GND'); return e
    print('GEEN GND-via bij', p); return None

# ---- koperpads op de achterkant: [VCC][UPDI via 4,7k][GND] + directe UPDI (HV) + grote batterijpads
def bpad(x, y, w, h, netn, label):
    net(netn); backpads.append((x, y, w, h, netn, label))
    B.add(box(x - w / 2, y - h / 2, x + w / 2, y + h / 2), netn, 'B', 'pad')
def bvia(px, py, vx, vy, netn):
    via(vx, vy, netn); track([(px, py), (vx, vy)], netn, 'B', 0.3)
KX, KY = 68.04, 62.0
bpad(KX - 2.54, KY, 1.9, 1.7, 'VCC', 'VCC')
bpad(KX, KY, 1.9, 1.7, 'UPDI_R', 'UPDI')
bpad(KX + 2.54, KY, 1.9, 1.7, 'GND', 'GND')
bpad(KX, KY + 2.6, 1.9, 1.7, 'UPDI0', 'HV')
bvia(KX, KY, KX, KY - 2.2, 'UPDI_R')
bvia(KX + 2.54, KY, KX + 2.54, KY - 2.2, 'GND')
bvia(KX, KY + 2.6, KX, KY + 4.9, 'UPDI0')
# grote batterijpads (draden aansoldeerbaar)
bpad(15.2, 37.2, 4.6, 3.8, 'VCC', 'BT+')
bpad(15.2, 42.6, 4.6, 3.8, 'GND', 'BT-')
bvia(15.2, 42.6, 18.9, 42.6, 'GND')
gnd_via_bij((CX - 3.1, CY + 1.6)); gnd_via_bij(c1['1']); gnd_via_bij(sw['2'])
# bovenkant: knop, UPDI-routes
route_free(qp(8), (sw['1'][0], sw['1'][1]), 'BTN', wp=[(CX, CY - 4.2)])
track([qp(19), (CX - 0.4, CY + 2.4)], 'UPDI0', w=0.2)
route_free((CX - 0.4, CY + 2.4), (KX, KY + 4.9), 'UPDI0')
route_free(r2['2'], (KX, KY - 2.2), 'UPDI_R')

# ------------------------------------------------------------------ LED-keten
led = keten()
P = []
for naam, p, wp in led:
    q = Point(p[0] * S, p[1] * S)
    if not inner_led.contains(q): q = nearest_points(inner_led.boundary, q)[0]
    P.append((q.x, q.y, naam, [(w[0] * S, w[1] * S) for w in wp]))
# SK6805-EC15 (datasheet): 1 DIN (links onder), 2 VDD (rechts onder), 3 DOUT (rechts boven), 4 GND (links boven)
LP = {'DI': (-0.45, -0.45), 'VDD': (0.45, -0.45), 'DO': (0.45, 0.45), 'GND': (-0.45, 0.45)}
LNR = {'DI': '1', 'VDD': '2', 'DO': '3', 'GND': '4'}

def led_pads(i, th): return {k: (P[i][0] + rot(v, th)[0], P[i][1] + rot(v, th)[1]) for k, v in LP.items()}
def led_geoms(i, th):
    pp = led_pads(i, th)
    return {k: affinity.translate(affinity.rotate(box(-.25, -.25, .25, .25), math.degrees(th), origin=(0, 0)), *pp[k]) for k in pp}

fails, rots, PP = [], [], []
prevDO = None
for i in range(len(P)):
    x, y = P[i][0], P[i][1]
    nxt = (P[i + 1][3][0] if P[i + 1][3] else (P[i + 1][0], P[i + 1][1])) if i + 1 < len(P) else None
    prv = (P[i][3][-1] if P[i][3] else (P[i - 1][0], P[i - 1][1])) if i > 0 else (x - 1, y)
    if nxt is None: nxt = (x + (x - prv[0]), y + (y - prv[1]))
    ideal = math.atan2(nxt[1] - y, nxt[0] - x) - math.pi / 4      # datastroom loopt diagonaal DIN -> DOUT
    cands = sorted([k * math.pi / 2 for k in range(4)], key=lambda t: abs((t - ideal + math.pi) % (2 * math.pi) - math.pi))   # alleen rechte standen
    gekozen = None; why = {}
    for th in cands:
        g = led_geoms(i, th); pp = led_pads(i, th)
        netsd = {'DO': f'D{i + 1}' if i + 1 < len(P) else '', 'GND': 'GND', 'DI': f'D{i}' if i > 0 else 'DATA1', 'VDD': 'VCC'}
        if not all(B.vrij(g[k], netsd[k], ['F']) for k in g): why['pads'] = why.get('pads', 0) + 1; continue
        keep = g['VDD'].buffer(0.3)
        seg_out = Point(0, 0).buffer(0)
        if i + 1 < len(P):
            tgt = P[i + 1][3][0] if P[i + 1][3] else (P[i + 1][0], P[i + 1][1])
            d_ = (tgt[0] - pp['DO'][0], tgt[1] - pp['DO'][1]); L_ = math.hypot(*d_) or 1
            seg = LineString([pp['DO'], (pp['DO'][0] + d_[0] / L_ * min(L_, 1.3), pp['DO'][1] + d_[1] / L_ * min(L_, 1.3))]).buffer(TW / 2 + CLR)
            seg_out = LineString([pp['DO'], (pp['DO'][0] + d_[0] / L_ * min(L_, 6), pp['DO'][1] + d_[1] / L_ * min(L_, 6))]).buffer(TW / 2 + CLR + 0.1)
            pass
        okroute = None
        a = prevDO if prevDO is not None else DATA_START
        wps = P[i][3]
        for r in routes(a, pp['DI'], wps):
            ln = LineString(r).buffer(TW / 2, 8)
            if B.vrij(ln, netsd['DI'], ['F']) and all(ln.distance(g[k_]) >= CLR for k_ in ('VDD', 'GND', 'DO')): okroute = r; break
        if okroute is None:
            why['route'] = why.get('route', 0) + 1
            if os.environ.get('DBGLED') == str(i):
                for rr in routes(a, pp['DI'], wps):
                    l2 = LineString(rr).buffer(TW / 2, 8)
                    print('   cand', round(math.degrees(th)), len(rr), 'binnen', outline.buffer(-EDGE).contains(l2), 'conf', [(n, k) for gg, n, l, k in B.items if l == 'F' and k != 'keep' and n != netsd['DI'] and gg.distance(l2) < CLR][:2], 'vdd', l2.intersects(g['VDD'].buffer(0.12)))
            r0 = [a] + wps + [pp['DI']]; ln0 = LineString(r0).buffer(TW / 2, 8)
            why.setdefault('dbg', []).append((round(math.degrees(th)), outline.buffer(-EDGE).contains(ln0), [(n, k, round(gg.distance(ln0), 2)) for gg, n, l, k in B.items if l == 'F' and n != netsd['DI'] and gg.distance(ln0) < CLR][:3], ln0.intersects(keep)))
            continue
        # GND-stub moet kunnen: korte aftakking van het GND-pad naar open koper
        rl = LineString(okroute).buffer(TW / 2 + CLR)
        stub = None
        for dist in (1.0, 1.4, 1.9):
            for k_ in range(24):
                ang = k_ * math.pi / 12
                e = (pp['GND'][0] + math.cos(ang) * dist, pp['GND'][1] + math.sin(ang) * dist)
                trs = LineString([pp['GND'], e]).buffer(0.125, 8)
                if B.vrij(trs, 'GND', ['F']) and not trs.intersects(rl) and not trs.intersects(seg_out) and not trs.intersects(g['VDD'].buffer(0.75)) and all(trs.distance(g[k_]) >= CLR for k_ in ('DI', 'DO', 'VDD')) and B.vrij(Point(e).buffer(0.3, 16), 'GND', ['F', 'B']) and Point(e).buffer(0.3).distance(rl) > 0.05:
                    stub = [pp['GND'], e]; break
            if stub: break
        if stub is None: why['stub'] = why.get('stub', 0) + 1; continue
        gekozen = (th, pp, okroute, netsd, stub); break
    if gekozen is None:
        fails.append(i); print('fail', i, P[i][2], why)
        th = cands[0]; pp = led_pads(i, th)
        netsd = {'DO': f'D{i + 1}', 'GND': 'GND', 'DI': f'D{i}' if i else 'DATA1', 'VDD': 'VCC'}
        gekozen = (th, pp, next(routes(prevDO if prevDO is not None else DATA_START, pp['DI'], P[i][3])), netsd, None)
    th, pp, r, netsd, stub = gekozen
    rots.append(th)
    for k, gk in led_geoms(i, th).items(): B.add(gk, netsd[k], 'F', 'pad')
    net(netsd['DI']); net(netsd['DO'])
    track(r, netsd['DI'])
    if stub: track(stub, 'GND', w=0.25); via(stub[1][0], stub[1][1], 'GND')
    PP.append((i, th, pp, r))
    B.add(led_geoms(i, th)['VDD'].buffer(0.3), 'VCC', 'F', 'keep')
    prevDO = pp['DO']
    fps.append(dict(ref=f'D{i + 1}', lib=LEDF, x=x, y=y, th=th, val='SK6805-EC15', lcsc='C2890035',
                    netmap={'1': netsd['DI'], '2': 'VCC', '3': netsd['DO'], '4': 'GND'}))

sfail = []
vfail = []
for i, th, pp, r in PP:
    vv = None
    for dist in (1.1, 1.3, 1.5, 1.8, 2.2, 2.6, 3.0, 3.6, 4.2, 5.0, 6.0, 7.0):
        for k in range(72):
            ang = k * math.pi / 36
            vx, vy = pp['VDD'][0] + math.cos(ang) * dist, pp['VDD'][1] + math.sin(ang) * dist
            vg = Point(vx, vy).buffer(0.3, 16); tr = LineString([pp['VDD'], (vx, vy)]).buffer(0.15, 8)
            if B.vrij(vg, 'VCC', ['F', 'B']) and B.vrij(tr, 'VCC', ['F']): vv = (vx, vy); break
        if vv: break
    if vv is None: vfail.append(i); vv = (pp['VDD'][0] + 1.2, pp['VDD'][1] + 1.2)
    track([pp['VDD'], vv], 'VCC', w=0.3); via(vv[0], vv[1], 'VCC')
print('LED-fouten', fails, 'via-fouten', vfail, 'GND-stub-fouten', sfail, 'aantal LED', len(P))

# ------------------------------------------------------------------ koperlagen
def cu(laag): return [(g, n, k) for g, n, l, k in B.items if l == laag and k != 'keep']
def zones(laag, netn):
    items = cu(laag)
    fremd = unary_union([g.buffer(CLR) for g, n, k in items if n != netn])
    pour = outline.buffer(-0.3).difference(fremd).buffer(-0.1).buffer(0.1)
    comps = list(pour.geoms) if hasattr(pour, 'geoms') else [pour]
    own = [g for g, n, k in items if n == netn]
    keep = [c for c in comps if any(c.buffer(0.02).intersects(o) for o in own)]
    losse = [c for c in comps if c not in keep and c.area > 0.15]   # randvulling / eilanden: puur optisch, zwevend
    alles = unary_union(own + keep).buffer(0.02)
    delen = list(alles.geoms) if hasattr(alles, 'geoms') else [alles]
    # elk deel van dit net moet in één samenhangend geheel zitten
    own_unreached = [] if len(delen) == 1 else [d for d in sorted(delen, key=lambda d: -d.area)[1:]]
    return unary_union(keep + losse), len(delen), own_unreached
pourF, nF, lostF = zones('F', 'GND')
pourB, nB, lostB = zones('B', 'VCC')
print('GND samenhangende delen:', nF, '| VCC samenhangende delen:', nB)

def laag_geom(laag, pour):
    return unary_union([g for g, n, k in cu(laag)] + [pour])
copF, copB = laag_geom('F', pourF), laag_geom('B', pourB)

# ------------------------------------------------------------------ soldeermasker / pasta
def padgeoms(laag):
    return [g for g, n, l, k in B.items if l == laag and k == 'pad']
maskF = unary_union([g.buffer(0.05) for g in padgeoms('F')])
maskB = unary_union([g.buffer(0.05) for g in padgeoms('B')])
pasteF = unary_union([g for g in padgeoms('F')])

# ------------------------------------------------------------------ silkscreen (bibliotheek + kunst)
def fp_silk(f):
    """silkscreen-geometrie van een bibliotheek-footprint op F.SilkS"""
    geoms = []
    for el in lib(f['lib']):
        if not isinstance(el, list) or not el or el[0] not in ('fp_line', 'fp_rect', 'fp_circle', 'fp_poly'): continue
        ly = kid(el, 'layer')
        if not ly or ly[1] != 'F.SilkS': continue
        st = kid(el, 'stroke'); w = num(kid(st, 'width')[1]) if st else 0.12
        w = max(w, 0.12)
        def P_(n): return (num(n[1]), -num(n[2]))
        if el[0] == 'fp_line': g = LineString([P_(kid(el, 'start')), P_(kid(el, 'end'))]).buffer(w / 2)
        elif el[0] == 'fp_rect':
            a, b = P_(kid(el, 'start')), P_(kid(el, 'end')); g = box(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])).exterior.buffer(w / 2)
        elif el[0] == 'fp_circle':
            c = P_(kid(el, 'center')); e = P_(kid(el, 'end')); g = Point(c).buffer(math.hypot(e[0] - c[0], e[1] - c[1])).exterior.buffer(w / 2)
        else:
            pts = [P_(q) for q in kid(el, 'pts') if isinstance(q, list) and q[0] == 'xy']; g = Polygon(pts).buffer(w / 2)
        geoms.append(g)
    if not geoms: return None
    g = unary_union(geoms)
    g = affinity.rotate(g, math.degrees(f['th']), origin=(0, 0))
    return affinity.translate(g, f['x'], f['y'])

silkF_lib = unary_union([g for g in (fp_silk(f) for f in fps) if g is not None])
itemsF = unary_union([gg for gg, n, kk in cu('F')])
kunst = maak_kunst(outline, P, itemsF, copB, backpads, vias, fps, dict(oog=OOG_MM, knop=KNOP_MM, neus=NEUS_MM))
copper_all = unary_union([copF.buffer(0.0)])
verbod = unary_union([maskF.buffer(0.15), unary_union([g.buffer(0.2) for g, n, l, k in B.items if l == 'F' and k in ('pad', 'via')])])
silkF = unary_union([silkF_lib.difference(maskF.buffer(0.12)), kunst['F'].difference(verbod)])
silkB = kunst['B'].difference(unary_union([maskB.buffer(0.2), unary_union([Point(v[0], v[1]).buffer(0.5) for v in vias])]))

# ------------------------------------------------------------------ Gerber-schrijver
def fmt(v): return f'{int(round(v * 1e6)):d}'
def polys(g):
    if g.is_empty: return []
    return [g] if g.geom_type == 'Polygon' else [p for p in g.geoms if p.geom_type == 'Polygon']
def ring(coords, pol):
    pts = list(coords)
    s = [f'X{fmt(pts[0][0])}Y{fmt(pts[0][1])}D02*', 'G36*']
    for p in pts[1:]: s.append(f'X{fmt(p[0])}Y{fmt(p[1])}D01*')
    s.append('G37*'); return s
def gerber(path, geom, title, outline_only=False):
    L = ['G04 ' + title + '*', '%FSLAX46Y46*%', '%MOMM*%', '%TF.GenerationSoftware,kerstkaart2026-gen2*%', 'G01*']
    if outline_only:
        L += ['%ADD10C,0.100*%', 'D10*']
        for p in polys(geom):
            pts = list(p.exterior.coords)
            L.append(f'X{fmt(pts[0][0])}Y{fmt(pts[0][1])}D02*')
            for q in pts[1:]: L.append(f'X{fmt(q[0])}Y{fmt(q[1])}D01*')
    else:
        for p in polys(geom):
            p = p.simplify(0.003)
            L.append('%LPD*%'); L += ring(p.exterior.coords, p)
            for h in p.interiors: L.append('%LPC*%'); L += ring(h.coords, p)
        L.append('%LPD*%')
    L.append('M02*')
    open(path, 'w').write('\n'.join(L) + '\n')

gerber(f'{OUT}/Gerber_TopLayer.GTL', copF, 'Top copper')
gerber(f'{OUT}/Gerber_BottomLayer.GBL', copB, 'Bottom copper')
gerber(f'{OUT}/Gerber_TopSolderMaskLayer.GTS', maskF, 'Top mask openings')
gerber(f'{OUT}/Gerber_BottomSolderMaskLayer.GBS', maskB, 'Bottom mask openings')
gerber(f'{OUT}/Gerber_TopPasteMaskLayer.GTP', pasteF, 'Top paste')
gerber(f'{OUT}/Gerber_TopSilkscreenLayer.GTO', silkF, 'Top silk')
gerber(f'{OUT}/Gerber_BottomSilkscreenLayer.GBO', silkB, 'Bottom silk')
gerber(f'{OUT}/Gerber_BoardOutlineLayer.GKO', outline, 'Outline', outline_only=True)
dr = ['M48', '; Excellon, plated vias', 'METRIC,TZ', 'T01C0.300', '%', 'G90', 'T01']
for v in vias: dr.append(f'X{v[0]:.4f}Y{v[1]:.4f}')
dr.append('M30')
open(f'{OUT}/Drill_PTH_Through.DRL', 'w').write('\n'.join(dr) + '\n')
with zipfile.ZipFile('kerstkaart_2026_gerber.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)):
        if fn.startswith(('Gerber', 'Drill')): z.write(f'{OUT}/{fn}', fn)

# ------------------------------------------------------------------ BOM + CPL (JLCPCB)
grp = OrderedDict()
for f in fps:
    key = (f['val'], f['lib'], f['lcsc']); grp.setdefault(key, []).append(f['ref'])
with open(f'{OUT}/BOM_kerstkaart_2026.csv', 'w') as fh:
    fh.write('Comment,Designator,Footprint,LCSC Part #\n')
    for (val, libn, lc), refs in grp.items(): fh.write(f'"{val}","{",".join(refs)}",{libn},{lc}\n')
with open(f'{OUT}/CPL_kerstkaart_2026.csv', 'w') as fh:
    fh.write('Designator,Mid X,Mid Y,Layer,Rotation\n')
    for f in fps:
        fh.write(f'{f["ref"]},{f["x"]:.3f}mm,{f["y"]:.3f}mm,Top,{(math.degrees(f["th"])) % 360:.0f}\n')

# ------------------------------------------------------------------ KiCad (best effort)
def kicad_footprint(f):
    import copy
    node = copy.deepcopy(lib(f['lib']))[2:]   # diepe kopie zonder 'footprint' + naam
    out = []
    ref, val = f['ref'], f['val']
    OX, OY = 20, 140
    kx, ky = f['x'] + OX, OY - f['y']
    ang = math.degrees(f['th'])
    for el in node:
        if isinstance(el, list) and el and el[0] in ('version', 'generator', 'generator_version', 'model', 'layer', 'attr'):
            if el[0] in ('layer', 'attr'): out.append(el)
            continue
        if isinstance(el, list) and el and el[0] == 'property':
            if el[1] == 'Reference': el[2] = Q(ref)
            if el[1] == 'Value': el[2] = Q(val)
            if el[1] in ('Reference', 'Value'): el.append(['hide', 'yes'])
        if isinstance(el, list) and el and el[0] == 'fp_text': continue
        if isinstance(el, list) and el and el[0] == 'pad':
            nr = el[1]
            n = f['netmap'].get(nr, '')
            if el[3] == 'custom' and f['lib'] == QFN:   # pen 1 etc: gewone pen
                at = kid(el, 'at'); lx, ly = num(at[1]), num(at[2])
                w, h = (0.8, 0.2) if abs(abs(lx) - 1.45) < .01 else (0.2, 0.8)
                el[:] = ['pad', nr, 'smd', 'roundrect', ['at', at[1], at[2]], ['size', str(w), str(h)],
                         ['layers', 'F.Cu', 'F.Mask', 'F.Paste'], ['roundrect_rratio', '0.25']]
            if n:
                el.append(['net', str(nets[n]), Q(n)])
            at = kid(el, 'at')
            if at is not None and ang:
                a0 = num(at[3]) if len(at) > 3 else 0.0
                at[:] = ['at', at[1], at[2], f'{a0 + ang:g}']
        out.append(el)
    name = f['lib']
    return ['footprint', Q(f'kerstkaart:{name}')] + [e for e in out] + [['at', f'{kx:.4f}', f'{ky:.4f}', f'{ang:g}']]

def kicad_pcb():
    OX, OY = 20, 140
    kx = lambda x: round(x + OX, 4); ky = lambda y: round(OY - y, 4)
    L = ['(kicad_pcb (version 20260206) (generator "kerstkaart2026") (generator_version "gen2")', '  (general (thickness 1.6) (legacy_teardrops no))', '  (paper "A4")',
         '  (layers (0 "F.Cu" signal) (2 "B.Cu" signal) (9 "F.Adhes" user "F.Adhesive") (11 "B.Adhes" user "B.Adhesive") (13 "F.Paste" user) (15 "B.Paste" user) (5 "F.SilkS" user "F.Silkscreen") (7 "B.SilkS" user "B.Silkscreen") (1 "F.Mask" user) (3 "B.Mask" user) (25 "Edge.Cuts" user) (31 "F.CrtYd" user "F.Courtyard") (29 "B.CrtYd" user "B.Courtyard") (35 "F.Fab" user) (33 "B.Fab" user))',
         '  (setup (pad_to_mask_clearance 0.05))', '  (net 0 "")']
    for n, i in nets.items(): L.append(f'  (net {i} "{n}")')
    for f in fps: L.append('  ' + dump(kicad_footprint(f)))
    for (a, b, w, laag, n) in tracks:
        L.append(f'  (segment (start {kx(a[0])} {ky(a[1])}) (end {kx(b[0])} {ky(b[1])}) (width {w}) (layer "{laag}.Cu") (net {nets[n]}))')
    for vx, vy, n in vias: L.append(f'  (via (at {kx(vx)} {ky(vy)}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net {nets[n]}))')
    pts = list(outline.exterior.coords)
    for a, b in zip(pts, pts[1:]): L.append(f'  (gr_line (start {kx(a[0])} {ky(a[1])}) (end {kx(b[0])} {ky(b[1])}) (layer "Edge.Cuts") (stroke (width 0.1) (type solid)))')
    for x, y, w, h, n, lab in backpads:
        L.append(f'  (footprint "kerstkaart:Pad_{lab}" (layer "B.Cu") (at {kx(x)} {ky(y)}) (property "Reference" "TP_{lab}" (at 0 0) (layer "B.SilkS") (hide yes) (effects (font (size 1 1) (thickness 0.15)))) (pad "1" smd rect (at 0 0) (size {w} {h}) (layers "B.Cu" "B.Mask") (net {nets[n]} "{n}")))')
    zp = ' '.join(f'(xy {kx(x)} {ky(y)})' for x, y in outline.buffer(-0.3).simplify(0.05).exterior.coords)
    for n, laag in (('GND', 'F.Cu'), ('VCC', 'B.Cu')):
        L.append(f'  (zone (net {nets[n]}) (net_name "{n}") (layer "{laag}") (hatch edge 0.5) (connect_pads (clearance 0.2)) (min_thickness 0.2) (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.4)) (polygon (pts {zp})))')
    for lay, g in (('F.SilkS', silkF), ('B.SilkS', silkB)):
        for p in polys(g):
            p = p.simplify(0.02)
            ptsx = ' '.join(f'(xy {kx(x)} {ky(y)})' for x, y in p.exterior.coords)
            L.append(f'  (gr_poly (pts {ptsx}) (stroke (width 0) (type solid)) (fill yes) (layer "{lay}"))')
    L.append(')')
    open('kerstkaart2026.kicad_pcb', 'w').write('\n'.join(L))
kicad_pcb()

# ------------------------------------------------------------------ leds.json voor de firmware
json.dump({'P': [(p[0], p[1], p[2]) for p in P]}, open('leds.json', 'w'))

# ------------------------------------------------------------------ render (zwart masker, goud, wit)
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path
def patch(ax, geom, **kw):
    for p in polys(geom):
        vs, cs = [], []
        for r in [p.exterior] + list(p.interiors):
            c = list(r.coords); vs += c; cs += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(vs, cs), **kw))
def render(naam, kant):
    fig, ax = plt.subplots(figsize=(10, 10), dpi=130); fig.patch.set_facecolor('#111'); ax.set_facecolor('#111')
    flip = (lambda g: affinity.scale(g, -1, 1, origin=(47.5, 0))) if kant == 'B' else (lambda g: g)
    patch(ax, flip(outline), fc='#14171a', ec='none', zorder=1)
    cop = copF if kant == 'F' else copB; msk = maskF if kant == 'F' else maskB; sil = silkF if kant == 'F' else silkB
    patch(ax, flip(cop.difference(msk)), fc='#2b2f33', ec='none', zorder=2)      # onder masker: donker koper-schijn
    patch(ax, flip(cop.intersection(msk)), fc='#d9b44a', ec='none', zorder=3)    # blank koper = ENIG-goud
    patch(ax, flip(sil), fc='#f4f4f4', ec='none', zorder=4)
    patch(ax, flip(outline), fc='none', ec='#555', lw=.6, zorder=5)
    ax.set_aspect('equal'); ax.axis('off'); ax.autoscale_view()
    fig.savefig(naam, bbox_inches='tight', facecolor=fig.get_facecolor()); plt.close(fig)
render('render_voor.png', 'F'); render('render_achter.png', 'B')
print('klaar')

# ------------------------------------------------------------------ firmware-tabel
from itertools import groupby
hdr = ['// Automatisch gegenereerd door gen2.py - niet handmatig aanpassen', '#pragma once', '#include <avr/pgmspace.h>', '',
       f'#define N_LED {len(P)}', '', '// positie in 0,5 mm, oorsprong linksonder van de kaart',
       'const uint8_t LED_X[N_LED] PROGMEM = {' + ', '.join(str(round((p[0] + 1.3) * 2)) for p in P) + '};',
       'const uint8_t LED_Y[N_LED] PROGMEM = {' + ', '.join(str(round((p[1] + .4) * 2)) for p in P) + '};', '']
idx, grpn = 0, {}
for nm, gg in groupby(P, key=lambda p: p[2]):
    l = len(list(gg)); grpn.setdefault(nm, []).append((idx, idx + l - 1)); idx += l
hdr += [f'#define GEWEI_B_VAN {grpn["gewei_b"][0][0]}', f'#define GEWEI_B_TOT {grpn["gewei_b"][0][1]}',
        f'#define GEWEI_A_VAN {grpn["gewei_a"][0][0]}', f'#define GEWEI_A_TOT {grpn["gewei_a"][0][1]}',
        f'#define NEUS {grpn["neus"][0][0]}', f'#define KOP {grpn["kop"][0][0]}', f'#define KIN {grpn["kin"][0][0]}',
        '',
        '// Beide geweien hebben evenveel LED\'s; A loopt in de keten omgekeerd t.o.v. B.',
        '// gewei_rang(i) geeft de spiegel-positie binnen het gewei (0..GEWEI_N-1) zodat beide geweien identiek reageren.',
        '#define GEWEI_N (GEWEI_B_TOT - GEWEI_B_VAN + 1)',
        'static inline uint8_t gewei_rang(uint8_t i) { return i <= GEWEI_B_TOT ? (uint8_t)(i - GEWEI_B_VAN) : (uint8_t)(GEWEI_N - 1 - (i - GEWEI_A_VAN)); }']
os.makedirs('firmware/kerstkaart2026', exist_ok=True)
open('firmware/kerstkaart2026/leds.h', 'w').write('\n'.join(hdr) + '\n')
