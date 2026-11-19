"""Chargeur du « Relevé complet » (KAIROS/dataset/RELEVE_COMPLET.pine, format DATASET_COMPLET.md).

Une table par instrument, une ligne par bougie (toutes les bougies), champs décodés, bits en colonnes.

    from releve_complet import charger
    B = charger("MNQ")           # dossier par défaut : ~/ERGON/KAIROS-data/releve_complet (sans test/)

Colonnes : t (ouverture de la bougie, heure de Paris, naïve), bloc, dt, o h l c (vrais prix),
bits b01..b35 sous des noms parlants (BITS), clx adx di sgs feu str dirC dirM dirH atr e1 e2 k1 k4 b1 b4
biF biI pW pM pA fib detU detD vr. Le dernier bloc (ouvert, sans commentaire de sortie) est absent.
"""
import glob
import os

import numpy as np
import pandas as pd

DOSSIER = os.path.expanduser("~/ERGON/KAIROS-data/releve_complet")
TICK = 0.25
VAL_POINT = {"MNQ": 2.0, "MES": 5.0}
CHAMPS = ["dt", "o", "h", "l", "c", "bits", "clx", "adx", "di", "sgs", "feu", "str", "dirC", "dirM", "dirH", "atr",
          "e1", "e2", "k1", "k4", "b1", "b4", "biF", "biI", "pW", "pM", "pA", "fib", "detU", "detD", "vr"]
BITS = ["ha_up", "hei_L", "hei_S", "sF_L", "sF_S", "sM_L", "sM_S", "tl_L", "tl_S", "lvl_L", "lvl_S", "clx_L", "clx_S",
        "div_L", "div_S", "det_bloque_L", "det_bloque_S", "blackout",
        "tr3m", "tr5m", "tr15m", "tr1h", "tr4h", "tr1d", "da1m", "da5m", "da15m", "da1h", "da4h", "da1d",
        "macd10", "fin", "go_L", "go_S", "fib_bas"]


def _blocs(f):
    x = pd.read_excel(f, sheet_name="Trades")
    s = x.loc[x["Type"].str.startswith("Sortir"), "Signal"].astype(str)
    lignes, coupes = [], 0
    for nb, com in enumerate(s):
        if not com.startswith("t="):
            continue
        parts = com.split("|")
        kv = {p.split("=", 1)[0]: p.split("=", 1)[1] for p in parts if p[:2] in ("t=", "r=", "n=")}
        if "n" not in kv:
            coupes += 1
            continue
        fiches = parts[2].split(";")
        if len(fiches) != int(kv["n"]):
            coupes += 1
            continue
        t0, r = int(kv["t"]), float(kv["r"])
        for i, fi in enumerate(fiches):
            v = fi.split(",")
            lignes.append([t0, r, nb, i] + v)
    return lignes, coupes


def charger(instrument, dossier=DOSSIER):
    fs = [f for f in glob.glob(os.path.join(dossier, "*.xlsx")) if f"_{instrument}1!_" in f]
    if len(fs) != 1:
        raise ValueError(f"{instrument} : un export attendu dans {dossier}, trouvé {fs}")
    lignes, coupes = _blocs(fs[0])
    D = pd.DataFrame(lignes, columns=["t0", "r", "bloc", "i"] + CHAMPS)
    for c in CHAMPS:
        if c != "bits":
            D[c] = pd.to_numeric(D[c], errors="coerce")
    # horodatage : t0 = 1re bougie du bloc, puis dt bougies de 15 min à chaque fiche
    D = D.sort_values(["t0", "i"]).reset_index(drop=True)
    pas = D.groupby("bloc").dt.cumsum() - D.dt.where(D.i == 0, 0).groupby(D.bloc).transform("first")
    D["t"] = (pd.to_datetime(D.t0, unit="s") + pd.to_timedelta(pas * 15, unit="m")).dt.tz_localize("UTC") \
        .dt.tz_convert("Europe/Paris").dt.tz_localize(None)
    for c in ("o", "h", "l", "c"):
        D[c] = D.r + D[c] * TICK
    lon = D.bits.astype(str).str.len()
    if (lon != 35).any():
        raise ValueError(f"{instrument} : {int((lon != 35).sum())} fiches sans 35 bits")
    bits = np.array(D.bits.astype(str).tolist(), dtype="U35").view("U1").reshape(-1, 35) == "1"
    for j, nom in enumerate(BITS):
        D[nom] = bits[:, j].astype(np.int8)
    D = D.drop(columns=["bits", "t0", "i"]).sort_values("t").reset_index(drop=True)
    D.attrs.update(instrument=instrument, val_point=VAL_POINT[instrument], coupes=coupes, fichier=os.path.basename(fs[0]))
    return D


if __name__ == "__main__":
    import sys
    for ins in sys.argv[1:] or ("MNQ", "MES"):
        B = charger(ins)
        print(f"{ins} : {len(B)} bougies, {B.bloc.nunique()} blocs, commentaires coupés {B.attrs['coupes']}, "
              f"{B.t.min():%d/%m/%Y %H:%M} → {B.t.max():%d/%m/%Y %H:%M} ; horodatages en double {int(B.t.duplicated().sum())} ;"
              f" go_L {int(B.go_L.sum())} go_S {int(B.go_S.sum())}")
