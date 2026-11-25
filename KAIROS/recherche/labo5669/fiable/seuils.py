"""25/11 — tableau des seuils de fiabilité en 15 et 5 min, période de Jeremy (17/10/2023 → 13/11/2026, Relevés complets).

Score = p1 × p4 : p_tf = P(couleur du Dashator en cours = couleur finale | |valeur en cours| en quintiles, part écoulée
en quarts). Tables apprises sur la 1re moitié (17/10/2023 → 01/05/2025), sur les bougies qui ont un déclencheur du 56
(comme les lignes du Relevé 5669), réapprises aussi en 15 min. Part écoulée calculée comme Strat5669_FIABLE (heure de
Paris, minute de clôture / 60 ; (heure % 4) × 60 + minute / 240), pour que les tables collent au Pine.
« alertes » = décisions en lecture b (bougie en cours) ; « graphique » = case Graphique = alertes cochée (o ET b).
Fantôme = trade d'alerte dont la bougie n'a pas la décision en lecture o (absent du graphique d'origine).
Une position à la fois, 2 contrats, moteur complet/moteur.py (56 : 3 ATR, 0,6667 R, 16 bougies).
Le scellé 2025-26 est ouvert (décision de Jeremy du 25/11) : la 2de moitié en fait partie.

    uv run --with pandas --with openpyxl python seuils.py      → resultats_seuils.csv, tables_pine_5min.txt
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, "..", "complet")]
from decision56 import charger56, DECL  # noqa: E402
from moteur import issues, sequence  # noqa: E402

DEBUT, MILIEU = pd.Timestamp("2023-10-17"), pd.Timestamp("2025-05-01")
COUPE_E = [0, .26, .51, .76, 1.0]
QTY = 2


def ecoule_pine(B):
    tc = B.t + pd.Timedelta(minutes=B.attrs["unite"])          # clôture de la bougie, heure de Paris
    m, h = tc.dt.minute.values, tc.dt.hour.values
    q = (h % 4) * 60 + m
    return np.where(m == 0, 1.0, m / 60), np.where(q == 0, 1.0, q / 240)


def tables(B, appr):
    """Quintiles de |b| et table 5 × 4 de P(couleur inchangée), apprises sur les bougies appr ; score de chaque bougie."""
    e = dict(zip("14", ecoule_pine(B)))
    out, p = {}, {}
    for tf in "14":
        b, o = B[f"b{tf}"].values, B[f"o{tf}"].values
        ok = (b > 0) == (o > 0)
        val = np.isfinite(b) & np.isfinite(o)
        a = np.abs(b)
        qa = np.quantile(a[appr & val], [.2, .4, .6, .8])
        r = np.searchsorted(qa, a, side="left")                # a ≤ qa[i] → ligne i, comme f_fiP
        c = np.digitize(e[tf], COUPE_E[1:-1], right=True)
        tab = np.full((5, 4), np.nan)
        for i in range(5):
            for j in range(4):
                m = appr & val & (r == i) & (c == j)
                tab[i, j] = ok[m].mean() if m.any() else np.nan
        pt = np.where(np.isfinite(b) & (a <= 99), tab[np.minimum(r, 4), c], np.nan)
        out[tf] = (qa, tab)
        p[tf] = pt
    return out, p["1"] * p["4"]


def dd(p):
    c = np.cumsum(p)
    return float(np.max(np.maximum.accumulate(np.r_[0, c])[1:] - c)) if len(p) else 0.0


def tableau(B, score):
    I = issues(B, 3.0, 0.6667, 16)
    t = B.t.values
    per = (B.t >= DEBUT).values
    goo = {1: B.goo_L.values == 1, -1: B.goo_S.values == 1}
    lignes = []
    for s in range(0, 100, 5):
        f = per & ((score >= s / 100) if s else True)
        res = {}
        for nom, L, S in (("a", B.gob_L.values == 1, B.gob_S.values == 1),
                          ("g", (B.gob_L.values == 1) & goo[1], (B.gob_S.values == 1) & goo[-1])):
            idx = np.flatnonzero(f & (L | S))
            sens = np.where(L[idx], 1, -1)
            pris, ss, pn = sequence(I, idx, sens)
            res[nom] = (pris, ss, pn * QTY)
        pris, ss, pn = res["a"]
        fant = np.array([not goo[d][i] for i, d in zip(pris, ss)])
        gp, _, gpn = res["g"]
        for moitie, m, mg in (("1re moitié", t[pris] < MILIEU, t[gp] < MILIEU),
                              ("2de moitié", t[pris] >= MILIEU, t[gp] >= MILIEU),
                              ("total", np.ones(len(pris), bool), np.ones(len(gp), bool))):
            d0, d1 = (DEBUT, MILIEU) if moitie == "1re moitié" else (MILIEU, B.t.max()) if moitie == "2de moitié" \
                else (DEBUT, B.t.max())
            mois = (d1 - d0).days / 30.44
            lignes.append(dict(moitie=moitie, seuil=s, trades=int(m.sum()), trades_mois=m.sum() / mois,
                               fantomes=fant[m].mean() if m.any() else np.nan,
                               gagnants=(pn[m] > 0).mean() if m.any() else np.nan,
                               alertes_usd=pn[m].sum(), dd_usd=dd(pn[m]),
                               graphique_trades=int(mg.sum()), graphique_usd=gpn[mg].sum()))
    r = pd.DataFrame(lignes)
    r["ecart_seuil0"] = r.alertes_usd - r.groupby("moitie").alertes_usd.transform("first")
    return r


def pine(ins, tabs):
    suf = "N" if ins == "MNQ" else "E"
    lignes = []
    for tf in "14":
        qa, tab = tabs[tf]
        lignes.append(f"var array<float> fi_q{tf}{suf} = array.from({', '.join(f'{x:.3f}' for x in qa)})")
        lignes.append(f"var array<float> fi_t{tf}{suf} = array.from({', '.join(f'{x * 100:.2f}' for x in tab.ravel())})")
    return lignes


if __name__ == "__main__":
    tout, txt = [], ["// Tables 5 min (labo fiable/seuils.py, apprises du 17/10/2023 au 01/05/2025, bougies avec déclencheur du 56)",
                     "// lignes = |valeur| ≤ quintile 1..4 puis au-delà ; colonnes = part écoulée ≤ 26 / 51 / 76 / 100 % ; en %"]
    pd.set_option("display.width", 250)
    for u in (15, 5):
        for ins in ("MNQ", "MES"):
            B = charger56(ins, u)
            at = dict(B.attrs)
            B = B[B.t >= DEBUT - pd.Timedelta(days=3)].reset_index(drop=True)
            B.attrs.update(at)
            trig = B[[f"{d}_{s}" for d in DECL for s in "LS"]].values.any(axis=1)
            appr = trig & (B.t >= DEBUT).values & (B.t < MILIEU).values
            tabs, score = tables(B, appr)
            r = tableau(B, score)
            r.insert(0, "instrument", ins)
            r.insert(0, "unite", f"{u} min")
            tout.append(r)
            print(f"\n===== {u} min {ins} — tables : 1 h {np.round(tabs['1'][1] * 100).astype(int).tolist()}")
            print(f"                    4 h {np.round(tabs['4'][1] * 100).astype(int).tolist()}")
            print(r.drop(columns=["unite", "instrument"]).round({"trades_mois": 1, "fantomes": 2, "gagnants": 2, "alertes_usd": 0,
                                                              "dd_usd": 0, "graphique_usd": 0, "ecart_seuil0": 0}).to_string(index=False))
            if u == 5:
                txt += [f"// {ins} 5 min"] + pine(ins, tabs)
    pd.concat(tout).to_csv(os.path.join(ICI, "resultats_seuils.csv"), index=False)
    open(os.path.join(ICI, "tables_pine_5min.txt"), "w").write("\n".join(txt) + "\n")
