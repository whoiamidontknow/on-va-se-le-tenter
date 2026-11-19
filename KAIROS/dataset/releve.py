"""Chargeur des exports « Relevé 5669 » (KAIROS/dataset/RELEVE_5669.pine).

Une table par instrument, Long et Short fusionnés : une ligne par bougie qui a un
déclencheur dans au moins un sens. Format des commentaires : DATASET_5669.md.

    from releve import charger
    t = charger("MNQ")            # dossier par défaut : ~/ERGON/KAIROS-data/dataset5669

Colonnes :
  t1        ouverture de la bougie 1 (bougie de remplissage), heure de l'export
  t17       ouverture de la bougie 17 (sortie du relevé)
  o1        ouverture de la bougie 1 = prix d'entrée du testeur (vrai prix)
  o17       ouverture de la bougie 17 = prix de sortie du testeur
  d_L d_S go_L go_S x2_L x2_S cf_L cf_S   clés qui dépendent du sens (NaN = pas de déclencheur)
  go56_L go56_S   décision du 56 recalculée : déclencheur dans le sens, aucun en sens opposé, x2 = 1,
            com = 1 (les autres filtres sont neutres en 56). `go` vaut celle du préréglage de l'export
            (les exports du 19/11 sont en 83 = 56 + confiance >= 5 %, voir la propriété « Préréglage »)
  c atr sl er o1h o4h b1h b4h k1h k4h gd_o gd_b gd_k el1 el4 fin pf hr bo com adx vr
            clés communes (o1/o4 du commentaire renommées o1h/o4h pour ne pas heurter le prix o1)
  h1..h16 l1..l16   haut / bas de chaque bougie en ticks entiers, relatifs à o1
  c16       clôture de la bougie 16 en ticks relatifs à o1
  f         1re bougie (1-16) où fin = 1, 0 = aucune
  parcours  True si h/l sont tous connus (les premières bougies de l'historique ont des NaN)
  err16     (o17 - o1) / tick - c16 : clôture de la bougie 16 contre ouverture de la 17, en ticks.
            Doit valoir 0 à quelques ticks près ; sinon le parcours ne se rapporte pas à ce trade.

ATTENTION : dans les PREMIERS exports du 19/11 (dataset5669/ancien-bug), le parcours est faux pour ~90 % des trades. Dans
RELEVE_5669.pine (commit 04c6f6a), f_rvOut() n'est appelée que sous `if rv_ok[rv_n]` : ses
références r_h[j], r_l[j], r_o[rv_n - 1] et fin_apres[j] lisent alors les APPELS précédents, pas
les bougies précédentes. Seules h16 / l16 / c16 sont des valeurs de la bonne bougie, mais
relatives à une mauvaise référence. Corrigé dans le Relevé a7d2173 (figé en 56, sans propriété
« Préréglage ») : |err16| <= 4 ticks pour 97 % (MNQ) et 99 % (MES), le reste surtout aux trous de séance.
"""
import glob
import os
import re

import numpy as np
import pandas as pd

DOSSIER = os.path.expanduser("~/ERGON/KAIROS-data/dataset5669")
TICK = 0.25
VAL_POINT = {"MNQ": 2.0, "MES": 5.0}
SENS_CLES = ("d", "go", "x2", "cf")
COMMUNES = ("c", "atr", "sl", "er", "o1h", "o4h", "b1h", "b4h", "k1h", "k4h", "gd_o", "gd_b", "gd_k",
            "el1", "el4", "fin", "pf", "hr", "bo", "com", "adx", "vr")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def _entree(s):
    kv = dict(p.split("=", 1) for p in str(s).split("|") if "=" in p)
    r = {"d": kv.get("d", "")}
    for k in ("go", "x2", "c", "atr", "sl", "er", "cf", "adx", "vr"):
        r[k] = _num(kv.get(k))
    for k, n in (("o1", "o1h"), ("o4", "o4h"), ("b1", "b1h"), ("b4", "b4h"), ("k1", "k1h"), ("k4", "k4h")):
        r[n] = _num(kv.get(k))
    g = (kv.get("gd", "") + ",,").split(",")
    r["gd_o"], r["gd_b"], r["gd_k"] = (_num(x) for x in g[:3])
    e = (kv.get("el", "") + ",").split(",")
    r["el1"], r["el4"] = _num(e[0]), _num(e[1])
    f = kv.get("f", "")
    for i, k in enumerate(("fin", "pf", "hr", "bo", "com")):
        r[k] = _num(f[i]) if len(f) > i else np.nan
    return r


def _sortie(s):
    kv = dict(p.split("=", 1) for p in str(s).split("|") if "=" in p)
    h = [_num(x) for x in kv.get("h", "").split(",")]
    l = [_num(x) for x in kv.get("l", "").split(",")]
    if len(h) != 16 or len(l) != 16 or "n" not in kv:
        return None                       # commentaire coupé ou trade encore ouvert
    r = {f"h{i + 1}": h[i] for i in range(16)}
    r.update({f"l{i + 1}": l[i] for i in range(16)})
    r["c16"], r["f"] = _num(kv.get("c")), _num(kv.get("f"))
    return r


