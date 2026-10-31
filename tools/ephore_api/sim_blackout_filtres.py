#!/usr/bin/env python3
"""Confirmation croisee du Blackout sur un AUTRE corpus : ~/ERGON/Singal
(case filtre DECOCHEE) contre ~/ERGON/Filtres (case COCHEE), meme version
d'Ephore (30/09), memes symboles / unites de temps.

On compare, barre par barre, les fleches de l'ORIGINAL entre les deux exports :
celles qui disparaissent quand la case est cochee donnent directement les
creneaux reellement bloques.
"""
import csv, glob, os, re, datetime as dt, collections

COLS = ("Signal Long Fort", "Signal Short Fort", "Signal Long Moyen", "Signal Short Moyen")

def arrows(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    hdr, data = rows[0], [r for r in rows[1:] if r and r[0]]
    idx = {}
    for i, n in enumerate(hdr):
        idx[n.strip()] = i          # derniere occurrence = fleches de l'original
    if not all(c in idx for c in COLS):
        return None, None
    out, bars = set(), set()
    for r in data:
        bars.add(r[0])
        for c in COLS:
            v = r[idx[c]].strip()
            if v and v not in ("0", "0.0"):
                out.add((r[0], c))
    return out, bars

def scan(d):
    res = {}
    for p in glob.glob(os.path.join(d, "*.csv")):
        m = re.match(r"CME_MINI_(MES|NQ)Z2026, ([0-9A-Z]+)_", os.path.basename(p))
        a, b = arrows(p)
        if a is None:
            continue
        k = (m.group(1), m.group(2))
        if k in res:                 # doublon (MES 3m x2) : on fusionne
            res[k] = (res[k][0] | a, res[k][1] | b)
        else:
            res[k] = (a, b)
    return res

OFF = scan(os.path.expanduser("~/ERGON/Singal"))
ON = scan(os.path.expanduser("~/ERGON/Filtres"))

print("unites communes :", sorted(set(OFF) & set(ON)))
retirees, gardees = [], []
for k in sorted(set(OFF) & set(ON)):
    aoff, boff = OFF[k]
    aon, bon = ON[k]
    common = boff & bon                      # barres presentes dans les deux exports
    for t, c in sorted(aoff):
        if t not in common:
            continue
        (gardees if (t, c) in aon else retirees).append((k, t, c))
    for t, c in sorted(aon):
        if t in common and (t, c) not in aoff:
            print("  !! fleche PRESENTE seulement avec le filtre :", k, t, c)

print("fleches comparables : %d gardees, %d retirees par la case filtre"
      % (len(gardees), len(retirees)))
hm = lambda t: t[11:16] if "T" in t else "DAILY"
print()
print("--- heures des fleches RETIREES par le filtre ---")
for h, n in sorted(collections.Counter(hm(t) for _, t, _ in retirees).items()):
    print("   %s  x%d" % (h, n))
print("--- heures sensibles chez les fleches GARDEES ---")
cg = collections.Counter(hm(t) for _, t, _ in gardees)
for h in ("09:00", "14:30", "15:30", "16:00"):
    print("   %s  x%d gardees" % (h, cg.get(h, 0)))
print()
print("--- detail des retirees ---")
for k, t, c in sorted(retirees, key=lambda x: x[1]):
    d = dt.datetime.fromisoformat(t)
    print("   %-4s %-4s %s %s  %s" % (k[0], k[1], t[:16], d.strftime("%a"), c))
