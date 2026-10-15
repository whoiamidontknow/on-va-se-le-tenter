"""Estimation de 1 R (distance du stop = 2 ATR14 vrais prix) pour chaque trade.

L'export ne donne ni l'ATR ni le stop. Mais un trade sorti par « Stop L » au
niveau prévu perd exactement 2 ATR + 1 tick de glissement (perte = MAE à 1 tick
près). On s'en sert comme MESURE DIRECTE de l'ATR et on l'interpole pour les
autres trades, en volatilité relative (R / prix d'entrée) :
  log(R/prix) = niveau local dans le temps (noyau gaussien en jours, NQ et ES
                mis en commun avec un écart propre au symbole)
              + effet de l'heure d'entrée (heure de Paris).
Validation « en laissant le trade de côté » sur les mesures directes :
`python risque.py` affiche l'écart-type de l'erreur (log).
"""
import numpy as np
import pandas as pd

import charge

SIGMA_J = 1.5   # largeur du noyau temporel (jours), choisie par validation


def mesures_directes(d, sym):
    """Trades stoppés proprement : perte = 1 R + 1 tick, MAE = perte (±1 tick)."""
    tick = charge.TICK[sym]
    st = d[d["stop"]]
    propre = (st["mae_pts"] + st["pts"]) < tick / 2
    st = st[propre]
    return (-st["pts"] - tick).rename("R_mes")


def _table(sym):
    d = charge.charge(sym)
    rm = mesures_directes(d, sym)
    d["R_mes"] = rm
    d["h"] = d["entree_dt"].dt.hour
    d["jour"] = (d["entree_dt"] - pd.Timestamp("2023-10-01")).dt.total_seconds() / 86400
    d["lv"] = np.log(d["R_mes"] / d["px_e"])
    return d


def estime_tous(loo=False):
    """Renvoie {sym: DataFrame avec colonne R (points)}."""
    tabs = {s: _table(s) for s in ["NQ", "ES"]}
    allm = pd.concat([t.assign(sym=s) for s, t in tabs.items()])
    m = allm.dropna(subset=["lv"]).reset_index()
    off_sym = pd.Series(0.0, index=["NQ", "ES"])
    eff_h = pd.Series(0.0, index=range(24))
    J = m["jour"].values
    for _ in range(4):
        y = m["lv"].values - m["sym"].map(off_sym).values - m["h"].map(eff_h).fillna(0).values
        W = np.exp(-0.5 * ((J[:, None] - J[None, :]) / SIGMA_J) ** 2)
        loc = (W @ y) / W.sum(1)
        r = m["lv"].values - loc
        off_sym = pd.Series(r).groupby(m["sym"].values).mean()
        off_sym -= off_sym.mean()
        r2 = r - m["sym"].map(off_sym).values
        eh = pd.Series(r2).groupby(m["h"].values).agg(["mean", "count"])
        # rétrécissement vers 0 pour les heures rares
        eff_h = (eh["mean"] * eh["count"] / (eh["count"] + 10)).reindex(range(24)).fillna(0)
    y = m["lv"].values - m["sym"].map(off_sym).values - m["h"].map(eff_h).values
    out = {}
    for s, t in tabs.items():
        Jt = t["jour"].values
        W = np.exp(-0.5 * ((Jt[:, None] - J[None, :]) / SIGMA_J) ** 2)
        if loo:
            same = (m["sym"].to_numpy(dtype=object)[None, :] == s) & (m["n"].values[None, :] == t.index.values[:, None])
            W = np.where(same, 0.0, W)
        loc = (W @ y) / W.sum(1)
        lv = loc + off_sym[s] + t["h"].map(eff_h).values
        t["R"] = np.exp(lv) * t["px_e"]
        out[s] = t
    return out, off_sym, eff_h


if __name__ == "__main__":
    for sg in [0.5, 1.5, 3, 10]:
        SIGMA_J = sg
        out, off, eh = estime_tous(loo=True)
        msg = []
        for s, t in out.items():
            ok = t["R_mes"].notna()
            e = np.log(t.loc[ok, "R"] / t.loc[ok, "R_mes"])
            msg.append(f"{s}: biais {e.mean():+.3f} sd {e.std():.3f} q10/q90 {e.quantile(.1):+.2f}/{e.quantile(.9):+.2f}")
        print(f"sigma {sg} j :", " | ".join(msg))
    print("écart NQ/ES (log)", off.round(3).to_dict())
    print("effet heure", eh.round(2).to_dict())
