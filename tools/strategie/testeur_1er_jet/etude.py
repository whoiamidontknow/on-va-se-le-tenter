"""Étude approfondie du préréglage A (climax BUY + TREND 1H, long seul, stop 2 ATR,
sortie Heishinator) sur le backtest TradingView de 3 ans, NQ1! et ES1! en 15 min.

    ~/venv-quant/bin/python etude.py          -> sortie_etude.txt + graphiques PNG

MESURÉ : tout ce qui vient directement de l'export (P&L, MFE/MAE, durée, sortie).
ESTIMÉ  : 1 R par trade (risque.py, ±25 % par trade), le correctif du bug de la
          bougie de remplissage, la dérive du marché, les variantes de sortie.
"""
import sys
import numpy as np
import pandas as pd

import charge
import risque

OUT = "/Users/jeremk/Ephore/on-va-se-le-tenter/tools/strategie/testeur_1er_jet/"
# Correctif du bug : nombre de trades « sortis au signal » qui ont en fait plongé
# sous le stop prévu sur la bougie 0. Le seuil MAE/R > 1 ne marche pas (le bruit
# de R suffit à expliquer ces dépassements). Estimation : n_sûrs (trades stoppés
# avec plongée visible) × (non stoppés / stoppés), appliquée aux N trades au plus
# fort MAE/R. FACTEUR_BUG permet la sensibilité (0 = aucun, 2 = double).
FACTEUR_BUG = 1.0
MILIEU = pd.Timestamp("2025-04-15")
RNG = np.random.default_rng(7)
B = 4000
# Nombre de bougies 15 min de la plage (Globex 23 h/j, 5 j/sem, ~155,3 semaines,
# moins ~27 jours fériés/fermetures anticipées) : approximation documentée.
MOIS = {}
N_BARRES = int(155.3 * 5 * 92 - 27 * 60)


def P(*a):
    print(*a)


# ───────────────────────────── préparation ─────────────────────────────
def prepare():
    out, _, _ = risque.estime_tous(loo=False)
    for s, t in out.items():
        vp, tk = charge.VALEUR_POINT[s], charge.TICK[s]
        t["Rf"] = t["R_mes"].fillna(t["R"])
        t["m_mae"] = t["mae_pts"] / t["Rf"]
        t["m_mfe"] = t["mfe_pts"] / t["Rf"]
        t["r_brut"] = t["pnl"] / (t["Rf"] * vp)
        # Bug : sur la bougie de remplissage le stop était hors d'atteinte.
        t["bug_sur"] = t["stop"] & ((t["mae_pts"] + t["pts"]) >= 2 * tk)   # stoppé plus tard, P&L inchangé
        n_bug = int(round(FACTEUR_BUG * t["bug_sur"].sum() * (~t["stop"]).sum() / t["stop"].sum()))
        rang = t["m_mae"].where(~t["stop"]).rank(ascending=False, method="first")
        t["bug_est"] = rang <= n_bug                                          # aurait dû être stoppé
        pnl_stop = -(t["Rf"] + tk) * vp - charge.COMMISSION_AR
        t["pnl_c"] = np.where(t["bug_est"], pnl_stop, t["pnl"])
        t["r"] = t["pnl_c"] / (t["Rf"] * vp)
        t["stop_c"] = t["stop"] | t["bug_est"]
        t.loc[t["bug_est"], "m_mfe_c"] = 0.0          # prudent : MFE de bougie 0 non attribuable
        t["m_mfe_c"] = t["m_mfe_c"].fillna(t["m_mfe"])
        t["m_mae_c"] = np.where(t["bug_est"], 1.0 + tk / t["Rf"], t["m_mae"])
        h = t["entree_dt"].dt.hour + t["entree_dt"].dt.minute / 60
        t["seance"] = np.select([h < 8, h < 14.5, h < 22], ["Asie (00-08)", "Londres (08-14h30)", "US (14h30-22)"], "Soir (22-23)")
        t["jour_sem"] = t["entree_dt"].dt.dayofweek.map(dict(enumerate(["lun", "mar", "mer", "jeu", "ven", "sam", "dim"])))
        t["annee"] = t["entree_dt"].dt.year
        t["sem"] = t["annee"].astype(str) + "-S" + ((t["entree_dt"].dt.month > 6) + 1).astype(str)
        t["trim"] = t["entree_dt"].dt.to_period("Q").astype(str)
        t["mois"] = t["entree_dt"].dt.to_period("M")
        t["moitie"] = np.where(t["entree_dt"] < MILIEU, "H1", "H2")
        t["duree"] = pd.cut(t["barres"], [-1, 1, 3, 10, 30, 100, 10_000],
                            labels=["0-1", "2-3", "4-10", "11-30", "31-100", ">100"])
    return out


