#!/usr/bin/env python3
"""
BLACKOUT NO-TRADE — test du panneau de reglages sur donnees.

Oracle : oracle_blackout.csv (produit par sim_blackout_oracle.py).
On part des 176 fleches du groupe 4 et on cherche le jeu de creneaux +
semantique + marge qui reproduit les 161 fleches du groupe 2.

Comptage maison : exact (retiree a juste titre), trop (retiree a tort),
manque (oubliee = g4\\g2 non retiree).
"""
import csv, datetime as dt, itertools, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.join(HERE, "oracle_blackout.csv")

TF_MIN = {"2": 2, "5": 5, "15": 15, "30": 30, "60": 60, "240": 240, "1D": 1440}

# ---------------------------------------------------------------- fuseaux
# Donnees : 2026-06 -> 2026-10-09.  Paris passe en hiver le 2026-10-25,
# New York le 2026-11-01 : sur toute la periode Paris=UTC+2 et ET=UTC-4,
# donc ET -> Paris = +6 h constant.  Verifie par offsets_dst() ci-dessous.
def paris_offset(d):
    """offset UTC de Europe/Paris, en heures, pour une date (regle UE)."""
    y = d.year
    # dernier dimanche de mars / octobre
    mar = max(x for x in range(25, 32) if dt.date(y, 3, x).weekday() == 6)
    oct_ = max(x for x in range(25, 32) if dt.date(y, 10, x).weekday() == 6)
    return 2 if dt.date(y, 3, mar) <= d.date() < dt.date(y, 10, oct_) else 1

def et_offset(d):
    """offset UTC de America/New_York, en heures (2e dim. mars -> 1er dim. nov.)."""
    y = d.year
    mar = [x for x in range(8, 15) if dt.date(y, 3, x).weekday() == 6][0]
    nov = [x for x in range(1, 8) if dt.date(y, 11, x).weekday() == 6][0]
    return -4 if dt.date(y, 3, mar) <= d.date() < dt.date(y, 11, nov) else -5

def et_to_paris_minutes(d, h, m):
    """heure ET -> minute-de-journee en heure de Paris, pour le jour d."""
    shift = paris_offset(d) - et_offset(d)      # 6 en ete, 6 en hiver, 5 pendant la zone grise
    return h * 60 + m + shift * 60

# ---------------------------------------------------------------- creneaux
def nth_weekday(d, weekday, n):
    """d est-il le n-ieme <weekday> du mois ?"""
    return d.weekday() == weekday and (d.day - 1) // 7 == n - 1

def slots_for_day(d, actifs):
    """liste des minutes-de-journee (heure de Paris) a bloquer ce jour-la."""
    out = []
    if "openEU" in actifs:                       # 09:00 Europe/Paris
        out.append(("openEU", 9 * 60))
    if "openUS" in actifs:                       # 09:30 ET
        out.append(("openUS", et_to_paris_minutes(d, 9, 30)))
    if "nfp" in actifs and nth_weekday(d.date(), 4, 1):      # 1er vendredi 08:30 ET
        out.append(("nfp", et_to_paris_minutes(d, 8, 30)))
    if "jobless" in actifs and d.weekday() == 3:             # jeudi 08:30 ET
        out.append(("jobless", et_to_paris_minutes(d, 8, 30)))
    if "us830" in actifs:                                    # 08:30 ET tous les jours
        out.append(("us830", et_to_paris_minutes(d, 8, 30)))
    if "us1000" in actifs:                                   # 10:00 ET tous les jours
        out.append(("us1000", et_to_paris_minutes(d, 10, 0)))
    if "fomc" in actifs and d.weekday() == 2:                # mercredi 14:00 ET
        out.append(("fomc", et_to_paris_minutes(d, 14, 0)))
    if "cust1" in actifs:                                    # creneau 1 : 14:30 ET
        out.append(("cust1", et_to_paris_minutes(d, 14, 30)))
    if "cust2" in actifs:                                    # creneau 2 : 20:00 ET
        out.append(("cust2", et_to_paris_minutes(d, 20, 0)))
    return out

ALL_SLOTS = ["openEU", "openUS", "nfp", "jobless", "us830", "us1000", "fomc",
             "cust1", "cust2"]
PANEL = {"openEU", "openUS", "nfp", "jobless", "us830", "us1000"}   # coches a l'ecran

# ---------------------------------------------------------------- semantiques
def blocked(d, tfmin, actifs, marge, mode):
    """d = datetime d'OUVERTURE de la bougie (heure de Paris, naive ou aware)."""
    bar0 = d.hour * 60 + d.minute
    bar1 = bar0 + tfmin
    for _, ev in slots_for_day(d, actifs):
        lo, hi = ev - marge, ev + marge
        if mode == "open":        # le test porte sur l'heure d'ouverture de la bougie
            if lo <= bar0 <= hi:
                return True
        elif mode == "inter":     # la fenetre croise l'intervalle de la bougie
            if bar0 < hi and lo < bar1:
                return True
        elif mode == "contient":  # la bougie contient l'instant de l'annonce
            if bar0 <= ev < bar1:
                return True
    return False

