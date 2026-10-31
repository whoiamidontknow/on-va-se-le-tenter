#!/usr/bin/env python3
"""Validation croisee de la regle BLACKOUT sur les DEUX corpus :
  corpus A = "Base 10:10/Ajustements"  (groupe 4 -> groupe 2, 176 -> 161)
  corpus B = ~/ERGON/Singal (filtre OFF) -> ~/ERGON/Filtres (filtre ON)
Balaye la marge et le jeu de creneaux, mode = test sur l'heure d'OUVERTURE
de la bougie en heure de Paris.
"""
import csv, glob, os, re, datetime as dt, itertools, collections

HERE = os.path.dirname(os.path.abspath(__file__))
COLS = ("Signal Long Fort", "Signal Short Fort", "Signal Long Moyen", "Signal Short Moyen")
TF_MIN = {"1": 1, "2": 2, "3": 3, "5": 5, "15": 15, "30": 30, "60": 60, "240": 240, "1D": 1440}

# --- creneaux (cf. sim_blackout.py pour les regles DST) ---------------------
def paris_offset(d):
    y = d.year
    mar = max(x for x in range(25, 32) if dt.date(y, 3, x).weekday() == 6)
    oc = max(x for x in range(25, 32) if dt.date(y, 10, x).weekday() == 6)
    return 2 if dt.date(y, 3, mar) <= d < dt.date(y, 10, oc) else 1

def et_offset(d):
    y = d.year
    mar = [x for x in range(8, 15) if dt.date(y, 3, x).weekday() == 6][0]
    nov = [x for x in range(1, 8) if dt.date(y, 11, x).weekday() == 6][0]
    return -4 if dt.date(y, 3, mar) <= d < dt.date(y, 11, nov) else -5

def et2paris(d, h, m):
    return h * 60 + m + (paris_offset(d) - et_offset(d)) * 60

def slots(d, actifs):
    o = []
    if "openEU" in actifs: o.append(9 * 60)
    if "openUS" in actifs: o.append(et2paris(d, 9, 30))
    if "nfp" in actifs and d.weekday() == 4 and (d.day - 1) // 7 == 0: o.append(et2paris(d, 8, 30))
    if "jobless" in actifs and d.weekday() == 3: o.append(et2paris(d, 8, 30))
    if "us830" in actifs: o.append(et2paris(d, 8, 30))
    if "us1000" in actifs: o.append(et2paris(d, 10, 0))
    if "fomc" in actifs and d.weekday() == 2: o.append(et2paris(d, 14, 0))
    if "cust1" in actifs: o.append(et2paris(d, 14, 30))
    if "cust2" in actifs: o.append(et2paris(d, 20, 0))
    return o

def blocked(ts, actifs, marge):
    d = dt.datetime.fromisoformat(ts).replace(tzinfo=None)
    bar0 = d.hour * 60 + d.minute
    return any(abs(bar0 - ev) <= marge for ev in slots(d.date(), actifs))

# --- corpus A ---------------------------------------------------------------
def corpusA():
    rows = list(csv.DictReader(open(os.path.join(HERE, "oracle_blackout.csv"))))
    key = lambda r: (r["sym"], r["tf"], r["t"], r["col"])
    g2 = {key(r) for r in rows if r["groupe"] == "2"}
    return [(r["sym"], r["tf"], r["t"], r["col"], key(r) not in g2)
            for r in rows if r["groupe"] == "4"]

