"""25/11 — décision du 56 sur chaque bougie du Relevé complet (15 et 5 min), en lecture o (graphique) et b (alertes).

56 d'origine (RELEVE_COMPLET.pine, préréglage « 56 · d'origine ») :
  déclencheur long = flèche Signator forte ou moyenne, flip Heishinator, cassure de trendline, cassure de niveau,
  climax, divergence (bits sF / sM / hei / tl / lvl / clx / div) ; pas de déclencheur court sur la même bougie ;
  pas de bougie `fin` ; Dashator 1 h > 0 et 4 h > 0 ; écart à l'EMA50 arrondi au dixième ≤ 0,6 (miroir en short :
  corps ≤ 0, écart ≥ −0,6).
Lectures du Dashator : k = dernière bougie 1 h / 4 h terminée (k1, k4) ; b = bougie en cours reconstituée (b1, b4) ;
o = valeur FINALE de la bougie en cours (= b sur la bougie qui clôt l'heure / le 4 h).
Bougies 4 h CME : calées sur l'ouverture de 17:00 Chicago (17, 21, 1, 5, 9, 13 h Chicago).
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/ERGON/on-va-se-le-tenter/KAIROS/dataset"))
from releve_complet import charger  # noqa: E402

DOSSIER = os.path.expanduser("~/ERGON/KAIROS-data/fiable")
DECL = ("sF", "sM", "hei", "tl", "lvl", "clx", "div")


def blocs(B):
    """Identifiant de la bougie 1 h et 4 h qui contient chaque bougie du graphique, et part écoulée à sa clôture."""
    chi = B.t.dt.tz_localize("Europe/Paris", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("America/Chicago")
    u = B.attrs["unite"]
    fin = chi + pd.Timedelta(minutes=u)                     # clôture de la bougie du graphique
    debut_h = chi.dt.floor("h")
    # 4 h : depuis 17:00 Chicago
    m17 = ((chi.dt.hour - 17) % 24) * 60 + chi.dt.minute
    debut_4 = chi - pd.to_timedelta(m17 % 240, unit="m") - pd.to_timedelta(chi.dt.second, unit="s")
    e1 = ((fin - debut_h).dt.total_seconds() / 3600).clip(upper=1)
    e4 = ((fin - debut_4).dt.total_seconds() / 14400).clip(upper=1)
    return debut_h, debut_4, e1.values, e4.values


def charger56(ins, unite):
    return complete56(charger(ins, dossier=os.path.join(DOSSIER, f"{unite}min")))


def complete56(B):
    """Ajoute à un relevé chargé les blocs 1 h / 4 h, o1 / o4 et les décisions du 56 en lectures k, b, o."""
    h, q, B["e1h"], B["e4h"] = blocs(B)
    B["bloc1"], B["bloc4"] = h.values, q.values
    # o = b de la dernière bougie du graphique dans la même bougie 1 h / 4 h
    B["o1"] = B.groupby("bloc1").b1.transform("last")
    B["o4"] = B.groupby("bloc4").b4.transform("last")
    er = np.round(B.e1 * 10) / 10
    L = B[[f"{d}_L" for d in DECL]].values.any(axis=1)
    S = B[[f"{d}_S" for d in DECL]].values.any(axis=1)
    base_L = L & ~S & (B.fin.values == 0) & (er.values <= 0.6)
    base_S = S & ~L & (B.fin.values == 0) & (er.values >= -0.6)
    for lec, c1, c4 in (("k", "k1", "k4"), ("b", "b1", "b4"), ("o", "o1", "o4")):
        B[f"go{lec}_L"] = (base_L & (B[c1] > 0) & (B[c4] > 0)).astype(np.int8)
        B[f"go{lec}_S"] = (base_S & (B[c1] <= 0) & (B[c4] <= 0)).astype(np.int8)
    return B


if __name__ == "__main__":
    for u in (15, 5):
        for ins in ("MNQ", "MES"):
            B = charger56(ins, u)
            print(f"{u} min {ins} : {len(B)} bougies ; bits go L/S {B.go_L.sum()}/{B.go_S.sum()} ;"
                  + " ; ".join(f"go{l} {B[f'go{l}_L'].sum()}/{B[f'go{l}_S'].sum()} (= bits {((B[f'go{l}_L'] == B.go_L) & (B[f'go{l}_S'] == B.go_S)).mean():.4f})" for l in "kbo"))
