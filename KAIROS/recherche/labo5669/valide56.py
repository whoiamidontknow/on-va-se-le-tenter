"""Validation du simulateur 56 contre les exports Strat5669 (même période, MNQ 15 min).

1. entrées : go56 du relevé contre les entrées du testeur ;
2. conventions de prix (vérifiées le 19/11 sur 6ef10, voir simu56.py) ;
3. simulation complète, en lecture d'origine (o) ou direct (b), contre les exports 56, 74, SANSFUITE.

    uv run -q --with pandas --with openpyxl python valide56.py
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "dataset"))
from releve import charger, TICK  # noqa: E402
from simu56 import simuler, ouvertures, TPR  # noqa: E402

DATA = os.path.expanduser("~/ERGON/KAIROS-data")
EXPORTS = {"6ef10 (Strat5669 du 12/11, préréglage 56)": f"{DATA}/Jeu12novfable/*MNQ1!_2026-11-12_6ef10.xlsx",
           "39d22 (Strat5669+ du 17/11, préréglage 74)": f"{DATA}/74-75/*MNQ1!_2026-11-17_39d22.xlsx"}
# (instrument, nom, motif, lecture) : o = Dashator d'origine (graphique), b = bougie en cours (direct)
CAS = [("MNQ", "6ef10 Strat5669 12/11, 56", f"{DATA}/Jeu12novfable/*MNQ1!_2026-11-12_6ef10.xlsx", "o"),
       ("MNQ", "39d22 Strat5669+ 17/11, 74", f"{DATA}/74-75/*MNQ1!_2026-11-17_39d22.xlsx", "o"),
       ("MNQ", "ca427 SANSFUITE ancien calcul (témoin)", f"{DATA}/SansFuite/*MNQ1!_2026-11-15_ca427.xlsx", "o"),
       ("MNQ", "aedc3 SANSFUITE mode b (direct)", f"{DATA}/SansFuite/*MNQ1!_2026-11-15_aedc3.xlsx", "b"),
       ("MES", "f47fe Strat5669 12/11, 56", f"{DATA}/Jeu12novfable/*MES1!_2026-11-12_f47fe.xlsx", "o"),
       ("MES", "a52ff SANSFUITE ancien calcul (témoin)", f"{DATA}/SansFuite/*MES1!_2026-11-15_a52ff.xlsx", "o"),
       ("MES", "886b4 SANSFUITE mode b (direct)", f"{DATA}/SansFuite/*MES1!_2026-11-15_886b4.xlsx", "b")]


def raison(sig):
    s = str(sig)
    return ("objectif" if s.startswith("Obj") else "stop" if s.startswith("Stop") else "temps" if s.startswith("Temps")
            else "fin" if s.startswith("Fin") else "retournement" if s.startswith("Retour") else s)


def testeur(f):
    t = pd.read_excel(f, sheet_name="Trades")
    t["Date et heure"] = pd.to_datetime(t["Date et heure"], errors="coerce")
    e = t[t.Type.str.startswith("Entrer")].set_index("Numéro de trade")
    s = t[t.Type.str.startswith("Sortir")].set_index("Numéro de trade")
    x = pd.DataFrame({"t1": e["Date et heure"], "sens": np.where(e.Type.str.contains("long"), "L", "S"),
                      "entree": e["Prix USD"], "tx": s["Date et heure"], "sortie": s["Prix USD"],
                      "raison": s["Signal"].map(raison), "pnl": s["P&L net USD"],
                      "gd": e["Signal"].astype(str).str.contains("GODLIKE")})
    return x.dropna(subset=["tx"]).reset_index(drop=True)


def valider(R, T, nom, lecture):
    """Compare la simulation (lecture o / b) à un export du testeur sur sa période. Rend une ligne de bilan."""
    gl, gs = ("go56_L", "go56_S") if lecture == "o" else ("go56b_L", "go56b_S")
    Ri = R.set_index("t1")
    j = T.join(Ri, on="t1", how="left")
    go_ok = int((np.where(j.sens == "L", j[gl], j[gs]) == 1).sum())
    iv = sorted(zip(T.t1, T.tx))
    per = R[(R.t1 >= T.t1.min()) & (R.t1 <= T.tx.max()) & ((R[gl] == 1) | (R[gs] == 1))]
    ent = set(T.t1)
    manq = [t for t in per.t1 if t not in ent and not any(a < t <= b for a, b in iv)]
    S = simuler(R, lecture=lecture)
    S = S[(S.t1 >= T.t1.min()) & (S.t1 <= T.t1.max())]
    c = T.merge(S, on="t1", how="outer", suffixes=("_t", "_s"), indicator=True)
    idem = (c._merge == "both") & (c.sens_t == c.sens_s) & (c.raison_t == c.raison_s)
    gcol = "gd_o" if lecture == "o" else "gd_b"
    Sg = S.join(Ri[[gcol]], on="t1")
    sg = Sg[np.where(Sg.sens == "L", 1, -1) == Sg[gcol]]
    tg = T[T.gd]
    b = dict(cas=nom, lecture=lecture, trades_t=len(T), trades_s=len(S), entrees_go=go_ok, go_manques=len(manq),
             identiques=int(idem.sum()), pct=idem.sum() / len(T), seul_t=int((c._merge == "left_only").sum()),
             seul_s=int((c._merge == "right_only").sum()), pnl_t=T.pnl.sum(), pnl_s=S.pnl.sum(),
             ecart_pnl=S.pnl.sum() / T.pnl.sum() - 1, ambigues=int(S.ambigu.sum()), fin_approx=int(S.approx.sum()),
             gd_t=len(tg), gd_s=len(sg), pnl_gd_t=tg.pnl.sum(), pnl_gd_s=sg.pnl.sum())
    print(f"\n=== {nom} [{R.attrs['instrument']}, lecture {lecture}] : {len(T)} trades, {T.t1.min():%d/%m/%Y} → {T.t1.max():%d/%m/%Y}")
    print(f"  entrées = go même bougie même sens : {go_ok}/{len(T)} ; go à plat sans entrée : {len(manq)} {[str(m) for m in manq[:3]]}")
    print(f"  identiques (bougie, sens, sortie) : {b['identiques']}/{len(T)} = {b['pct']:.1%} ; seulement testeur {b['seul_t']}, seulement simulation {b['seul_s']}")
    print(f"  P&L testeur {b['pnl_t']:,.0f} $ ; simulé {b['pnl_s']:,.0f} $ ({b['ecart_pnl']:+.1%}) ; ambiguës {b['ambigues']} ; fin approchées {b['fin_approx']}")
    print(f"  GODLIKE : testeur {len(tg)} trades {tg.pnl.sum():,.0f} $ ; simulé {len(sg)} trades {sg.pnl.sum():,.0f} $")
    both = c[(c._merge == "both") & (c.sens_t == c.sens_s)]
    x = pd.crosstab(both.raison_t, both.raison_s)
    if (x.values.sum() - np.trace(x.reindex(index=x.columns, fill_value=0).values)) > 0:
        print("  type de sortie testeur × simulé :\n    " + x.to_string().replace("\n", "\n    "))
    return b


def main():
    charges = {}
    bilans = []
    for ins, nom, motif, lec in CAS:
        if ins not in charges:
            charges[ins] = charger(ins, controle=False)
            R = charges[ins]
            print(f"Relevé {ins} : {len(R)} bougies ; parcours cohérent (|err16| <= 4 ticks) {(R.err16.abs() <= 4).mean():.1%}")
        fs = glob.glob(motif)
        if not fs:
            print(f"(absent : {motif})")
            continue
        bilans.append(valider(charges[ins], testeur(fs[0]), nom, lec))
    B = pd.DataFrame(bilans)
    print("\n" + B[["cas", "lecture", "trades_t", "identiques", "pct", "pnl_t", "pnl_s", "ecart_pnl", "ambigues"]].to_string(index=False))
    return B


if __name__ == "__main__":
    main()
