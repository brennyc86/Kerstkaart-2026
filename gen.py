"""Genereert KiCad-PCB, render en firmware-tabel voor Kerstkaart 2026 (rendier)."""
import math, json, sys
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union, nearest_points
from shapely import affinity
from shape import silhouet
from ketting import keten, S

CLR = 0.2      # koper-koper vrij
EDGE = 0.4     # koper-rand
TW = 0.25      # datasporen
OX, OY = 20, 140   # plaatsing op KiCad-pagina; y wordt gespiegeld

outline = affinity.scale(silhouet(), S, S, origin=(0, 0)).simplify(0.05)
inner_led = outline.buffer(-2.0)

class Board:
    def __init__(s):
        s.items = []     # (geom, net, laag, soort)
        s.fouten = []
    def vrij(s, geom, net, lagen):
        if not outline.buffer(-EDGE).contains(geom):
            return False
        for g, n, l, k in s.items:
            if n == net and net: continue
            if l in lagen and g.distance(geom) < CLR:
                return False
        return True
    def add(s, geom, net, laag, kind):
        s.items.append((geom, net, laag, kind))

B = Board()
nets = {}
def net(naam):
    if naam not in nets: nets[naam] = len(nets) + 1
    return naam
net('GND'); net('VCC')

pads_out = []    # (ref, nr, x, y, w, h, net, soort, drill)
tracks = []      # (x1,y1,x2,y2,w,laag,net)
vias = []        # (x,y,net)
refs = []        # (ref, waarde, x, y, label)

def pad(ref, nr, x, y, w, h, netn, kind='smd', drill=0, shape='roundrect'):
    n = net(netn) and netn
    pads_out.append((ref, nr, x, y, w, h, netn, kind, drill, shape))
    g = box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
    if kind == 'smd':
        B.add(g, netn, 'F', 'pad')
    else:
        g = Point(x, y).buffer(max(w, h) / 2, 16)
        B.add(g, netn, 'F', 'pad'); B.add(g, netn, 'B', 'pad')
    return g

def track(pts, netn, laag='F', w=TW):
    ln = LineString(pts)
    tracks.extend((pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], w, laag, netn) for i in range(len(pts) - 1))
    B.add(ln.buffer(w / 2, 8), netn, laag, 'track')

def via(x, y, netn):
    vias.append((x, y, netn))
    g = Point(x, y).buffer(0.3, 16)
    B.add(g, netn, 'F', 'via'); B.add(g, netn, 'B', 'via')

def probeer_pad_vrij(g, netn, lagen): return B.vrij(g, netn, lagen)

# ---------------- onderdelen (alle coordinaten in echte mm, y omhoog) ----------------
CX, CY = 35.0, 37.8
# U1 ATtiny1616 SOIC-20 (breed), 90 graden gedraaid: pin1 rechtsboven, pin20 rechtsonder
def u1(n):
    if n <= 10: return (CX + 5.715 - (n - 1) * 1.27, CY + 4.7)
    return (CX - 5.715 + (n - 11) * 1.27, CY - 4.7)
PINNET = {1: 'VCC', 20: 'GND', 5: 'BTN', 11: 'BUZ', 12: 'DATA0', 16: 'UPDI0'}
for n in range(1, 21):
    x, y = u1(n)
    pad('U1', n, x, y, 0.6, 1.9, PINNET.get(n, ''))
refs.append(('U1', 'ATtiny1616-SU (SOIC-20)', CX, CY, 'U1'))

# C1 100n 0603 verticaal rechts naast VCC-pin; via naar onderlaag VCC
via(43.0, CY + 4.7, 'VCC')
track([u1(1), (43.0, CY + 4.7)], 'VCC')
pad('C1', 1, 43.0, CY + 3.0, 0.9, 1.0, 'VCC'); pad('C1', 2, 43.0, CY + 1.4, 0.9, 1.0, 'GND')
track([(43.0, CY + 4.7), (43.0, CY + 3.0)], 'VCC')
refs.append(('C1', '100nF 0603', 43.0, CY + 2.2, 'C1'))

