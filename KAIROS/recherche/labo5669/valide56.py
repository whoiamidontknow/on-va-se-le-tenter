"""Validation du simulateur 56 contre les exports Strat5669 (même période, MNQ 15 min).

1. entrées : go56 du relevé contre les entrées du testeur ;
2. conventions de prix : entrée, sortie au temps, objectif, stop, fin ;
3. simulation complète : n'a de sens qu'avec un parcours juste (err16 ≈ 0), ce qui n'est pas le cas
   des exports du 19/11 (bug f_rvOut, voir KAIROS/dataset/releve.py).

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
                      "raison": s["Signal"].map(raison), "pnl": s["P&L net USD"]})
    return x.dropna(subset=["tx"]).reset_index(drop=True)


def main():
    R = charger("MNQ", controle=False)
    Ri = R.set_index("t1")
    opn = ouvertures(R)
    print(f"Relevé MNQ : {len(R)} bougies, préréglage de l'export : {R.attrs['prereglage']}")
    print(f"  go=1 => go56=1 : {int(((R.go_L == 1) & (R.go56_L == 0)).sum() + ((R.go_S == 1) & (R.go56_S == 0)).sum())} exception(s)")
    print(f"  parcours cohérent (|err16| <= 4 ticks) : {(R.err16.abs() <= 4).mean():.1%}")
    for nom, motif in EXPORTS.items():
        T = testeur(glob.glob(motif)[0])
        print(f"\n=== {nom} : {len(T)} trades, {T.t1.min():%d/%m/%Y} → {T.t1.max():%d/%m/%Y}")
        # 1. entrées
        j = T.join(Ri, on="t1", how="left")
        go_ok = np.where(j.sens == "L", j.go56_L, j.go56_S) == 1
        print(f"  1. entrée du testeur = go56 même bougie même sens : {go_ok.sum()}/{len(T)}"
              f" (go du préréglage 83 : {(np.where(j.sens == 'L', j.go_L, j.go_S) == 1).sum()})")
        iv = sorted(zip(T.t1, T.tx))
        per = R[(R.t1 >= T.t1.min()) & (R.t1 <= T.tx.max()) & ((R.go56_L == 1) | (R.go56_S == 1))]
        ent = set(T.t1)
        manq = [t for t in per.t1 if t not in ent and not any(a < t <= b for a, b in iv)]
        print(f"     go56 à plat sans entrée du testeur : {len(manq)} {[str(m) for m in manq[:5]]}")
        # 2. conventions de prix (le relevé est un export du 19/11 : même ajustement des prix si pas de roll)
        d = np.where(j.sens == "L", 1, -1)
        de = ((j.entree - j.o1) / TICK * d)
        print(f"  2. entrée testeur − o1, en ticks dans le sens : {de.value_counts().head(4).to_dict()}")
        fill = j.entree
        m = j.raison == "temps"
        ds = ((j.sortie - j.o17) / TICK * d)[m]
        print(f"     sortie au temps − o17 : {ds.value_counts().head(4).to_dict()} (attendu −1 : glissement)")
        for rs, sgn, k in (("objectif", 1, TPR), ("stop", -1, 1.0)):
            m = j.raison == rs
            vf = ((j.sortie - (fill + d * sgn * k * j.sl)) / TICK)[m]
            vc = ((j.sortie - (j.c + d * sgn * k * j.sl)) / TICK)[m]
            print(f"     {rs} ({m.sum()}) : écart à entrée±{k:g}×sl médiane {vf.abs().median():.2f} tick, "
                  f"<=0,5 tick {(vf.abs() <= 0.5).mean():.0%} | écart à c±{k:g}×sl médiane {vc.abs().median():.2f}, "
                  f"<=0,5 tick {(vc.abs() <= 0.5).mean():.0%}")
        m = j.raison == "fin"
        tf = j.tx[m]
        kn = tf.map(opn)
        dfin = ((j.sortie[m] - kn) / TICK * d[m])
        print(f"     fin ({m.sum()}) : ouverture connue {kn.notna().sum()}, sortie − ouverture : {dfin.value_counts().head(3).to_dict()}")
        # 3. simulation
        S = simuler(R)
        S = S[(S.t1 >= T.t1.min()) & (S.t1 <= T.t1.max())]
        c = T.merge(S, on="t1", how="outer", suffixes=("_t", "_s"), indicator=True)
        idem = (c._merge == "both") & (c.sens_t == c.sens_s) & (c.raison_t == c.raison_s)
        print(f"  3. simulation : {len(S)} trades ; identiques (bougie, sens, type de sortie) : {idem.sum()}/{len(T)}"
              f" = {idem.sum() / len(T):.1%} ; seulement testeur {int((c._merge == 'left_only').sum())},"
              f" seulement simulation {int((c._merge == 'right_only').sum())}")
        print(f"     P&L testeur {T.pnl.sum():,.0f} $ ; simulé {S.pnl.sum():,.0f} $ ({S.pnl.sum() / T.pnl.sum() - 1:+.1%})")
        print(f"     bougies ambiguës (stop et objectif) : {int(S.ambigu.sum())} ; sorties fin approchées : {int(S.approx.sum())}")
        both = c[(c._merge == "both") & (c.sens_t == c.sens_s)]
        print("     type de sortie testeur × simulé :")
        print(pd.crosstab(both.raison_t, both.raison_s).to_string().replace("\n", "\n       "))


if __name__ == "__main__":
    main()
