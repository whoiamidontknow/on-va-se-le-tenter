"""Banc d'essai du 56 (labo5669). Étape 3 : référence « entrées au hasard ».

Période de RECHERCHE seulement (05/2019 → 12/2024) : 2025-2026 reste sous scellé.

Chaque bougie du relevé (déclencheur dans au moins un sens, filtres communs respectés : com = 1)
a une issue déterministe dans chaque sens (simu56.un_trade). Une stratégie = une suite de signaux
(bougie, sens) passée dans la même règle « une position à la fois ».

Deux références, 1 000 tirages chacune, calées sur le 56 de la même lecture :
  A. bougies tirées au hasard, sens au hasard (même part de longs que le 56) ;
  B. bougies tirées au hasard, sens du déclencheur (le 56 sans ses filtres Dashator / eMax).
Le tirage suit la répartition horaire (heure de Paris) des signaux du 56, et sa densité est réglée
pour donner le même nombre de trades que le 56.

    uv run -q --with pandas --with openpyxl python banc.py 3
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "dataset"))
from releve import charger  # noqa: E402
from simu56 import un_trade, ouvertures, QTY, COMM  # noqa: E402

DEBUT, FIN_RECHERCHE = pd.Timestamp("2019-05-01"), pd.Timestamp("2025-01-01")
TIRAGES = 1000
GRAINE = 5669


def issues(R):
    """Table des bougies candidates avec, pour chaque sens, P&L par contrat, raison, heure de liberté."""
    vp = R.attrs["val_point"]
    opn = ouvertures(R)
    C = R[R.parcours & (R.com == 1) & (R.t1 >= DEBUT) & (R.t1 < FIN_RECHERCHE)].sort_values("t1").reset_index(drop=True)
    out = {}
    for d, s in ((1, "L"), (-1, "S")):
        p, lib, rs, sl = [], [], [], []
        for r in C.itertuples(index=False):
            tr, libre = un_trade(r, d, opn)
            p.append((tr["sortie"] - tr["entree"]) * d * vp - 2 * COMM)
            lib.append(libre)
            rs.append(tr["raison"])
        out[f"p1_{s}"], out[f"lib_{s}"], out[f"r_{s}"] = p, lib, rs
    for k, v in out.items():
        C[k] = v
    C["h"] = C.t1.dt.hour
    return C


def sequence(C, choix, sens):
    """choix : indices de C triés ; sens : +1 / -1 par indice. Une position à la fois. Rend P&L (2 contrats)."""
    t1 = C.t1.values
    libL, libS = C.lib_L.values, C.lib_S.values
    pL, pS = C.p1_L.values, C.p1_S.values
    libre = np.datetime64("1970-01-01")
    pn = []
    for i, d in zip(choix, sens):
        if t1[i] < libre:
            continue
        if d > 0:
            pn.append(pL[i] * QTY)
            libre = libL[i]
        else:
            pn.append(pS[i] * QTY)
            libre = libS[i]
    return np.array(pn)


def mesures(pn):
    if len(pn) == 0:
        return dict(n=0, gain=np.nan, pnl=0.0, par_trade=np.nan, baisse_max=0.0)
    cum = np.cumsum(pn)
    dd = np.max(np.maximum.accumulate(np.concatenate([[0], cum]))[1:] - cum)
    return dict(n=len(pn), gain=(pn > 0).mean(), pnl=pn.sum(), par_trade=pn.mean(), baisse_max=dd)


def strategie56(C, lecture):
    gl, gs = ("go56_L", "go56_S") if lecture == "o" else ("go56b_L", "go56b_S")
    m = (C[gl] == 1) | (C[gs] == 1)
    idx = np.flatnonzero(m.values)
    sens = np.where(C[gl].values[idx] == 1, 1, -1)
    return idx, sens


def tirages(C, idx56, sens56, n56, ref, rng):
    # poids horaires : densité des signaux du 56 par heure rapportée à celle des candidates
    h = C.h.values
    w56 = np.bincount(h[idx56], minlength=24).astype(float)
    wc = np.bincount(h, minlength=24).astype(float)
    w = np.where(wc > 0, w56 / np.maximum(wc, 1), 0)
    w = w / w.max()
    p_long = (sens56 > 0).mean()
    dL, dS = C.d_L.notna().values, C.d_S.notna().values

    def un(c, rng):
        sel = np.flatnonzero(rng.random(len(C)) < c * w[h])
        if ref == "A":
            s = np.where(rng.random(len(sel)) < p_long, 1, -1)
        else:
            both = dL[sel] & dS[sel]
            s = np.where(dL[sel] & ~dS[sel], 1, np.where(dS[sel] & ~dL[sel], -1, 0))
            s[both] = np.where(rng.random(both.sum()) < 0.5, 1, -1)
        return sequence(C, sel, s)

    # réglage de la densité c pour viser n56 trades (bissection sur la moyenne de 20 tirages)
    lo, hi = 0.0, 1.0
    r0 = np.random.default_rng(1)
    for _ in range(14):
        c = (lo + hi) / 2
        n = np.mean([len(un(c, r0)) for _ in range(20)])
        lo, hi = (c, hi) if n < n56 else (lo, c)
    c = (lo + hi) / 2
    return pd.DataFrame([mesures(un(c, rng)) for _ in range(TIRAGES)]), c


def etape3():
    rng = np.random.default_rng(GRAINE)
    lignes = []
    for ins in ("MNQ", "MES"):
        R = charger(ins, controle=False)
        C = issues(R)
        print(f"\n{ins} : {len(C)} bougies candidates, {C.t1.min():%d/%m/%Y} → {C.t1.max():%d/%m/%Y}")
        for lec in ("o", "b"):
            idx, sens = strategie56(C, lec)
            m56 = mesures(sequence(C, idx, sens))
            for ref in ("A", "B"):
                D, c = tirages(C, idx, sens, m56["n"], ref, rng)
                rang = {k: (D[k] >= m56[k]).mean() for k in ("gain", "pnl", "par_trade")}
                rang["baisse_max"] = (D.baisse_max <= m56["baisse_max"]).mean()
                lignes.append(dict(instrument=ins, lecture=lec, reference=ref, n56=m56["n"], gain56=m56["gain"],
                                   pnl56=m56["pnl"], dd56=m56["baisse_max"], n_hasard=D.n.median(),
                                   gain_hasard=D.gain.median(), pnl_hasard_med=D.pnl.median(),
                                   pnl_hasard_p95=D.pnl.quantile(0.95), dd_hasard=D.baisse_max.median(),
                                   p_gain=rang["gain"], p_pnl=rang["pnl"], p_dd=rang["baisse_max"]))
                print(f"  lecture {lec} · réf {ref} : 56 = {m56['n']} trades, {m56['gain']:.1%}, {m56['pnl']:,.0f} $, baisse max {m56['baisse_max']:,.0f} $"
                      f" | hasard médian {D.n.median():.0f} trades, {D.gain.median():.1%}, {D.pnl.median():,.0f} $ (95e centile {D.pnl.quantile(.95):,.0f}),"
                      f" baisse {D.baisse_max.median():,.0f} | part des tirages >= 56 : gain {rang['gain']:.3f}, P&L {rang['pnl']:.3f}")
    T = pd.DataFrame(lignes)
    T.to_csv(os.path.join(os.path.dirname(__file__), "resultats_etape3.csv"), index=False)
    return T


# ══════════════════════════════════════════════════════════════════════════════════
# Étape 4 : évaluations propfirm, rejouées depuis chaque jour de départ + rééchantillonnage
# par blocs de 5 jours. Règles données par DAEMON le 19/11 (H = hypothèse de KAIROS).
# ══════════════════════════════════════════════════════════════════════════════════
COMPTES = {
    # Tradeify Select 50k : +3 000 $, plancher suiveur 2 000 $ fin de journée (H : pas de blocage du
    # plancher), consistance 40 %, risque 450 $ par trade, MNQ seul si MNQ et MES dans le même sens
    # (H : un trade MES qui chevauche un trade MNQ de même sens est sauté).
    "Tradeify Select 50k": dict(type="suiveur", depart=50000, objectif=3000, plancher=2000, consistance=0.40,
                                risque=450, instruments=("MNQ", "MES"), mnq_seul=True, jour="cme"),
    # FTMO 100k 2-step : phase 1 +10 %, phase 2 +5 %, perte max 10 % statique, perte du jour 5 % du
    # capital initial depuis le solde d'ouverture du jour, risque 2 % (2 000 $), 2 stops max par jour.
    # H : 4 jours de trading minimum par phase ; MNQ et MES pris tous les deux ; contrats futures
    # micro à la place des CFD ; jour = minuit heure de Paris.
    "FTMO 100k 2-step": dict(type="ftmo", depart=100000, phases=(10000, 5000), perte_max=10000, perte_jour=5000,
                             risque=2000, instruments=("MNQ", "MES"), stops_jour=2, jours_min=4, jour="paris"),
    # Lucid Flex 50k : 300 $ visés, max 2 micros, arrêt du jour après 2 pertes ou -400 $.
    # H : objectif +3 000 $, plancher suiveur 2 000 $ fin de journée, consistance 50 % ; et surtout
    # le bot trade le MNQ 5 min, pas le 56 en 15 min : ce n'est qu'une approximation du compte.
    "Lucid Flex 50k (H : 56 MNQ 15 min, pas le bot)": dict(type="suiveur", depart=50000, objectif=3000, plancher=2000,
                                                          consistance=0.50, risque=300, max_contrats=2,
                                                          instruments=("MNQ",), pertes_jour=2, perte_jour_max=400,
                                                          jour="cme"),
}
BLOC, CHEMINS, LONGUEUR = 5, 1000, 250


def trades56(ins, lecture):
    """Trades du 56 sur la période de recherche, avec P&L par contrat, stop en points et étiquette GODLIKE."""
    from simu56 import simuler
    R = charger(ins, controle=False)
    attrs = dict(R.attrs)
    R = R[R.t1 < FIN_RECHERCHE].copy()
    R.attrs.update(attrs)
    S = simuler(R, lecture=lecture)
    S = S[S.t1 >= DEBUT].copy()
    d = np.where(S.sens == "L", 1, -1)
    S["d"] = d
    S["p1"] = (S.sortie - S.entree) * d * attrs["val_point"] - 2 * COMM
    g = R.set_index("t1")["gd_o" if lecture == "o" else "gd_b"]
    S["gd"] = S.t1.map(g).values == d
    S["ins"] = ins
    S["vp"] = attrs["val_point"]
    return S


def jour_de(t, regle):
    t = pd.DatetimeIndex(t).tz_localize("Europe/Paris", ambiguous="NaT", nonexistent="shift_forward")
    if regle == "cme":   # séance CME : 17:00 Chicago -> date du lendemain
        return (t.tz_convert("America/Chicago") + pd.Timedelta(hours=7)).date
    return t.date


def jours_compte(cpt, lecture, godlike):
    """Liste ordonnée (jour, [P&L des trades du jour]) après tailles et règles du jour du compte."""
    T = pd.concat([trades56(i, lecture) for i in cpt["instruments"]]).sort_values("t1").reset_index(drop=True)
    if godlike:
        T = T[T.gd]
    if cpt.get("mnq_seul"):
        mnq = T[T.ins == "MNQ"]
        garde = []
        for r in T.itertuples():
            if r.ins == "MES":
                ch = mnq[(mnq.d == r.d) & (mnq.t1 < r.tx) & (mnq.tx > r.t1)]
                if len(ch):
                    continue
            garde.append(r.Index)
        T = T.loc[garde]
    n = np.floor(cpt["risque"] / (T.sl * T.vp))
    if "max_contrats" in cpt:
        n = np.minimum(n, cpt["max_contrats"])
    T = T.assign(n=n)
    T = T[T.n >= 1]
    T = T.assign(pnl=T.n * T.p1, jour=jour_de(T.tx.values, cpt["jour"]))
    # calendrier : tous les jours de séance de la période (bougies du relevé), même sans trade
    R = charger("MNQ", controle=False)
    cal = sorted(set(jour_de(R.t1[(R.t1 >= DEBUT) & (R.t1 < FIN_RECHERCHE)].values, cpt["jour"])))
    par_jour = {j: g.sort_values("tx") for j, g in T.groupby("jour")}
    jours = []
    for j in cal:
        g = par_jour.get(j)
        pn = []
        if g is not None:
            pertes = stops = 0
            cumul = 0.0
            for r in g.itertuples():
                if cpt.get("stops_jour") and stops >= cpt["stops_jour"]:
                    break
                if cpt.get("pertes_jour") and (pertes >= cpt["pertes_jour"] or cumul <= -cpt["perte_jour_max"]):
                    break
                pn.append(r.pnl)
                cumul += r.pnl
                pertes += r.pnl < 0
                stops += r.raison == "stop"
        jours.append((j, np.array(pn)))
    return jours, len(T)


def evaluer(jours, cpt):
    """Rejoue une évaluation sur une suite de jours. Rend (statut, jours écoulés)."""
    if cpt["type"] == "suiveur":
        bal = haut = cpt["depart"]
        plancher = bal - cpt["plancher"]
        meilleur = 0.0
        for k, (_, pn) in enumerate(jours, 1):
            for p in pn:
                bal += p
                if bal <= plancher:
                    return "échec", k
            meilleur = max(meilleur, pn.sum())
            haut = max(haut, bal)
            plancher = haut - cpt["plancher"]
            prof = bal - cpt["depart"]
            if prof >= cpt["objectif"] and meilleur <= cpt["consistance"] * prof:
                return "réussi", k
        return "en cours", len(jours)
    # FTMO : phases successives, chacune repart de 100 000 $
    k0 = 0
    for obj in cpt["phases"]:
        bal = cpt["depart"]
        nj = 0
        fini = False
        for k in range(k0, len(jours)):
            _, pn = jours[k]
            ouv = bal
            for p in pn:
                bal += p
                if bal < cpt["depart"] - cpt["perte_max"] or bal < ouv - cpt["perte_jour"]:
                    return "échec", k + 1
            nj += len(pn) > 0
            if bal - cpt["depart"] >= obj and nj >= cpt["jours_min"]:
                k0, fini = k + 1, True
                break
        if not fini:
            return "en cours", len(jours)
    return "réussi", k0


def etape4():
    rng = np.random.default_rng(GRAINE)
    lignes = []
    for nom, cpt in COMPTES.items():
        for lec in ("o", "b"):
            for gl in (False, True):
                jours, ntr = jours_compte(cpt, lec, gl)
                res = [evaluer(jours[i:], cpt) for i in range(len(jours))]
                st = pd.Series([r[0] for r in res])
                dur = pd.Series([r[1] for r in res])
                # rééchantillonnage par blocs de 5 jours, chemins de 250 jours
                nb = len(jours) - BLOC
                bs = []
                for _ in range(CHEMINS):
                    deb = rng.integers(0, nb, LONGUEUR // BLOC)
                    ch = [jours[d + i] for d in deb for i in range(BLOC)]
                    bs.append(evaluer(ch, cpt))
                bst = pd.Series([b[0] for b in bs])
                bdu = pd.Series([b[1] for b in bs])
                L = dict(compte=nom, lecture=lec, trades="GODLIKE" if gl else "tous", n_trades=ntr,
                         departs=len(res), reussi=(st == "réussi").mean(), echec=(st == "échec").mean(),
                         en_cours=(st == "en cours").mean(), jours_reussite_med=dur[st == "réussi"].median(),
                         jours_echec_med=dur[st == "échec"].median(), bs_reussi=(bst == "réussi").mean(),
                         bs_echec=(bst == "échec").mean(), bs_jours_reussite_med=bdu[bst == "réussi"].median())
                lignes.append(L)
                print(f"{nom} · lecture {lec} · {L['trades']} ({ntr} trades) : réussi {L['reussi']:.0%}, échec {L['echec']:.0%},"
                      f" en cours {L['en_cours']:.0%}, {L['jours_reussite_med']} j médian pour réussir"
                      f" | blocs : réussi {L['bs_reussi']:.0%}, échec {L['bs_echec']:.0%}")
    T = pd.DataFrame(lignes)
    T.to_csv(os.path.join(os.path.dirname(__file__), "resultats_etape4.csv"), index=False)
    return T


if __name__ == "__main__":
    if "3" in sys.argv[1:]:
        etape3()
    if "4" in sys.argv[1:]:
        etape4()