# R1 330R data: pin12 -> R1 -> LED0
d0 = u1(12)
R1A, R1B = CY - 6.5, CY - 8.4
pad('R1', 1, d0[0], R1A, 0.9, 1.0, 'DATA0'); pad('R1', 2, d0[0], R1B, 0.9, 1.0, 'DATA1')
track([d0, (d0[0], R1A)], 'DATA0')
refs.append(('R1', '330R 0603', d0[0], (R1A + R1B) / 2, 'R1'))
# R2 470R UPDI: pin16 -> R2 -> header
u0 = u1(16)
pad('R2', 1, u0[0], CY - 6.5, 0.9, 1.0, 'UPDI0'); pad('R2', 2, u0[0], CY - 8.4, 0.9, 1.0, 'UPDI')
track([u0, (u0[0], CY - 6.5)], 'UPDI0')
refs.append(('R2', '470R 0603', u0[0], CY - 7.45, 'R2'))
# programmeerheader (UPDI, VCC, GND) THT 2.54
HX, HY = 43.5, 31.8
for i, nn in enumerate(['UPDI', 'VCC', 'GND']):
    pad('J1', i + 1, HX + i * 2.54, HY, 1.7, 1.7, nn, 'tht', 1.0, 'circle')
track([(u0[0], CY - 8.4), (HX, CY - 8.4), (HX, HY)], 'UPDI')
refs.append(('J1', 'UPDI 1x3', HX + 2.54, HY - 2.1, 'J1'))
# knop SW1 rechts van MCU (twee brede pads)
SX, SY = 48.5, CY + 1.0
pad('SW1', 1, SX - 2.3, SY, 1.5, 2.6, 'BTN'); pad('SW1', 2, SX + 2.3, SY, 1.5, 2.6, 'GND')
b5 = u1(5)
track([b5, (b5[0], CY + 6.6), (SX - 2.3, CY + 6.6), (SX - 2.3, SY + 1.0)], 'BTN')
refs.append(('SW1', 'Tact SMD', SX, SY, 'SW1'))
# batterij + schakelaar + buzzer in de heup (THT 2.54)
BX, BY = 16.0, 40.5
pad('J2', 1, BX, BY, 1.9, 1.9, 'VBAT', 'tht', 1.0, 'circle')       # BT+
pad('J2', 2, BX + 2.54, BY, 1.9, 1.9, 'GND', 'tht', 1.0, 'circle')  # BT-
pad('J3', 1, BX + 5.08, BY, 1.9, 1.9, 'VBAT', 'tht', 1.0, 'circle')  # schakelaar A
pad('J3', 2, BX + 7.62, BY, 1.9, 1.9, 'VCC', 'tht', 1.0, 'circle')   # schakelaar B
pad('BZ1', 1, BX, BY - 4.0, 1.9, 1.9, 'BUZ', 'tht', 1.0, 'circle')
pad('BZ1', 2, BX + 2.54, BY - 4.0, 1.9, 1.9, 'GND', 'tht', 1.0, 'circle')
track([(BX + 5.08, BY), (BX + 5.08 - 0.0, BY)], 'VBAT') if False else None
# BT+ naar schakelaar A: korte spoor boven langs
track([(BX, BY), (BX, BY + 2.6), (BX + 5.08, BY + 2.6), (BX + 5.08, BY)], 'VBAT')
# BUZ van pin 11 naar buzzer-pad
b11 = u1(11)
track([b11, (BX, b11[1]), (BX, BY - 4.0)], 'BUZ')
refs.append(('J2', 'BT+ BT-', BX + 1.27, BY - 2.0, 'BT'))
refs.append(('J3', 'SCHAKELAAR', BX + 6.35, BY - 2.0, 'SW'))
refs.append(('BZ1', 'BUZZER', BX + 1.27, BY - 6.0, 'BZ'))

# ---------------- LED's ----------------
led = keten()
P = []
for naam, p, wp in led:
    q = Point(p[0] * S, p[1] * S)
    if not inner_led.contains(q):
        q = nearest_points(inner_led.boundary, q)[0] if inner_led.geom_type == 'Polygon' else q
    P.append((q.x, q.y, naam, [(w[0] * S, w[1] * S) for w in wp]))
LP = {'DO': (-0.915, 0.55), 'GND': (-0.915, -0.55), 'DI': (0.915, -0.55), 'VDD': (0.915, 0.55)}
LNR = {'DO': 1, 'GND': 2, 'DI': 3, 'VDD': 4}

def rot(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)

def led_pads(i, th):
    x, y = P[i][0], P[i][1]
    return {k: (x + rot(v, th)[0], y + rot(v, th)[1]) for k, v in LP.items()}

def led_geoms(i, th, nets_):
    pp = led_pads(i, th)
    return {k: box(pp[k][0] - .35, pp[k][1] - .35, pp[k][0] + .35, pp[k][1] + .35) for k in pp}

