"""Étape 5 : rapprochement des alertes RÉELLES de la Strat5669 (flux manuels MNQ / MES 15 min) avec
les trois lectures simulées du 56 : o (origine, graphique), b (bougie en cours, direct), k (dernière
bougie terminée).

Sources : tous les journaux TradingView_Alerts_Log*.csv de KAIROS-data (lus, jamais recopiés : le
journal contient aussi des messages du bot avec un jeton en clair ; ce script ne garde que les deux
flux manuels et n'écrit aucun texte de message).

    uv run -q --with pandas --with openpyxl python reel.py
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "dataset"))
from releve import charger  # noqa: E402
from simu56 import simuler  # noqa: E402

DATA = os.path.expanduser("~/ERGON/KAIROS-data")
FLUX = {"MNQ": 5884297809, "MES": 5886471945}      # ID des alertes manuelles 15 min (Strat5669)
ENGAGEMENT = pd.Timestamp("2026-10-20")
QUART = pd.Timedelta(minutes=15)


def journal():
    ds = []
    for f in glob.glob(os.path.join(glob.escape(DATA), "**", "TradingView_Alerts_Log*.csv"), recursive=True):
        d = pd.read_csv(f, usecols=["ID de l'alerte", "Heure", "Description"])
        ds.append(d[d["ID de l'alerte"].isin(FLUX.values())])
    L = pd.concat(ds).drop_duplicates(["ID de l'alerte", "Heure", "Description"])
    L["t"] = pd.to_datetime(L["Heure"]).dt.tz_convert("Europe/Paris").dt.tz_localize(None)
    return L.sort_values("t", kind="stable")


def num(txt, motif):
    m = re.search(motif, txt)
    return float(re.sub(r"[,\s  ]", "", m.group(1))) if m else np.nan


def alertes_reelles(L, ins):
    s = L[L["ID de l'alerte"] == FLUX[ins]]
    out, ouvert = [], None
    for a in s.itertuples():
        d = str(a.Description)
        if "au marché maintenant" in d:
            ouvert = dict(ins=ins, alerte=a.t, t1=a.t.floor("15min"), sens="L" if "ACHAT" in d else "S",
                          etiq="GODLIKE" if "GODLIKE" in d else "56 seul", raison=None, pnl=np.nan)
            out.append(ouvert)
        elif ("trade terminé" in d or "FERMER" in d) and ouvert is not None:
            ouvert["raison"] = (("objectif" if "OBJECTIF" in d else "stop") if "trade terminé" in d
                                else ("fin" if "fin de la fenêtre" in d else "temps"))
            ouvert["pnl"] = num(d, r"P&L ≈? ?(-?[\d.,  ]+) \$")
            ouvert = None
    A = pd.DataFrame(out)
    A = A[A.alerte >= ENGAGEMENT]
    return A, s.t.min(), s.t.max()


def main():
    L = journal()
    print(f"Journal : {len(L)} messages des deux flux manuels, du {L.t.min():%d/%m %H:%M} au {L.t.max():%d/%m %H:%M}")
    lignes, bilans = [], []
    for ins in ("MNQ", "MES"):
        A, t0, t9 = alertes_reelles(L, ins)
        R = charger(ins, controle=False)
        Ri = R.set_index("t1")
        fin_releve = R.t1.max()
        print(f"\n{ins} : {len(A)} alertes d'entrée réelles ; flux actif du {t0:%d/%m %H:%M} au {t9:%d/%m %H:%M} ; relevé jusqu'au {fin_releve:%d/%m %H:%M}")
        sims = {}
        for lec in ("o", "b", "k"):
            S = simuler(R, lecture=lec)
            sims[lec] = S[(S.t1 >= t0) & (S.t1 <= fin_releve)].set_index("t1")
        for a in A.itertuples():
            r = dict(ins=ins, t1=a.t1, sens=a.sens, etiq=a.etiq, reel=a.raison or "?", pnl_reel=a.pnl)
            g = Ri.loc[a.t1] if a.t1 in Ri.index else None
            for lec, S in sims.items():
                if a.t1 in S.index and S.loc[a.t1, "sens"] == a.sens:
                    r[lec] = S.loc[a.t1, "raison"]
                    r[f"pnl_{lec}"] = S.loc[a.t1, "pnl"]
                else:
                    r[lec] = "—"
            if g is not None:
                d = 1 if a.sens == "L" else -1
                r["gd_o"], r["gd_b"], r["gd_k"] = (int(g.gd_o == d), int(g.gd_b == d), int(g.gd_k == d))
            lignes.append(r)
        # trades simulés sans alerte, pendant que le flux était actif et après son silence
        for lec, S in sims.items():
            reels = set(zip(A.t1, A.sens))
            sans = S[[(t, s) not in reels for t, s in zip(S.index, S.sens)]]
            actif = sans[sans.index <= t9]
            bilans.append(dict(ins=ins, lecture=lec, simules=len(S[S.index <= t9]), sans_alerte_flux_actif=len(actif),
                               sans_alerte_apres_silence=len(sans) - len(actif),
                               detail_sans=", ".join(f"{t:%d/%m %H:%M} {r.sens} {r.raison}" for t, r in actif.iterrows())))
    T = pd.DataFrame(lignes)
    pd.set_option("display.width", 250)
    print("\nALERTES RÉELLES contre simulations (— = pas de trade simulé à la même bougie dans le même sens)")
    print(T.to_string(index=False))
    print("\nCONCORDANCE")
    n = len(T)
    for lec in ("o", "b", "k"):
        pres = (T[lec] != "—")
        conn = T.reel.isin(["objectif", "stop", "temps", "fin"])
        meme = pres & conn & (T[lec] == T.reel)
        print(f"  lecture {lec} : alerte présente (bougie, sens) {pres.sum()}/{n} ; même sortie {meme.sum()}/{(pres & conn).sum()} parmi les présentes au résultat connu")
    B = pd.DataFrame(bilans)
    print("\nTRADES SIMULÉS SANS ALERTE")
    print(B.drop(columns="detail_sans").to_string(index=False))
    for b in B.itertuples():
        if b.detail_sans:
            print(f"  {b.ins} {b.lecture} : {b.detail_sans}")
    print("\nRÉSULTATS SUR LA PÉRIODE DES ALERTES (flux actif)")
    conn = T[T.reel.isin(["objectif", "stop", "temps", "fin"])]
    vc = conn.reel.value_counts()
    print(f"  réel : {len(T)} alertes, {len(conn)} au résultat connu : {vc.to_dict()} ; objectif/stop = {vc.get('objectif', 0)}/{vc.get('stop', 0)} ;"
          f" gagnants (P&L > 0) {int((conn.pnl_reel > 0).sum())}/{conn.pnl_reel.notna().sum()}")
    T.to_csv(os.path.join(os.path.dirname(__file__), "resultats_etape5.csv"), index=False)
    B.to_csv(os.path.join(os.path.dirname(__file__), "resultats_etape5_sans_alerte.csv"), index=False)
    return T, B, sims


if __name__ == "__main__":
    main()
