"""LED-keten (tekeneenheden, y omhoog; koppen/neus-positie in mm via mm()). Volgorde = datavolgorde."""
from shapely.geometry import LineString

S = 0.85  # tekening -> echte mm
def mm(x, y): return (x / S, y / S)

def bp(beam, s, lat):
    ln = LineString(beam)
    p = ln.interpolate(s, normalized=True)
    q = ln.interpolate(min(1, s + 0.01), normalized=True) if s < .99 else p
    r = ln.interpolate(max(0, s - 0.01), normalized=True) if s > .01 else p
    dx, dy = q.x - r.x, q.y - r.y
    n = (dx * dx + dy * dy) ** .5
    return (round(p.x - dy / n * lat, 1), round(p.y + dx / n * lat, 1))

AS = 85.0   # spiegelas gewei
BEAM_B = [(90, 82), (96, 96), (104, 106)]
BEAM_A = [(2 * AS - x, y) for x, y in BEAM_B]
E_TIP_B = (105.5, 94.5)
N_TIP_B = (97.5, 109)
W = 2.8

# ---- vaste punten in mm
OOG_MM = (74.0, 64.5)     # ATtiny (QFN) = oog van Rudolf
KNOP_MM = (87.5, 54.5)    # knopje = neus (indrukken om te wisselen)
NEUS_MM = (91.8, 54.5)    # rode neus-LED
JST_MM = (24.0, 39.0)     # tweede batterij-aansluiting (JST-PH) in de heup, plug van links

def keten():
    g = []
    def add(naam, p, wp=()): g.append((naam, p, list(wp)))
    # --- kop: eerste LED vlak bij het oog (data van de chip), dan de neus
    add('kop', mm(79.5, 70.0))
    # --- gewei B (rechts) en A (links): identieke sets, A is de spiegel van B in omgekeerde volgorde
    B6 = [bp(BEAM_B, 0.36, -W), E_TIP_B, bp(BEAM_B, 0.80, -W * .3), bp(BEAM_B, 0.50, W * .7), bp(BEAM_B, 0.16, W * .9)]
    for p in B6: add('gewei_b', p)
    for p in reversed(B6): add('gewei_a', (round(2 * AS - p[0], 1), p[1]))
    # --- hals links omlaag, rug, staart
    add('hals', (73, 68)); add('hals', (65, 59)); add('hals', (57, 52.5))
    for x in (48, 38, 28, 19): add('rug', (x, 55.5 if x > 30 else 54))
    # --- achterpoten
    for p in [(11.2, 24), (11.2, 8), (15.8, 8), (15.8, 24)]: add('poot', p)
    add('romp', (20.5, 35.5), [(16.5, 31)])
    for p in [(25.2, 24), (25.2, 8), (29.8, 8), (29.8, 24)]: add('poot', p)
    # --- buik, dan de voorpoten
    add('buik', (33, 31), [(31, 30)])
    add('buik', (41, 31))
    add('poot', (51.5, 24), [(50, 30)])
    for p in [(51.5, 8), (56, 8), (56, 24)]: add('poot', p)
    add('poot', (64.5, 24), [(57.5, 31), (63, 31)])
    for p in [(64.5, 8), (69, 8), (69, 24)]: add('poot', p)
    # --- borst + hals rechts omhoog, kin
    add('hals', (70, 42)); add('hals', (75, 51)); add('hals', (81, 59))
    add('kin', mm(79.5, 53.0))
    add('neus', mm(*NEUS_MM), [mm(84.0, 52.0), mm(90.2, 52.0)])
    return g
