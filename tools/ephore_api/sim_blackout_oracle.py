#!/usr/bin/env python3
"""Extrait l'oracle Blackout : flèches groupe 2 vs groupe 4 sur les 14 CSV
de ~/Ephore/Base 10:10/Ajustements/.  Sortie : CSV d'oracle + effectifs."""
import csv, glob, os, re, datetime as dt

SRC = "/Users/jeremk/Ephore/Base 10:10/Ajustements"
OUT = "/Users/jeremk/Ephore/on-va-se-le-tenter/tools/ephore_api/oracle_blackout.csv"
COLS = ["Signal Long Fort", "Signal Short Fort", "Signal Long Moyen", "Signal Short Moyen"]

def groups(header):
    """retourne la liste des groupes [ {nom_col: idx} ] dans l'ordre d'apparition"""
    gs, cur = [], {}
    for i, h in enumerate(header):
        if h in COLS:
            if h in cur:
                gs.append(cur); cur = {}
            cur[h] = i
    if cur: gs.append(cur)
    return gs

def parse_t(s):
    return dt.datetime.fromisoformat(s)

rows = []
for path in sorted(glob.glob(os.path.join(SRC, "*.csv"))):
    base = os.path.basename(path)
    m = re.match(r"CME_MINI_(MES|NQ)Z2026, ([0-9A-Z]+)_", base)
    sym, tf = m.group(1), m.group(2)
    with open(path) as f:
        r = csv.reader(f)
        header = next(r)
        gs = groups(header)
        assert len(gs) == 4, (base, len(gs))
        data = list(r)
    for line in data:
        t = parse_t(line[0])
        for gi, g in enumerate(gs, start=1):
            for cname, idx in g.items():
                v = line[idx].strip()
                if v and v not in ("0", "0.0") and v.lower() != "nan":
                    rows.append(dict(sym=sym, tf=tf, t=t.isoformat(), groupe=gi,
                                     col=cname, val=v))

# effectifs
from collections import Counter
c = Counter(r["groupe"] for r in rows)
print("flèches par groupe de colonnes :", dict(sorted(c.items())))

with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["sym", "tf", "t", "groupe", "col", "val"])
    w.writeheader()
    for r in sorted(rows, key=lambda r: (r["sym"], r["tf"], r["t"], r["groupe"])):
        w.writerow(r)
print("oracle ->", OUT)

# comparaison g2 / g4
key = lambda r: (r["sym"], r["tf"], r["t"], r["col"])
g2 = {key(r) for r in rows if r["groupe"] == 2}
g4 = {key(r) for r in rows if r["groupe"] == 4}
print("g2=%d  g4=%d  g2\\g4=%d  g4\\g2=%d" % (len(g2), len(g4), len(g2 - g4), len(g4 - g2)))
# bornes temporelles
ts = sorted(parse_t(r["t"]) for r in rows)
print("période des flèches :", ts[0].isoformat(), "->", ts[-1].isoformat())
