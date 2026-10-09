"""LED-keten (tekeningcoordinaten, y omhoog). Volgorde = datavolgorde."""
from shapely.geometry import LineString

S = 0.85  # tekening -> echte mm

def bp(beam, s, lat):
    """Punt op polyline (fractie s) met zijwaartse verschuiving lat (links = +)."""
    ln = LineString(beam)
    p = ln.interpolate(s, normalized=True)
    q = ln.interpolate(min(1, s + 0.01), normalized=True) if s < .99 else p
    r = ln.interpolate(max(0, s - 0.01), normalized=True) if s > .01 else p
    dx, dy = q.x - r.x, q.y - r.y
    n = (dx * dx + dy * dy) ** .5
    return (round(p.x - dy / n * lat, 1), round(p.y + dx / n * lat, 1))

BEAM_B = [(90, 82), (96, 96), (104, 106)]
BEAM_A = [(80, 82), (74, 96), (66, 106)]
W = 2.8

def keten():
    g = []  # (groep, (x, y), [waypoints naar deze led])
    def add(naam, p, wp=()): g.append((naam, p, list(wp)))
    # buik start (naast MCU)
    add('buik', (40, 31)); add('buik', (46, 31))
    # voorpoot 2: heen west, terug oost
    add('poot', (51.5, 24), [(50, 30)])
    for p in [(51.5, 8), (56, 8), (56, 24)]: add('poot', p)
    add('poot', (64.5, 24), [(57.5, 31), (63, 31)])
    for p in [(64.5, 8), (69, 8), (69, 24)]: add('poot', p)
    # borst + hals rechts omhoog
    add('hals', (70, 42)); add('hals', (75, 51)); add('hals', (81, 59))
    # kin, neus, snuit, oog
    add('kin', (89, 63)); add('kin', (98, 62))
    add('neus', (106, 66))
    add('snuit', (100, 71)); add('snuit', (94, 73.5))
    add('oog', (91.5, 78))
    # gewei B: omhoog oostzijde met oost-tine, omlaag westzijde met noord-tine
    add('gewei_b', bp(BEAM_B, 0.30, -W)); add('gewei_b', (105.5, 94.5))
    add('gewei_b', bp(BEAM_B, 0.78, -W * .5))
    add('gewei_b', (97.5, 109))
    add('gewei_b', bp(BEAM_B, 0.5, W * .7)); add('gewei_b', bp(BEAM_B, 0.16, W * .5))
    # gewei A: omhoog oostzijde, omlaag westzijde met west-tine
    add('gewei_a', bp(BEAM_A, 0.30, -W), [(86, 76)])
    add('gewei_a', bp(BEAM_A, 0.80, -W * .5))
    add('gewei_a', (64.5, 94.5), [(70, 106)])
    add('gewei_a', bp(BEAM_A, 0.45, W)); add('gewei_a', bp(BEAM_A, 0.12, W))
    # hals links omlaag, rug naar staart
    add('hals', (73, 68)); add('hals', (65, 59)); add('hals', (57, 52.5))
    for x in (48, 38, 28, 19): add('rug', (x, 55.5 if x > 30 else 54))
    add('staart', (6, 53.5))
    add('romp', (12.5, 42))
    # achterpoot 1 (west)
    for p in [(11.2, 24), (11.2, 8), (15.8, 8), (15.8, 24)]: add('poot', p)
    add('romp', (20.5, 35.5), [(16.5, 31)])
    for p in [(25.2, 24), (25.2, 8), (29.8, 8), (29.8, 24)]: add('poot', p)
    add('buik', (33, 31), [(31, 30)])
    return g