def stats(t, col="pnl_c", rcol="r"):
    g = t[col][t[col] > 0].sum()
    l = -t[col][t[col] < 0].sum()
    r = t[rcol]
    n = len(t)
    return pd.Series({
        "n": n, "P&L $": round(t[col].sum()), "PF": round(g / l, 2) if l > 0 else np.nan,
        "gagn %": round(100 * (t[col] > 0).mean(), 1), "R moy": round(r.mean(), 3),
        "t": round(r.mean() / r.std(ddof=1) * np.sqrt(n), 2) if n > 2 else np.nan,
        "R tot": round(r.sum(), 1),
    })


def table(t, by, **kw):
    return t.groupby(by, observed=True).apply(lambda x: stats(x, **kw)).astype(object)


def boot_mois(t, fn, B=B):
    """Bootstrap par mois calendaire (bloc = mois) ; renvoie (est, lo95, hi95)."""
    groupes = [g for _, g in t.groupby("mois")]
    k = len(groupes)
    est = fn(t)
    v = np.empty(B)
    for b in range(B):
        idx = RNG.integers(0, k, k)
        v[b] = fn(pd.concat([groupes[i] for i in idx]))
    return est, np.percentile(v, 2.5), np.percentile(v, 97.5), (v <= 0).mean()


def boot_mois_vec(rmat, mois, B=B):
    """Version rapide : rmat (n_trades × n_variantes) ; moyenne par trade, IC par mois."""
    codes, uniq = pd.factorize(mois)
    k = len(uniq)
    S = np.zeros((k, rmat.shape[1]))
    np.add.at(S, codes, rmat)
    N = np.bincount(codes, minlength=k).astype(float)
    W = RNG.multinomial(k, np.ones(k) / k, size=B).astype(float)   # B × k
    means = (W @ S) / (W @ N)[:, None]
    return means


# ───────────────────────────── variantes de sortie ─────────────────────────────
def simule(t, sym, k=1.0, x=np.inf, b=np.inf):
    """Résultat en R (net de commission) d'une variante : (borne prudente, borne optimiste).

    k : stop à k R (k ≤ 1 ; 1 = stop actuel 2 ATR). x : objectif en R. b : break-even
    (stop à entrée + 1 tick) dès que le MFE atteint b R.
    Pour chaque trade on liste les issues COMPATIBLES avec (MFE, MAE, sortie finale) :
      - le MFE d'un trade stoppé s'est produit AVANT le stop (sinon trade déjà fermé) ;
      - un trade non stoppé n'est jamais descendu à −1 R (après correction du bug) ;
      - l'ordre MAE / MFE est inconnu sinon -> plusieurs issues possibles.
    Prudente = la pire issue compatible, optimiste = la meilleure. Stop seul ou
    objectif seul avec le stop actuel : une seule issue possible (exact, au bruit de R près).
    """
    vp, tk = charge.VALEUR_POINT[sym], charge.TICK[sym]
    R = t["Rf"].values
    c = charge.COMMISSION_AR / (R * vp)
    sl = tk / R
    r0 = t["r"].values
    mae = t["m_mae_c"].values
    mfe = t["m_mfe_c"].values
    stopped = t["stop_c"].values
    fin = np.where(t["bug_est"].values, -1.0, t["pts"].values / R)      # sortie finale (R brut)
    pe = np.empty(len(t))
    op = np.empty(len(t))
    for i in range(len(t)):
        stop_v = (-k - sl[i] - c[i]) if k < 1 else r0[i]
        tp_v, be_v = x - c[i], -c[i]
        reach_T, reach_B = mfe[i] >= x, (mfe[i] >= b) and (b < x)
        dip = mae[i] > sl[i]                       # est passé sous l'entrée à un moment
        if stopped[i] or (k < 1 and mae[i] >= k):
            poss = set()
            if k < 1:
                poss.add(stop_v)                   # le stop serré a pu partir en premier
            elif not (reach_T or reach_B):
                poss.add(stop_v)
            if reach_T:
                poss.add(tp_v)
                if reach_B and dip:
                    poss.add(be_v)
            elif reach_B:
                poss.add(be_v)                     # armé puis redescendu jusqu'au stop
            if k >= 1 and stopped[i] and reach_B and not reach_T:
                poss = {be_v}                      # certain : b atteint avant le stop d'origine
        else:
            if reach_T:
                poss = {tp_v, be_v} if (reach_B and dip) else {tp_v}
            elif reach_B:
                if fin[i] <= sl[i]:
                    poss = {be_v}
                elif dip:
                    poss = {be_v, r0[i]}
                else:
                    poss = {r0[i]}
            else:
                poss = {r0[i]}
        pe[i], op[i] = min(poss), max(poss)
    return pe, op


