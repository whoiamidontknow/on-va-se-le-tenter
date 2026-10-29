"""Graphiques de l'étude du préréglage A (lancer etude.py d'abord : cache_trades.pkl, variantes.csv)."""
import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "/Users/jeremk/ERGON/on-va-se-le-tenter/tools/strategie/testeur_1er_jet/"
COUL = {"NQ": "#2a78d6", "ES": "#eb6834"}
GRIS = "#8a8984"
plt.rcParams.update({"figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.edgecolor": "#c9c8c2",
                     "axes.grid": True, "grid.color": "#e6e5df", "grid.linewidth": 0.6, "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6})

D = pickle.load(open(OUT + "cache_trades.pkl", "rb"))
V = pd.read_csv(OUT + "variantes.csv")

# 1. Courbe des gains (R), drawdown, marché
fig, ax = plt.subplots(3, 1, figsize=(11, 9), sharex=True, gridspec_kw={"height_ratios": [3, 1.4, 2]})
for s, t in D.items():
    cr = t["r"].cumsum()
    ax[0].plot(t["sortie_dt"], cr, color=COUL[s], label=f"{s} corrigé ({t['r'].sum():+.0f} R, {t['pnl_c'].sum():+,.0f} $)")
    ax[0].plot(t["sortie_dt"], t["r_brut"].cumsum(), color=COUL[s], lw=0.8, ls="--", alpha=0.7, label=f"{s} export brut")
    ax[1].fill_between(t["sortie_dt"], cr - cr.cummax(), 0, color=COUL[s], alpha=0.35, lw=0, label=s)
    p = pd.concat([pd.Series(t["px_e"].values, t["entree_dt"].values), pd.Series(t["px_s"].values, t["sortie_dt"].values)]).sort_index()
    ax[2].plot(p.index, 100 * p / p.iloc[0], color=COUL[s], lw=1.0, label=f"{s} (prix des trades, base 100)")
for a, b in [("2024-07-10", "2024-08-08"), ("2024-12-17", "2025-04-08"), ("2025-10-29", "2026-03-31"), ("2026-06-03", "2026-07-30")]:
    for x in ax:
        x.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=GRIS, alpha=0.12, lw=0)
ax[0].set_title("Préréglage A — gains cumulés en R (1 R = 2 ATR) ; zones grises = baisses NQ ≥ 10 %", loc="left")
ax[0].legend(frameon=False, ncol=2)
ax[1].set_ylabel("drawdown (R)")
ax[1].legend(frameon=False)
ax[2].set_ylabel("marché")
ax[2].legend(frameon=False)
fig.tight_layout()
fig.savefig(OUT + "1_courbe_gains.png", dpi=130)

# 2. MAE / MFE en R
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
for a, (s, t) in zip(ax, D.items()):
    w = t["pnl_c"] > 0
    a.scatter(t.loc[~w, "m_mae_c"], t.loc[~w, "m_mfe_c"].clip(lower=0.05), s=10, color=GRIS, alpha=0.6, label="perdants", lw=0)
    a.scatter(t.loc[w, "m_mae_c"], t.loc[w, "m_mfe_c"].clip(lower=0.05), s=12, color=COUL[s], alpha=0.8, label="gagnants", lw=0)
    a.set_yscale("log")
    a.axvline(1, color="#52514e", lw=0.8)
    a.set_xlabel("MAE (R)")
    a.set_title(f"{s} : excursions de chaque trade", loc="left")
    a.legend(frameon=False)
ax[0].set_ylabel("MFE (R, échelle log)")
fig.tight_layout()
fig.savefig(OUT + "2_mae_mfe.png", dpi=130)

# 3. Variantes exactes (stop plus serré, objectif) : espérance par moitié
noms = ["actuel", "stop 0.875 R", "stop 0.75 R", "stop 0.625 R", "stop 0.5 R"] + \
       [f"objectif {x:g} R" for x in (1, 2, 3, 4, 6, 10, 15)]
fig, ax = plt.subplots(figsize=(11, 4.6))
xs = np.arange(len(noms))
for j, s in enumerate(["NQ", "ES"]):
    sub = V[(V.sym == s)].set_index(["variante", "part"])["prudent"]
    ax.bar(xs + (j - 0.5) * 0.36, [sub[(n, "tout")] for n in noms], 0.34, color=COUL[s], label=f"{s} 3 ans")
    for part, mk in (("H1", "v"), ("H2", "^")):
        ax.scatter(xs + (j - 0.5) * 0.36, [sub[(n, part)] for n in noms], marker=mk, s=22, color="#0b0b0b",
                   label=f"{part} (moitié)" if j == 0 else None, zorder=3)
ax.axhline(0, color="#52514e", lw=0.8)
ax.set_xticks(xs, noms, rotation=30, ha="right")
ax.set_ylabel("espérance (R / trade)")
ax.set_title("Variantes simulées à partir des excursions (issues certaines) — rien ne bat la sortie actuelle", loc="left")
ax.legend(frameon=False, ncol=4)
fig.tight_layout()
fig.savefig(OUT + "3_variantes.png", dpi=130)

# 4. Heure d'entrée (Paris)
fig, ax = plt.subplots(figsize=(11, 4))
for j, (s, t) in enumerate(D.items()):
    g = t.groupby(t["entree_dt"].dt.hour)["r"].agg(["mean", "size"]).reindex(range(24))
    ax.bar(np.arange(24) + (j - 0.5) * 0.4, g["mean"].where(g["size"] >= 5), 0.38, color=COUL[s], label=f"{s} (heures avec ≥ 5 trades)")
ax.axhline(0, color="#52514e", lw=0.8)
ax.set_xticks(range(24))
ax.set_xlabel("heure d'entrée (Paris)")
ax.set_ylabel("R moyen / trade")
ax.set_title("Espérance par heure d'entrée", loc="left")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(OUT + "4_heures.png", dpi=130)
print("ok")