# ---------------------------------------------------------------- donnees
rows = list(csv.DictReader(open(ORACLE)))
key = lambda r: (r["sym"], r["tf"], r["t"], r["col"])
g2 = {key(r) for r in rows if r["groupe"] == "2"}
g4 = [r for r in rows if r["groupe"] == "4"]
for r in g4:
    t = r["t"]
    r["dt"] = dt.datetime.fromisoformat(t).replace(tzinfo=None)
    r["doit_partir"] = key(r) not in g2
CIBLE = sum(1 for r in g4 if r["doit_partir"])
print("groupe 4 : %d fleches | groupe 2 : %d | a retirer : %d" % (len(g4), len(g2), CIBLE))

def evaluate(actifs, marge, mode, par_tf=False):
    ex = trop = manq = 0
    detail = []
    per = collections.defaultdict(lambda: [0, 0, 0])
    for r in g4:
        b = blocked(r["dt"], TF_MIN[r["tf"]], actifs, marge, mode)
        bucket = "15m" if r["tf"] == "15" else ("2m" if r["tf"] == "2" else "autres")
        if b and r["doit_partir"]:
            ex += 1; per[bucket][0] += 1
        elif b:
            trop += 1; per[bucket][1] += 1; detail.append(("TROP", r))
        elif r["doit_partir"]:
            manq += 1; per[bucket][2] += 1; detail.append(("MANQ", r))
    return (ex, trop, manq, detail, per) if par_tf else (ex, trop, manq, detail)

# ---------------------------------------------------------------- balayage
best = []
combos = 0
for nactifs in range(len(ALL_SLOTS) + 1):
    pass
for k in range(0, len(ALL_SLOTS) + 1):
    for sub in itertools.combinations(ALL_SLOTS, k):
        for marge in (0, 1, 2, 3, 5, 10, 15, 30):
            for mode in ("open", "inter", "contient"):
                combos += 1
                ex, trop, manq, _ = evaluate(set(sub), marge, mode)
                best.append((trop + manq, -ex, trop, manq, ex, sub, marge, mode))
best.sort()
print("combinaisons testees :", combos)
print()
print("--- 12 meilleures combinaisons (erreurs = trop + manque) ---")
seen = set()
shown = 0
for err, nex, trop, manq, ex, sub, marge, mode in best:
    sig = (trop, manq, tuple(sorted(sub)), mode)
    if sig in seen:
        continue
    seen.add(sig)
    print("  err=%2d  exactes=%2d trop=%2d manque=%2d | marge=%-2d mode=%-8s | %s"
          % (err, ex, trop, manq, marge, mode, ",".join(sub) or "(aucun)"))
    shown += 1
    if shown >= 12:
        break

print()
print("--- le panneau tel quel (6 creneaux coches, +/-3 min) ---")
for mode in ("open", "inter", "contient"):
    ex, trop, manq, det = evaluate(PANEL, 3, mode)
    print("  mode=%-8s exactes=%2d trop=%2d manque=%2d" % (mode, ex, trop, manq))

print()
print("--- creneau par creneau, mode=open marge=3 ---")
for s in ALL_SLOTS:
    ex, trop, manq, det = evaluate({s}, 3, "open")
    print("  %-8s exactes=%2d trop=%2d (manque=%2d)" % (s, ex, trop, manq))

print()
print("--- REGLE RETENUE : us1000 seul, mode=open, marge=3 ---")
ex, trop, manq, det, per = evaluate({"us1000"}, 3, "open", par_tf=True)
print("  exactes=%d trop=%d manque=%d" % (ex, trop, manq))
for b in ("2m", "15m", "autres"):
    print("    %-7s exact=%d trop=%d manque=%d" % (b, *per[b]))
print("  oubliees :")
for tag, r in det:
    print("    %-5s %-4s %-4s %s %s  %s" % (tag, r["sym"], r["tf"],
          r["dt"].strftime("%Y-%m-%d %H:%M"), r["dt"].strftime("%a"), r["col"]))

print()
print("--- stabilite de la marge (us1000 seul, mode=open) ---")
for marge in (0, 1, 2, 3, 5, 10, 15, 30):
    ex, trop, manq, _ = evaluate({"us1000"}, marge, "open")
    print("  marge=%-3d exactes=%2d trop=%2d manque=%2d" % (marge, ex, trop, manq))

print()
print("--- controle DST : decalage ET->Paris sur la periode des donnees ---")
seen = {}
d = dt.date(2026, 6, 1)
while d <= dt.date(2026, 12, 31):
    dd = dt.datetime(d.year, d.month, d.day)
    seen.setdefault(paris_offset(dd) - et_offset(dd), []).append(d)
    d += dt.timedelta(days=1)
for k, v in sorted(seen.items()):
    print("  +%dh : %s -> %s (%d jours)" % (k, v[0], v[-1], len(v)))
print("  derniere fleche des donnees :", max(r["dt"] for r in g4).date())