# --- corpus B ---------------------------------------------------------------
def arrows(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    hdr, data = rows[0], [r for r in rows[1:] if r and r[0]]
    idx = {n.strip(): i for i, n in enumerate(hdr)}
    if not all(c in idx for c in COLS): return None, None
    a, b = set(), set()
    for r in data:
        b.add(r[0])
        for c in COLS:
            v = r[idx[c]].strip()
            if v and v not in ("0", "0.0"): a.add((r[0], c))
    return a, b

def scan(d):
    res = {}
    for p in glob.glob(os.path.join(d, "*.csv")):
        m = re.match(r"CME_MINI_(MES|NQ)Z2026, ([0-9A-Z]+)_", os.path.basename(p))
        a, b = arrows(p)
        if a is None: continue
        k = (m.group(1), m.group(2))
        res[k] = (res[k][0] | a, res[k][1] | b) if k in res else (a, b)
    return res

def corpusB():
    OFF, ON = scan(os.path.expanduser("~/ERGON/Singal")), scan(os.path.expanduser("~/ERGON/Filtres"))
    out = []
    for k in sorted(set(OFF) & set(ON)):
        common = OFF[k][1] & ON[k][1]
        for t, c in OFF[k][0]:
            if t in common:
                out.append((k[0], k[1], t, c, (t, c) not in ON[k][0]))
    return out

A, B = corpusA(), corpusB()
print("corpus A : %d fleches, %d a retirer" % (len(A), sum(1 for x in A if x[4])))
print("corpus B : %d fleches, %d a retirer" % (len(B), sum(1 for x in B if x[4])))

def ev(data, actifs, marge):
    e = t = m = 0
    det = []
    for sym, tf, ts, col, doit in data:
        b = blocked(ts, actifs, marge)
        if b and doit: e += 1
        elif b: t += 1; det.append(("TROP", sym, tf, ts, col))
        elif doit: m += 1; det.append(("MANQ", sym, tf, ts, col))
    return e, t, m, det

ALL = ["openEU", "openUS", "nfp", "jobless", "us830", "us1000", "fomc", "cust1", "cust2"]
MARGES = (0, 1, 2, 3, 5, 8, 10, 12, 15, 20, 30)
res, n = [], 0
for k in range(len(ALL) + 1):
    for sub in itertools.combinations(ALL, k):
        for mg in MARGES:
            n += 1
            ea, ta, ma, _ = ev(A, set(sub), mg)
            eb, tb, mb, _ = ev(B, set(sub), mg)
            res.append((ta + ma + tb + mb, -(ea + eb), sub, mg, (ea, ta, ma), (eb, tb, mb)))
res.sort()
print("combinaisons testees (les deux corpus) :", n)
print()
print("--- 10 meilleures ---")
seen, sh = set(), 0
for err, _, sub, mg, a, b in res:
    sig = (a, b, tuple(sorted(sub)))
    if sig in seen: continue
    seen.add(sig); sh += 1
    print("  err=%d | A exact/trop/manq = %d/%d/%d | B = %d/%d/%d | marge=%-2d | %s"
          % (err, *a, *b, mg, ",".join(sub) or "(aucun)"))
    if sh >= 10: break
print()
print("--- REGLE : us830 + us1000, marge variable ---")
for mg in MARGES:
    a = ev(A, {"us830", "us1000"}, mg)[:3]
    b = ev(B, {"us830", "us1000"}, mg)[:3]
    print("  marge=%-3d A %d/%d/%d   B %d/%d/%d" % (mg, *a, *b))
print()
print("--- creneaux du panneau ajoutes un a un a us830+us1000 (marge 3) ---")
for s in ("openEU", "openUS", "nfp", "jobless", "fomc", "cust1", "cust2"):
    a = ev(A, {"us830", "us1000", s}, 3)[:3]
    b = ev(B, {"us830", "us1000", s}, 3)[:3]
    print("  +%-8s A %d/%d/%d   B %d/%d/%d" % (s, *a, *b))
print()
print("--- ecarts restants (us830+us1000, marge 3) ---")
for tag, sym, tf, ts, col in sorted(ev(A, {"us830", "us1000"}, 3)[3] + ev(B, {"us830", "us1000"}, 3)[3], key=lambda x: x[3]):
    print("  %-5s %-4s %-4s %s %s" % (tag, sym, tf, ts[:16], col))