def routes(a, b, wp):
    """kandidaat-routes van a naar b"""
    yield [a] + wp + [b]
    for mid in ((b[0], a[1]), (a[0], b[1])):
        yield [a] + wp + [mid, b]
    dx, dy = b[0] - a[0], b[1] - a[1]
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    L = math.hypot(dx, dy) or 1
    for off in (2, -2, 4, -4, 6, -6, 9, -9):
        yield [a] + wp + [(mx - dy / L * off, my + dx / L * off), b]
    # 45 graden-knik
    dx, dy = b[0] - a[0], b[1] - a[1]
    m = min(abs(dx), abs(dy))
    if m > 0.3:
        yield [a] + wp + [(a[0] + math.copysign(m, dx), a[1] + math.copysign(m, dy)), b]
        yield [a] + wp + [(b[0] - math.copysign(m, dx), b[1] - math.copysign(m, dy)), b]

fails = []
rots = []
PP = []
prevDO = None   # (positie, netnaam)
for i in range(len(P)):
    x, y = P[i][0], P[i][1]
    nxt = (P[i + 1][3][0] if P[i + 1][3] else (P[i + 1][0], P[i + 1][1])) if i + 1 < len(P) else None
    prv = (P[i][3][-1] if P[i][3] else (P[i - 1][0], P[i - 1][1])) if i > 0 else (x - 1, y)
    if nxt is None: nxt = (x + (x - prv[0]), y + (y - prv[1]))
    ideal = math.atan2(nxt[1] - y, nxt[0] - x) + math.pi
    cands = sorted([k * math.pi / 8 for k in range(16)], key=lambda t: abs((t - ideal + math.pi) % (2 * math.pi) - math.pi))
    gekozen = None; why = {}
    for th in cands:
        g = led_geoms(i, th, None)
        pp = led_pads(i, th)
        netsd = {'DO': f'D{i + 1}' if i + 1 < len(P) else '', 'GND': 'GND', 'DI': f'D{i}' if i > 0 else 'DATA1', 'VDD': 'VCC'}
        # pads zelf vrij?
        if not all(B.vrij(g[k], netsd[k], ['F']) for k in g): why['pads']=why.get('pads',0)+1; continue
        # uitgaande richting mag eigen pads niet raken
        if i + 1 < len(P):
            tgt = P[i + 1][3][0] if P[i + 1][3] else (P[i + 1][0], P[i + 1][1])
            d_ = (tgt[0] - pp['DO'][0], tgt[1] - pp['DO'][1]); L_ = math.hypot(*d_) or 1
            seg = LineString([pp['DO'], (pp['DO'][0] + d_[0] / L_ * min(L_, 3), pp['DO'][1] + d_[1] / L_ * min(L_, 3))]).buffer(TW / 2 + CLR)
            if any(seg.intersects(g[kk]) for kk in g if kk != 'DO') or seg.intersects(g['VDD'].buffer(0.3)):
                why['uit'] = why.get('uit', 0) + 1; continue
        # route naar DI (eigen VDD-pad houdt ruimte vrij voor via-stub)
        keep = g['VDD'].buffer(0.3)
        okroute = None
        if prevDO is None:
            a = (d0[0], R1B)
            netn = 'DATA1'
            for r in routes(a, pp['DI'], []):
                ln = LineString(r).buffer(TW / 2, 8)
                if B.vrij(ln, netn, ['F']) and not ln.buffer(CLR).intersects(keep): okroute = r; break
        else:
            for r in routes(prevDO, pp['DI'], P[i][3]):
                ln = LineString(r).buffer(TW / 2, 8)
                if B.vrij(ln, f'D{i}', ['F']) and not ln.buffer(CLR).intersects(keep): okroute = r; break
        if okroute is None: why['route']=why.get('route',0)+1; continue
        vv = (0, 0)
        gekozen = (th, pp, okroute, vv, netsd); break
    if gekozen is None:
        fails.append(i); print('fail',i,P[i][2],why)
        th = cands[0]; pp = led_pads(i, th); netsd = {'DO': f'D{i + 1}', 'GND': 'GND', 'DI': f'D{i}' if i else 'DATA1', 'VDD': 'VCC'}
        okroute = next(routes(prevDO if prevDO else (d0[0], R1B), pp['DI'], P[i][3])); vv = (pp['VDD'][0] + .9, pp['VDD'][1] + .9)
        gekozen = (th, pp, okroute, vv, netsd)
    th, pp, r, vv, netsd = gekozen
    rots.append(th)
    for k in LP:
        pad(f'D{i + 1}', LNR[k], pp[k][0], pp[k][1], 0.7, 0.7, netsd[k])
    net(netsd['DI']); net(netsd['DO'])
    track(r, netsd['DI'])
    PP.append((i, th, pp, r))
    B.add(led_geoms(i, th, None)['VDD'].buffer(0.3), 'VCC', 'F', 'keep')
    prevDO = pp['DO']
    refs.append((f'D{i + 1}', 'WS2812B-2020', x, y, None))