def lire_fichier(f):
    """Un export Relevé -> (sens 'L'/'S', symbole, DataFrame une ligne par trade fermé)."""
    p = pd.read_excel(f, sheet_name="Propriétés", header=None)
    prop = dict(zip(p[0].astype(str), p[1].astype(str)))
    sens = "L" if prop.get("Sens du relevé", "").startswith("Long") else "S"
    t = pd.read_excel(f, sheet_name="Trades")
    t["Date et heure"] = pd.to_datetime(t["Date et heure"], errors="coerce")   # « Ouverture » = trade encore ouvert
    ent = t[t["Type"].str.startswith("Entrer")].set_index("Numéro de trade")
    sor = t[t["Type"].str.startswith("Sortir")].set_index("Numéro de trade")
    lignes = []
    for n, e in ent.iterrows():
        if n not in sor.index:
            continue
        s = sor.loc[n]
        if pd.isna(s["Date et heure"]):
            continue
        rs = _sortie(s["Signal"])
        if rs is None:
            continue
        r = {"t1": e["Date et heure"], "t17": s["Date et heure"],
             "o1": float(e["Prix USD"]), "o17": float(s["Prix USD"])}
        r.update(_entree(e["Signal"]))
        r.update(rs)
        lignes.append(r)
    return sens, prop.get("Symbole", ""), pd.DataFrame(lignes)


def charger(instrument, dossier=DOSSIER, controle=True):
    fs = [f for f in glob.glob(os.path.join(dossier, "*.xlsx")) if f"_{instrument}1!_" in f]
    par_sens = {}
    for f in fs:
        sens, _, d = lire_fichier(f)
        if sens in par_sens:
            raise ValueError(f"deux exports {instrument} {sens} : {fs}")
        par_sens[sens] = d
    if set(par_sens) != {"L", "S"}:
        raise ValueError(f"{instrument} : il faut un export Long et un Short, trouvé {sorted(par_sens)}")
    parc = [f"h{i}" for i in range(1, 17)] + [f"l{i}" for i in range(1, 17)] + ["c16", "f"]
    base = ["t1", "t17", "o1", "o17"] + list(COMMUNES) + parc
    L, S = par_sens["L"], par_sens["S"]
    if controle:
        m = L[base].merge(S[base], on="t1", suffixes=("", "_s"))
        ecarts = {}
        for k in [k for k in base[1:] if k not in parc]:   # le parcours, lui, diffère (bug f_rvOut)
            a, b = m[k], m[k + "_s"]
            n = int(((a != b) & ~(a.isna() & b.isna())).sum())
            if n:
                ecarts[k] = n
        if ecarts:
            print(f"[releve] {instrument} : valeurs communes différentes entre Long et Short sur {len(m)} bougies : {ecarts}")
    lr = L.rename(columns={k: f"{k}_L" for k in SENS_CLES})
    sr = S.rename(columns={k: f"{k}_S" for k in SENS_CLES})
    t = pd.concat(sort=True, objs=[lr[base + [f"{k}_L" for k in SENS_CLES]].set_index("t1"),
                   sr[base + [f"{k}_S" for k in SENS_CLES]].set_index("t1")], axis=1)
    # les colonnes communes existent deux fois : on garde la première non vide
    t = _fusion(t)
    t = t.reset_index().rename(columns={"index": "t1"}).sort_values("t1").reset_index(drop=True)
    for k in ("go_L", "go_S"):
        t[k] = t[k].fillna(0).astype(int)
    for s_, o_ in (("L", "S"), ("S", "L")):
        t[f"go56_{s_}"] = (t[f"d_{s_}"].notna() & t[f"d_{o_}"].isna() & (t[f"x2_{s_}"] == 1) & (t.com == 1)).astype(int)
    t["err16"] = (t.o17 - t.o1) / TICK - t.c16
    t["parcours"] = t[[f"h{i}" for i in range(1, 17)] + [f"l{i}" for i in range(1, 17)]].notna().all(axis=1)
    pr = prop_communes(fs)
    t.attrs["prereglage"] = pr
    e = t.err16.abs()
    if (e <= 4).mean() < 0.9:
        print(f"[releve] {instrument} : parcours INCOHÉRENT, |c16 + o1 - o17| <= 4 ticks pour seulement "
              f"{(e <= 4).mean():.0%} des trades (bug f_rvOut, voir l'en-tête)")
    t.attrs["instrument"] = instrument
    t.attrs["val_point"] = VAL_POINT[instrument]
    return t


def prop_communes(fs):
    v = set()
    for f in fs:
        p = pd.read_excel(f, sheet_name="Propriétés", header=None)
        v.add(dict(zip(p[0].astype(str), p[1].astype(str))).get("Préréglage", "?"))
    return " / ".join(sorted(v))


def _fusion(t):
    out = pd.DataFrame(index=t.index)
    for k in dict.fromkeys(t.columns):
        c = t.loc[:, t.columns == k]
        out[k] = c.iloc[:, 0] if c.shape[1] == 1 else c.iloc[:, 0].combine_first(c.iloc[:, 1])
    return out


if __name__ == "__main__":
    import sys
    for ins in sys.argv[1:] or ("MNQ", "MES"):
        t = charger(ins)
        print(ins, len(t), "bougies", t.t1.min(), "→", t.t1.max(),
              "| préréglage", t.attrs["prereglage"], "| go", int(t.go_L.sum()), int(t.go_S.sum()),
              "| go56", int(t.go56_L.sum()), int(t.go56_S.sum()), "| parcours complet", int(t.parcours.sum()))
