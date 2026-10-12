#!/usr/bin/env python3
"""Caracterise le reliquat du Blackout : les 6 fleches retirees par le groupe 2
que le creneau 10:00 ET n'explique pas.  On regarde si elles sont en frontiere
sur les ingredients Signator (ADX, dBand, volume, range/ATR, cpos, score CQF)
et sur l'heure, comparees aux 161 fleches conservees.
"""
import csv, glob, os, re, datetime as dt, statistics

SRC = "/Users/jeremk/Ephore/Base 10:10/Ajustements"
HERE = os.path.dirname(os.path.abspath(__file__))

def ema(x, p):
    a = 2 / (p + 1); out = [x[0]]
    for v in x[1:]: out.append(a * v + (1 - a) * out[-1])
    return out

def rma(x, p):
    out = [None] * len(x); s = None; buf = []
    for i, v in enumerate(x):
        if v is None: continue
        if s is None:
            buf.append(v)
            if len(buf) == p: s = sum(buf) / p
        else: s = (s * (p - 1) + v) / p
        out[i] = s
    return out

def metrics(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    hdr, data = rows[0], [r for r in rows[1:] if r and r[0]]
    last = {}
    for i, n in enumerate(hdr): last[n.strip()] = i
    def col(n): return last.get(n)
    T, O, H, L, C, V = [], [], [], [], [], []
    for r in data:
        T.append(r[0])
        O.append(float(r[1])); H.append(float(r[2])); L.append(float(r[3])); C.append(float(r[4]))
        iv = col("Volume")
        try: V.append(float(r[iv]))
        except Exception: V.append(0.0)
    N = len(T)
    o4 = [(O[i] + H[i] + L[i] + C[i]) / 4 for i in range(N)]
    bull = [a > b for a, b in zip(ema(o4, 4), ema(o4, 32))]
    tr = [H[0] - L[0]] + [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])) for i in range(1, N)]
    up = [0] + [max(H[i] - H[i - 1], 0) if H[i] - H[i - 1] > L[i - 1] - L[i] else 0 for i in range(1, N)]
    dn = [0] + [max(L[i - 1] - L[i], 0) if L[i - 1] - L[i] > H[i] - H[i - 1] else 0 for i in range(1, N)]
    atr, pu, pd = rma(tr, 14), rma(up, 14), rma(dn, 14)
    dx = [None if atr[i] is None else (abs(pu[i] - pd[i]) / (pu[i] + pd[i]) * 100 if pu[i] + pd[i] > 0 else 0) for i in range(N)]
    adx = rma(dx, 14)
    e50, e60 = ema(C, 50), ema(C, 60)
    vs = [sum(V[i - 19:i + 1]) / 20 if i >= 19 else None for i in range(N)]
    out = {}
    for i in range(N):
        if atr[i] is None or not atr[i] or vs[i] is None: continue
        rng = H[i] - L[i]
        cpos = (C[i] - L[i]) / rng if rng else 0.0
        if not bull[i]: cpos = 1 - cpos
        db = ((C[i] - max(e50[i], e60[i])) if bull[i] else (min(e50[i], e60[i]) - C[i])) / atr[i]
        out[T[i]] = dict(adx=adx[i] or 0.0, db=db, vr=(V[i] / vs[i] if vs[i] else 0.0),
                         ratr=rng / (0.5 * atr[i]), cpos=cpos)
    return out

# ----- oracle
rows = list(csv.DictReader(open(os.path.join(HERE, "oracle_blackout.csv"))))
key = lambda r: (r["sym"], r["tf"], r["t"], r["col"])
g2 = {key(r) for r in rows if r["groupe"] == "2"}
g4 = [r for r in rows if r["groupe"] == "4"]

files = {}
for p in sorted(glob.glob(os.path.join(SRC, "*.csv"))):
    m = re.match(r"CME_MINI_(MES|NQ)Z2026, ([0-9A-Z]+)_", os.path.basename(p))
    files[(m.group(1), m.group(2))] = p
MET = {k: metrics(p) for k, p in files.items()}

RELIQUAT = {("MES", "2", "2026-10-09T13:20:00+02:00"),
            ("MES", "30", "2026-10-08T02:30:00+02:00"),
            ("MES", "30", "2026-10-08T05:30:00+02:00"),
            ("MES", "60", "2026-09-25T09:00:00+02:00"),
            ("NQ", "15", "2026-09-29T18:00:00+02:00"),
            ("NQ", "1D", "2026-07-13T00:00:00")}

kept, rel = [], []
for r in g4:
    met = MET.get((r["sym"], r["tf"]), {}).get(r["t"])
    if met is None: continue
    tag = (r["sym"], r["tf"], r["t"])
    (rel if tag in RELIQUAT else (kept if key(r) in g2 else [])).append((r, met))

print("fleches mesurables : conservees=%d  reliquat=%d" % (len(kept), len(rel)))
print()
print("--- les 6 du reliquat ---")
for r, m in sorted(rel, key=lambda x: x[0]["t"]):
    print("  %-4s %-4s %s  ADX=%6.2f dBand=%6.2f vol=%5.2f range/ATR=%5.2f cpos=%4.2f"
          % (r["sym"], r["tf"], r["t"][:16], m["adx"], m["db"], m["vr"], m["ratr"] * 0.5, m["cpos"]))
print()
print("--- distribution sur les 161 conservees (min / q1 / med / max) ---")
for f in ("adx", "db", "vr", "ratr", "cpos"):
    v = sorted(x[1][f] for x in kept)
    lab = {"ratr": "range/(0.5ATR)"}.get(f, f)
    print("  %-14s min=%7.2f q1=%7.2f med=%7.2f max=%8.2f" %
          (lab, v[0], v[len(v) // 4], statistics.median(v), v[-1]))
print()
print("--- rang (percentile) du reliquat dans les conservees ---")
for r, m in sorted(rel, key=lambda x: x[0]["t"]):
    s = []
    for f in ("adx", "db", "vr", "ratr", "cpos"):
        v = sorted(x[1][f] for x in kept)
        pct = 100.0 * sum(1 for y in v if y < m[f]) / len(v)
        s.append("%s=%.0f%%" % (f, pct))
    print("  %-4s %-4s %s  %s" % (r["sym"], r["tf"], r["t"][:16], "  ".join(s)))