# tweede ronde: VDD-via's
vfail = []
for i, th, pp, r in PP:
    vv = None
    for dist in (1.5, 1.8, 2.2, 2.6, 3.0, 3.6, 4.2, 5.0):
        for k in range(24):
            ang = k * math.pi / 12
            vx = pp['VDD'][0] + math.cos(ang) * dist
            vy = pp['VDD'][1] + math.sin(ang) * dist
            vg = Point(vx, vy).buffer(0.3, 16)
            tr = LineString([pp['VDD'], (vx, vy)]).buffer(0.15, 8)
            if B.vrij(vg, 'VCC', ['F']) and B.vrij(tr, 'VCC', ['F']):
                vv = (vx, vy); break
        if vv: break
    if vv is None:
        vfail.append(i); vv = (pp['VDD'][0] + 1.2, pp['VDD'][1] + 1.2)
    track([pp['VDD'], vv], 'VCC', w=0.3)
    via(vv[0], vv[1], 'VCC')
print('via-fouten', vfail)

# ---------------- pour-controle ----------------
cu = [(g, n) for g, n, l, k in B.items if l == 'F' and n != 'GND']
pour = outline.buffer(-EDGE).difference(unary_union([g.buffer(CLR) for g, n in cu]))
comps = list(pour.geoms) if pour.geom_type == 'MultiPolygon' else [pour]
comps.sort(key=lambda c: -c.area)
main = comps[0]
gnd_pads = [(g, k) for g, n, l, k in B.items if l == 'F' and n == 'GND' and k == 'pad']
verweesd = 0
for g, k in gnd_pads:
    if not main.buffer(0.01).intersects(g): verweesd += 1
print('LEDs', len(P), 'fouten', fails, 'GND-pads niet op hoofdpour', verweesd, 'pour-eilanden', len(comps))
json.dump({'P': [(p[0], p[1], p[2]) for p in P]}, open('leds.json', 'w'))

# ---------------- render ----------------
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
fig, ax = plt.subplots(figsize=(13, 13), dpi=110)
fig.patch.set_facecolor('#0b1a12')
ax.set_facecolor('#0b1a12')
x, y = outline.exterior.xy
ax.fill(x, y, color='#0d5a2c', zorder=1)
for c in comps:
    if c.area < 1: continue
    xs, ys = c.exterior.xy
    ax.fill(xs, ys, color='#1d8a4a', alpha=.75, zorder=2)
    for h in c.interiors:
        hx, hy = h.xy; ax.fill(hx, hy, color='#0d5a2c', zorder=2)
for t in tracks:
    ax.plot([t[0], t[2]], [t[1], t[3]], color='#e8c15a' if t[5] == 'F' else '#999', lw=max(t[4] * 3.2, 0.6), solid_capstyle='round', zorder=3)
for p in pads_out:
    ref, nr, px, py, w, h, nn, kind, dr, sh = p
    if kind == 'smd':
        ax.add_patch(plt.Rectangle((px - w / 2, py - h / 2), w, h, color='#f2d98a', zorder=4))
    else:
        ax.add_patch(plt.Circle((px, py), w / 2, color='#f2d98a', zorder=4)); ax.add_patch(plt.Circle((px, py), dr / 2, color='#0b1a12', zorder=5))
for vx, vy, nn in vias:
    ax.add_patch(plt.Circle((vx, vy), .3, color='#f2d98a', zorder=4)); ax.add_patch(plt.Circle((vx, vy), .15, color='#0b1a12', zorder=5))
for ref, val, rx, ry, lab in refs:
    if ref.startswith('D'):
        ax.add_patch(plt.Rectangle((rx - 1.1, ry - 1.1), 2.2, 2.2, fill=False, ec='#ffffff', lw=.5, zorder=6))
        ax.text(rx, ry + 1.6, ref[1:], color='#ffd', fontsize=5.5, ha='center', zorder=7)
    elif lab:
        ax.text(rx, ry, lab, color='#fff', fontsize=6, ha='center', zorder=7)
