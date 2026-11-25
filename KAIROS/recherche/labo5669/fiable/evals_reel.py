"""25/11 — chances de passer les évals avec la stratégie RÉELLE de Jeremy (Strat5669 56, 15 min, lecture alertes),
MNQ et MES fusionnés par jour, 17/10/2023 → 13/11/2026. Chaque trade en R (P&L / risque au stop).
FTMO 100k : objectif +10 %, perte jour 5 %, perte max 10 % (statique). Tradeify Select 50k : objectif +3 000 $,
recul EOD 2 000 $ (plancher figé à 50 100 $ une fois atteint), consistance meilleure journée ≤ 40 % du profit.
Tous les jours de départ (historique tel quel) + bootstrap par blocs de 5 jours (2 000 tirages)."""
import os, sys
import numpy as np, pandas as pd
ICI = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet")]
from decision56 import charger56
from moteur import issues, sequence
DEBUT = pd.Timestamp("2023-10-17")
rows = []
for ins in ("MNQ", "MES"):
    B = charger56(ins, 15); I = issues(B, 3.0, 0.6667, 16); vp = B.attrs["val_point"]
    per = (B.t >= DEBUT).values
    L, S = (B.gob_L.values == 1) & per, (B.gob_S.values == 1) & per
    idx = np.flatnonzero(L | S); pris, ss, pn = sequence(I, idx, np.where(L[idx], 1, -1))
    risque = 3.0 * B.atr.values[pris] * vp + 2.5          # $ par contrat au stop (+ commissions)
    jour = (B.t.values[pris] - np.timedelta64(7, "h")).astype("datetime64[D]")
    rows.append(pd.DataFrame(dict(jour=jour, R=pn / risque)))
T = pd.concat(rows)
J = T.groupby("jour").R.apply(list)                       # liste des R de chaque jour
jours = list(J.values)
print(f"{len(T)} trades, {len(jours)} jours tradés, R moyen {T.R.mean():+.3f}, gagnants {(T.R > 0).mean():.0%}")

def ftmo(seq, r):
    eq = 0.0
    for k, day in enumerate(seq):
        d = 0.0
        for R in day:
            d += R * r
            if d <= -5 or eq + d <= -10: return "sauté", k + 1
        eq += d
        if eq >= 10: return "validé", k + 1
    return "en cours", len(seq)

def tradeify(seq, risk_usd):
    eq, plafond, best, pr = 0.0, 0.0, 0.0, 0.0
    for k, day in enumerate(seq):
        d = 0.0
        for R in day:
            d += R * risk_usd
            if eq + d <= plafond - 2000: return "sauté", k + 1
        eq += d; best = max(best, d)
        plafond = min(max(plafond, eq), 2100)            # recul EOD, figé à +100 $
        if eq >= 3000 and best <= 0.4 * eq: return "validé", k + 1
    return "en cours", len(seq)

rng = np.random.default_rng(0)
def tirages(n=2000, L=250):
    for _ in range(n):
        s = []
        while len(s) < L:
            i = rng.integers(0, len(jours) - 5); s += jours[i:i + 5]
        yield s[:L]
print("\nFTMO 100k — risque par trade (% du compte)")
for r in (0.5, 1, 1.5, 2, 3):
    res = [ftmo(s, r) for s in tirages()]
    v = np.mean([a == "validé" for a, _ in res]); sa = np.mean([a == "sauté" for a, _ in res])
    dur = np.median([k for a, k in res if a == "validé"]) if v else np.nan
    print(f"  {r:>3} % : validé {v:.0%} · sauté {sa:.0%} · durée médiane si validé {dur:.0f} jours tradés")
print("\nTradeify 50k — risque par trade ($), départ à 0")
for u in (150, 250, 350, 450, 600):
    res = [tradeify(s, u) for s in tirages()]
    v = np.mean([a == "validé" for a, _ in res]); sa = np.mean([a == "sauté" for a, _ in res])
    dur = np.median([k for a, k in res if a == "validé"]) if v else np.nan
    print(f"  {u:>4} $ : validé {v:.0%} · sauté {sa:.0%} · durée médiane si validé {dur:.0f} jours tradés")

# --- État réel des comptes au 21/11 (captures de Jeremy) ---
def ftmo_etat(seq, r, eq0=3.38):            # % au-dessus de 100k ; objectif +10 % ; perte max à −10 % (90k)
    eq = eq0
    for k, day in enumerate(seq):
        d = 0.0
        for R in day:
            d += R * r
            if d <= -5 or eq + d <= -10: return "sauté", k + 1
        eq += d
        if eq >= 10: return "validé", k + 1
    return "en cours", len(seq)
def tradeify_etat(seq, u, eq0=770.0, plafond0=1301.0, best0=603.8):
    eq, plafond, best = eq0, plafond0, best0
    for k, day in enumerate(seq):
        d = 0.0
        for R in day:
            d += R * u
            if eq + d <= plafond - 2000: return "sauté", k + 1
        eq += d; best = max(best, d); plafond = min(max(plafond, eq), 2100)
        if eq >= 3000 and best <= 0.4 * eq: return "validé", k + 1
    return "en cours", len(seq)
print("\nFTMO depuis l'état réel (+3,38 %)")
for r in (0.5, 1, 1.5, 2, 3):
    res = [ftmo_etat(s, r) for s in tirages()]
    v = np.mean([a == "validé" for a, _ in res]); dur = np.median([k for a, k in res if a == "validé"]) if v else np.nan
    print(f"  {r:>3} % : validé {v:.0%} · sauté {np.mean([a == 'sauté' for a, _ in res]):.0%} · durée médiane {dur:.0f} jours tradés")
print("\nTradeify depuis l'état réel (+770 $, plancher à 1 469 $ sous le solde)")
for u in (150, 250, 350, 450):
    res = [tradeify_etat(s, u) for s in tirages()]
    v = np.mean([a == "validé" for a, _ in res]); dur = np.median([k for a, k in res if a == "validé"]) if v else np.nan
    print(f"  {u:>4} $ : validé {v:.0%} · sauté {np.mean([a == 'sauté' for a, _ in res]):.0%} · durée médiane {dur:.0f} jours tradés")