# ───────────────────────────── programme ─────────────────────────────
def main():
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_rows", 200)
    D = prepare()

    P("=" * 100)
    P("0. CONTRÔLES : fuseau horaire, bug de la bougie de remplissage, qualité de R")
    P("=" * 100)
    for s, t in D.items():
        hrs = pd.concat([t["entree_dt"], t["sortie_dt"]]).dt.hour.value_counts().sort_index()
        P(f"{s} heures présentes (entrées+sorties) : {hrs.to_dict()}")
    P("Aucune entrée/sortie à 23 h ; pic à 15h30-16h et 8h-10h -> heure de PARIS (maintenance CME 17-18 h ET = 23-24 h Paris ;\n"
      " en heure de la bourse (CT) on aurait 110 entrées à 16 h CT, marché fermé).")
    for s, t in D.items():
        vp = charge.VALEUR_POINT[s]
        n0 = ((t["barres"] == 0) & t["stop"]).sum()
        P(f"\n{s}: stops sur la bougie de remplissage (barres=0) : {n0} sur {t['stop'].sum()} stops "
          f"(dernier contrat seulement : {t.loc[(t['barres']==0)&t['stop'],'entree_dt'].dt.date.tolist()})")
        P(f"  SÛR  : trades stoppés dont le MAE dépasse la perte (plongée sous le stop prévu sur la bougie 0, "
          f"remontée, stoppés plus tard au bon niveau) : {t['bug_sur'].sum()} -> P&L inchangé")
        for th in (0.8, 1.0, 1.25, 1.5):
            m = (~t["stop"]) & (t["m_mae"] > th)
            gain = t.loc[m, "pnl"].sum()
            corr = (-(t.loc[m, "Rf"] + 0.25) * vp - 2.5).sum()
            P(f"  ESTIMÉ seuil MAE > {th:.2f} R : {m.sum():3d} trades sortis au signal ; leur P&L réel "
              f"{gain:+9.0f} $ -> corrigé {corr:+9.0f} $ (écart {corr-gain:+8.0f} $)")
        # bruit : combien de MAE/R > 1 attendus sans bug, vu l'erreur de R (sd log ≈ 0,24) ?
        sig = t[(~t["stop"])]
        vrai = sig["m_mae"].clip(upper=0.999).values
        sim = np.mean([(vrai * np.exp(RNG.normal(0, 0.24, len(vrai))) > 1).sum() for _ in range(300)])
        P(f"  Sans bug, l'erreur sur R seule donnerait ~{sim:.0f} trades > 1 R (borne haute) : "
          f"excédent ≈ {(sig['m_mae']>1).sum()-sim:.0f} vrais trades touchés.")
        tot = t["pnl"].sum()
        P(f"  => Correctif retenu : {t['bug_sur'].sum()} sûrs × {(~t['stop']).sum()}/{t['stop'].sum()} = {t['bug_est'].sum()} trades "
          f"au plus fort MAE/R (MAE/R ≥ {t.loc[t['bug_est'],'m_mae'].min():.2f}) passés à −1 R ; leur P&L réel "
          f"{t.loc[t['bug_est'],'pnl'].sum():+.0f} $")
        P(f"  P&L brut {tot:+.0f} $ -> corrigé {t['pnl_c'].sum():+.0f} $ ; trades touchés par le bug au total ≈ "
          f"{t['bug_sur'].sum()+t['bug_est'].sum()} ({100*(t['bug_sur'].sum()+t['bug_est'].sum())/len(t):.1f} %)")

    P("\n" + "=" * 100)
    P("1. ROBUSTESSE DANS LE TEMPS (P&L corrigé ; R = 2 ATR estimé)")
    P("=" * 100)
    for s, t in D.items():
        P(f"\n--- {s} --- global brut : {stats(t, 'pnl', 'r_brut').to_dict()}")
        P(f"    global corrigé : {stats(t).to_dict()}")
        P(table(t, "annee").to_string())
        P(table(t, "sem").to_string())
        P(table(t, "trim").to_string())
        P(table(t, "moitie").to_string())

    # prix du marché reconstruit à partir des prix des trades
    P("\n--- Marché (prix reconstitués depuis les entrées/sorties) et phases baissières ---")
    prix = {}
    for s, t in D.items():
        p = pd.concat([pd.Series(t["px_e"].values, t["entree_dt"].values),
                       pd.Series(t["px_s"].values, t["sortie_dt"].values)]).sort_index()
        p = p[~p.index.duplicated()]
        prix[s] = p
        dd = p / p.cummax() - 1
        # phases : creux ≥ 8 % sous le sommet précédent
        phases = []
        sous = dd < 0
        grp = (sous != sous.shift()).cumsum()
        for _, seg in dd[sous].groupby(grp[sous]):
            if seg.min() <= -0.08:
                debut = p.loc[:seg.index[0]].index[-2] if len(p.loc[:seg.index[0]]) > 1 else seg.index[0]
                creux = seg.idxmin()
                phases.append((debut, creux, seg.min()))
        P(f"{s} phases baissières ≥ 8 % : " + "; ".join(f"{a:%Y-%m-%d}→{b:%Y-%m-%d} ({m:.0%})" for a, b, m in phases))
        for a, b_, m in phases:
            sub = t[(t["entree_dt"] >= a) & (t["entree_dt"] <= b_)]
            P(f"   {a:%Y-%m-%d}→{b_:%Y-%m-%d} marché {m:.0%} : " + str(stats(sub).to_dict()))
        for a, b_ in (("2024-07-10", "2024-08-07"), ("2025-02-19", "2025-04-08"), ("2025-10-29", "2026-03-31")):
            sub = t[(t["entree_dt"] >= a) & (t["entree_dt"] <= b_)]
            pa, pb = p[:a].iloc[-1], p[:b_].iloc[-1]
            P(f"   fenêtre fixe {a}→{b_} (marché {pb/pa-1:+.0%}) : n={len(sub)} P&L {sub['pnl_c'].sum():+,.0f} $ "
              f"R {sub['r'].sum():+.1f} ({sub['r'].mean():+.3f} R/trade)")
        mret = p.resample("ME").last().pct_change()
        mret.index = mret.index.to_period("M")
        mo = t.groupby("mois").agg(pnl=("pnl_c", "sum"), r=("r", "sum"), n=("r", "size"))
        mo = mo.join(mret.rename("marche"), how="left").dropna()
        up, dn = mo[mo["marche"] > 0], mo[mo["marche"] <= 0]
        P(f"{s} mois haussiers ({len(up)}) : P&L {up['pnl'].sum():+.0f} $, R {up['r'].sum():+.1f} sur {up['n'].sum()} trades "
          f"({up['r'].sum()/up['n'].sum():+.3f} R/trade) | mois baissiers ({len(dn)}) : P&L {dn['pnl'].sum():+.0f} $, "
          f"R {dn['r'].sum():+.1f} sur {dn['n'].sum()} trades ({dn['r'].sum()/max(dn['n'].sum(),1):+.3f} R/trade)")
        P(f"   corrélation P&L mensuel / rendement mensuel du marché : {mo['pnl'].corr(mo['marche']):+.2f} ; "
          f"mois gagnants {100*(mo['pnl']>0).mean():.0f} %")
        MOIS[s] = mo

    P("\n--- Acheter et garder, dérive haussière ---")
    bh = {"NQ": (242905, 68.35), "ES": (137575, 55.14)}   # feuille Performance du testeur
    for s, t in D.items():
        vp = charge.VALEUR_POINT[s]
        g = np.log(1 + bh[s][1] / 100) / N_BARRES         # dérive log par bougie 15 min
        drift_pts = t["px_e"] * (np.exp(g * t["barres"]) - 1)
        expo = t["barres"].sum() / N_BARRES
        brut_pts = np.where(t["bug_est"], -(t["Rf"] + 0.25), t["pts"])
        exces = (brut_pts - drift_pts) * vp - 2.5
        P(f"{s}: acheter-garder {bh[s][0]:+,} $ (+{bh[s][1]} %) ; stratégie corrigée {t['pnl_c'].sum():+,.0f} $ ; "
          f"temps en position {100*expo:.1f} % des bougies")
        P(f"   dérive attendue par trade (même durée, dérive moyenne) : {drift_pts.mean()*vp:+.1f} $ ; "
          f"total {drift_pts.sum()*vp:+,.0f} $ ; espérance corrigée {t['pnl_c'].mean():+.1f} $/trade")
        P(f"   excédent sur la dérive : {exces.mean():+.1f} $/trade, t = {exces.mean()/exces.std()*np.sqrt(len(t)):.2f} ; "
          f"équivalent acheter-garder au même temps d'exposition : {bh[s][0]*expo:+,.0f} $")
        t["exces"] = exces
        dd = t["pnl_c"].cumsum()
        P(f"   DD max (clôtures de trades) brut {(t['pnl'].cumsum().cummax()-t['pnl'].cumsum()).max():,.0f} $ ; "
          f"corrigé {(dd.cummax()-dd).max():,.0f} $ ; en R {(t['r'].cumsum().cummax()-t['r'].cumsum()).max():.1f} R")
        conc = t["pnl_c"].sort_values(ascending=False)
        P(f"   concentration : 10 meilleurs trades = {conc.head(10).sum():+,.0f} $ ; sans eux {conc.iloc[10:].sum():+,.0f} $ ; "
          f"sans les 20 meilleurs {conc.iloc[20:].sum():+,.0f} $")

    P("\n" + "=" * 100)
    P("2. CONTEXTE (P&L corrigé)")
    P("=" * 100)
    for s, t in D.items():
        P(f"\n--- {s} ---")
        P(table(t, "seance").to_string())
        t["h"] = t["entree_dt"].dt.hour
        P(table(t, "h").to_string())
        P(table(t, "jour_sem").to_string())
        P(table(t, "duree").to_string())
        P(table(t, "stop_c").rename(index={True: "stop", False: "changement couleur"}).to_string())
        for sc, sub in t.groupby("seance"):
            P(f"   {sc} par moitié : " + " | ".join(f"{m}: {stats(x)['R moy']:+.3f} R (n={len(x)})" for m, x in sub.groupby("moitie")))

    P("\n" + "=" * 100)
    P("3. EXCURSIONS ET VARIANTES DE SORTIE (en R ; R = 2 ATR)")
    P("=" * 100)
    for s, t in D.items():
        w = t[t["pnl_c"] > 0]
        P(f"\n--- {s} --- gagnants {len(w)} : MAE/R quantiles 50/75/90/95 % = "
          f"{w['m_mae_c'].quantile([.5,.75,.9,.95]).round(2).tolist()}")
        for k in (0.5, 0.625, 0.75, 0.875):
            P(f"   stop {k:.3f} R ({2*k:.2f} ATR) : garde {100*(w['m_mae_c']<k).mean():.0f} % des gagnants "
              f"({w.loc[w['m_mae_c']>=k,'r'].sum():+.1f} R de gagnants perdus)")
        P(f"   MFE/R tous trades : % atteignant 0,5/1/2/3/5 R = "
          f"{[round(100*(t['m_mfe_c']>=x).mean()) for x in (0.5,1,2,3,5)]}")
        P(f"   gagnants : MFE médian {w['m_mfe_c'].median():.2f} R, sortie médiane {w['r'].median():.2f} R "
          f"(capté {100*(w['r']/w['m_mfe_c']).median():.0f} % du MFE) ; perdants non stoppés : "
          f"{len(t[(t['pnl_c']<=0)&~t['stop_c']])} (moy {t.loc[(t['pnl_c']<=0)&~t['stop_c'],'r'].mean():+.2f} R)")
        P(f"   stoppés ayant d'abord atteint +1 R : {(t['stop_c']&(t['m_mfe_c']>=1)).sum()} / {t['stop_c'].sum()}")

    VARS = ([("actuel", 1.0, np.inf, np.inf)]
            + [(f"stop {k:g} R", k, np.inf, np.inf) for k in (0.875, 0.75, 0.625, 0.5)]
            + [(f"objectif {x:g} R", 1.0, x, np.inf) for x in (1, 1.5, 2, 3, 4, 6, 8, 10, 15)]
            + [(f"BE {b:g} R", 1.0, np.inf, b) for b in (0.5, 1, 1.5, 2, 3, 5)]
            + [(f"objectif {x:g} + BE {b:g}", 1.0, x, b) for x, b in ((2, 1), (3, 1), (4, 2))]
            + [(f"stop {k:g} + objectif {x:g}", k, x, np.inf) for k, x in ((0.75, 2), (0.75, 4), (0.5, 3))])
    lignes = []
    SIM = {}
    for s, t in D.items():
        for nom, k, x, b in VARS:
            pe, op = simule(t, s, k, x, b)
            SIM[(s, nom)] = (pe, op)
            for part, m in [("tout", np.ones(len(t), bool)), ("H1", (t["moitie"] == "H1").values),
                            ("H2", (t["moitie"] == "H2").values)]:
                lignes.append(dict(sym=s, variante=nom, part=part, prudent=pe[m].mean(), optimiste=op[m].mean()))
    V = pd.DataFrame(lignes)
    V.to_csv(OUT + "variantes.csv", index=False)
    P("\nEspérance (R/trade) par variante — prudent | optimiste (identiques quand l'issue est certaine) :")
    pv = V.pivot_table(index="variante", columns=["sym", "part"], values=["prudent", "optimiste"], sort=False)
    out = pd.DataFrame(index=pv.index)
    for sym in ("NQ", "ES"):
        for part in ("tout", "H1", "H2"):
            a_, b_ = pv[("prudent", sym, part)], pv[("optimiste", sym, part)]
            out[f"{sym} {part}"] = [f"{u:+.3f}" if abs(u - v) < 0.0005 else f"{u:+.3f}|{v:+.3f}" for u, v in zip(a_, b_)]
    P(out.to_string())

    P("\n" + "=" * 100)
    P("4/5. BOOTSTRAP PAR MOIS (IC 95 %, 4000 tirages ; p = part des tirages ≤ 0)")
    P("=" * 100)
    for s, t in D.items():
        mo = t["mois"].values
        for lab, col in (("brut (export)", "r_brut"), ("corrigé", "r")):
            m = boot_mois_vec(t[[col]].values, mo)[:, 0]
            P(f"{s} {lab:14s}: R moy {t[col].mean():+.3f}  IC95 [{np.percentile(m,2.5):+.3f} ; {np.percentile(m,97.5):+.3f}]  p(≤0) {np.mean(m<=0):.3f}")
        tot = boot_mois(t, lambda x: x["pnl_c"].sum(), B=2000)
        pf = boot_mois(t, lambda x: x.loc[x.pnl_c > 0, "pnl_c"].sum() / -x.loc[x.pnl_c < 0, "pnl_c"].sum(), B=2000)
        P(f"   P&L total corrigé {tot[0]:+,.0f} $ IC95 [{tot[1]:+,.0f} ; {tot[2]:+,.0f}] ; PF {pf[0]:.2f} IC95 [{pf[1]:.2f} ; {pf[2]:.2f}]")
        ex = boot_mois_vec(t[["exces"]].values, mo)[:, 0]
        P(f"   excédent sur la dérive {t['exces'].mean():+.1f} $/trade IC95 [{np.percentile(ex,2.5):+.1f} ; {np.percentile(ex,97.5):+.1f}]")
        hors = (t["seance"] != "Asie (00-08)").values
        rr = np.column_stack([t["r"].values, np.where(hors, t["r"].values, np.nan)])
        # filtre hors Asie : moyenne par trade retenu
        codes, uniq = pd.factorize(mo)
        k_ = len(uniq)
        Sa = np.zeros(k_); Na = np.zeros(k_); Sh = np.zeros(k_); Nh = np.zeros(k_)
        np.add.at(Sa, codes, t["r"].values); np.add.at(Na, codes, 1)
        np.add.at(Sh, codes, np.where(hors, t["r"].values, 0)); np.add.at(Nh, codes, hors.astype(float))
        W = RNG.multinomial(k_, np.ones(k_) / k_, size=B).astype(float)
        ma, mh = (W @ Sa) / (W @ Na), (W @ Sh) / (W @ Nh)
        P(f"   filtre « pas d'entrée 00-08 h Paris » : {t.loc[hors,'r'].mean():+.3f} R/trade (n={hors.sum()}) "
          f"IC95 [{np.percentile(mh,2.5):+.3f} ; {np.percentile(mh,97.5):+.3f}] ; gain vs actuel "
          f"{np.mean(mh-ma):+.3f} IC95 [{np.percentile(mh-ma,2.5):+.3f} ; {np.percentile(mh-ma,97.5):+.3f}] ; "
          f"P&L {t.loc[hors,'pnl_c'].sum():+,.0f} $")
        base = SIM[(s, "actuel")][0]
        for nom in ("objectif 4 R", "objectif 10 R", "stop 0.75 R", "stop 0.875 R", "BE 2 R", "BE 3 R"):
            pe, op = SIM[(s, nom)]
            dm = boot_mois_vec(np.column_stack([pe - base, op - base]), mo)
            P(f"   {nom:14s}: écart vs actuel prudent {np.mean(pe-base):+.3f} IC95 [{np.percentile(dm[:,0],2.5):+.3f} ; "
              f"{np.percentile(dm[:,0],97.5):+.3f}] | optimiste {np.mean(op-base):+.3f} IC95 [{np.percentile(dm[:,1],2.5):+.3f} ; {np.percentile(dm[:,1],97.5):+.3f}]")

    P("\n--- NQ vs ES ---")
    a_, b_ = D["NQ"], D["ES"]
    mN = a_.groupby("mois")["r"].sum(); mE = b_.groupby("mois")["r"].sum()
    j = pd.concat([mN, mE], axis=1, keys=["NQ", "ES"]).fillna(0)
    P(f"corrélation des R mensuels NQ/ES : {j['NQ'].corr(j['ES']):+.2f} ; mois où les deux gagnent {((j.NQ>0)&(j.ES>0)).mean():.0%}, "
      f"les deux perdent {((j.NQ<0)&(j.ES<0)).mean():.0%}")
    eN = a_["entree_dt"].values; eE = b_["entree_dt"].values
    proche = np.array([np.min(np.abs(eE - x)) <= np.timedelta64(30, "m") for x in eN])
    P(f"entrées NQ avec une entrée ES à ±30 min : {proche.mean():.0%} ({proche.sum()}/{len(eN)})")
    a_["simul_ES"] = proche
    P(f"   R moyen NQ quand ES entre aussi : {a_.loc[proche,'r'].mean():+.3f} (n={proche.sum()}) ; seul : {a_.loc[~proche,'r'].mean():+.3f} (n={(~proche).sum()})")
    D["V"] = V
    D["SIM"] = SIM
    return D


if __name__ == "__main__":
    f = open(OUT + "sortie_etude.txt", "w")

    class T:
        def write(self, x):
            sys.__stdout__.write(x)
            f.write(x)

        def flush(self):
            sys.__stdout__.flush()
    sys.stdout = T()
    D = main()
    import pickle
    pickle.dump({k: v for k, v in D.items() if k not in ("V", "SIM")}, open(OUT + "cache_trades.pkl", "wb"))