import os
C = [float(v) for v in os.environ.get('CROP', '-2,98,-2,98').split(',')]
ax.set_aspect('equal'); ax.set_xlim(C[0], C[1]); ax.set_ylim(C[2], C[3]); ax.axis('off')
fig.savefig(os.environ.get('OUT', 'pcb_render.png'), bbox_inches='tight')

# ---------------- KiCad-export ----------------
def kx(x): return round(x + OX, 4)
def ky(y): return round(OY - y, 4)
def nid(n): return nets[n] if n else 0
L = []
L.append('(kicad_pcb (version 20221018) (generator "kerstkaart2026")')
L.append('  (general (thickness 1.6))')
L.append('  (paper "A4")')
L.append('''  (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (32 "B.Adhes" user "B.Adhesive") (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user) (49 "F.Fab" user))''')
L.append('  (setup (pad_to_mask_clearance 0.05) (pcbplotparams (layerselection 0x00010fc_ffffffff) (outputdirectory "gerber/")))')
L.append('  (net 0 "")')
for n, i in nets.items():
    L.append(f'  (net {i} "{n}")')
# footprints
from collections import OrderedDict
byref = OrderedDict()
for p in pads_out: byref.setdefault(p[0], []).append(p)
for ref, ps in byref.items():
    cx = sum(p[2] for p in ps) / len(ps); cy = sum(p[3] for p in ps) / len(ps)
    val = next((r[1] for r in refs if r[0] == ref), '')
    L.append(f'  (footprint "kerstkaart:{ref}" (layer "F.Cu") (at {kx(cx)} {ky(cy)})')
    L.append(f'    (fp_text reference "{ref}" (at 0 -2.2) (layer "F.SilkS") hide (effects (font (size 0.8 0.8) (thickness 0.12))))')
    L.append(f'    (fp_text value "{val}" (at 0 2.2) (layer "F.Fab") hide (effects (font (size 0.8 0.8) (thickness 0.12))))')
    for (_, nr, x, y, w, h, nn, kind, dr, sh) in ps:
        nt = f'(net {nid(nn)} "{nn}")' if nn else ''
        at = f'(at {round(x - cx, 4)} {round(-(y - cy), 4)})'
        if kind == 'smd':
            L.append(f'    (pad "{nr}" smd roundrect {at} (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.2) {nt})')
        else:
            L.append(f'    (pad "{nr}" thru_hole circle {at} (size {w} {h}) (drill {dr}) (layers "*.Cu" "*.Mask") {nt})')
    L.append('  )')
for (x1, y1, x2, y2, w, laag, nn) in tracks:
    L.append(f'  (segment (start {kx(x1)} {ky(y1)}) (end {kx(x2)} {ky(y2)}) (width {w}) (layer "{laag}.Cu") (net {nid(nn)}))')
for vx, vy, nn in vias:
    L.append(f'  (via (at {kx(vx)} {ky(vy)}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net {nid(nn)}))')
pts = list(outline.exterior.coords)
for a, b in zip(pts, pts[1:]):
    L.append(f'  (gr_line (start {kx(a[0])} {ky(a[1])}) (end {kx(b[0])} {ky(b[1])}) (layer "Edge.Cuts") (width 0.1))')
zp = ' '.join(f'(xy {kx(x)} {ky(y)})' for x, y in outline.buffer(-0.3).simplify(0.05).exterior.coords)
for netn, laag in (('GND', 'F.Cu'), ('VCC', 'B.Cu')):
    L.append(f'  (zone (net {nid(netn)}) (net_name "{netn}") (layer "{laag}") (hatch edge 0.5)')
    L.append('    (connect_pads (clearance 0.2)) (min_thickness 0.2) (filled_areas_thickness no)')
    L.append('    (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.4))')
    L.append(f'    (polygon (pts {zp})))')
L.append(f'  (gr_text "Kerstkaart 2026" (at {kx(40)} {ky(14)}) (layer "B.SilkS") (effects (font (size 2 2) (thickness 0.3)) (justify mirror)))')
for lab, x, y in (('BT+ BT-', BX + 1.27, BY + 1.8), ('SCH', BX + 6.35, BY + 1.8), ('BZ', BX + 1.27, BY - 5.8), ('UPDI VCC GND', HX + 2.54, HY + 1.6)):
    L.append(f'  (gr_text "{lab}" (at {kx(x)} {ky(y)}) (layer "F.SilkS") (effects (font (size 0.9 0.9) (thickness 0.15))))')
L.append(')')
open('kerstkaart2026.kicad_pcb', 'w').write('\n'.join(L))
print('kicad geschreven', len(L), 'regels')
