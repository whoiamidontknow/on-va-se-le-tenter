"""Contrôles de cohérence d'un export DATASET.pine.

Usage :
    ~/venv-quant/bin/python verifier.py <export.csv> [<export2.csv> ...] [--jeu "/Users/jeremk/Jeu 15:10"]

Contrôles :
  1. vrais prix plausibles face au HA (clôture HA = moyenne OHLC vraie, mèches HA englobantes) ;
  2. trous dans le temps (hors week-end et pause quotidienne CME) ;
  3. colonnes vides ou mortes (constantes) — cf. MEMOIRE_PROJET §13 ;
  4. fréquence des événements (pour 1 000 bougies) ;
  5. graphique bien en Heiken Ashi, disponibilité des données multi-unités ;
  6. si un export « Jeu 15:10 » (CompletV2/V3 + original) recouvre la période : comparaison
     des signaux communs (Signator, Climax, Moyenator, clôture HA).

Code de sortie 1 si un contrôle BLOQUANT échoue.
"""
from __future__ import annotations

import csv
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from charger import BITS, charger  # noqa: E402

DOSSIER_JEU = "/Users/jeremk/Jeu 15:10"
CHAUFFE = 300          # bougies ignorées au début (indicateurs en chauffe)

# Cartographie des exports Jeu 15:10 (tools/jeu1510/, MEMOIRE §15), par INDEX de colonne
# (les en-têtes y sont dupliqués) : 0 time, 4 close HA, 5-7 notre Climator, 18-19 Moyenator,
# 22-25 nos flèches Signator (CompletV2 de l'époque), 50-53 flèches originales Vd (sans
# blackout), 34-37 originales Vb (avec blackout), 56-57 Climax original confirmé.
JEU = {
    "close": 4, "ema50": 18, "ema60": 19,
    "sig_long_fort": 22, "sig_short_fort": 23, "sig_long_moyen": 24, "sig_short_moyen": 25,
    "orig_vb": (34, 35, 36, 37), "orig_vd": (50, 51, 52, 53),
    "clx_buy": (5, 6), "clx_sell": (7,), "orig_clx": (56, 57),
}
RACINE_JEU = {"MNQ": "NQZ", "NQ": "NQZ", "MES": "MES", "ES": "MES"}


def _ok(b: bool) -> str:
    return "OK " if b else "!! "


def _tick(df: pd.DataFrame) -> float:
    d = np.diff(np.unique(df["c"].dropna().round(6).to_numpy()))
    d = d[d > 1e-9]
    return float(np.min(d)) if len(d) else 0.25


def controle_prix(df: pd.DataFrame, r: list) -> bool:
    d = df.iloc[CHAUFFE:]
    na_vrai = d[["o", "h", "l", "c"]].isna().any(axis=1).mean()
    ohlc4 = (d.o + d.h + d.l + d.c) / 4
    ecart = (d.ha_c - ohlc4).abs()
    tk = _tick(df)
    p_ok = (ecart <= tk / 2 + 1e-9).mean()
    meche_h = (d.ha_h + 1e-9 < d.h).mean()
    meche_l = (d.ha_l - 1e-9 > d.l).mean()
    incoh = ((d.h + 1e-9 < d[["o", "c"]].max(axis=1)) | (d.l - 1e-9 > d[["o", "c"]].min(axis=1))).mean()
    bon = na_vrai < 0.001 and p_ok > 0.99 and meche_h < 0.001 and meche_l < 0.001 and incoh == 0
    r.append(f"{_ok(bon)}Vrais prix : {na_vrai:.2%} manquants ; clôture HA = OHLC4 vrai à ½ tick près sur "
             f"{p_ok:.2%} des bougies (écart médian {ecart.median():.4f}, max {ecart.max():.4f}) ; "
             f"mèche HA plus courte que la vraie : haut {meche_h:.2%}, bas {meche_l:.2%} ; "
             f"bougies vraies incohérentes {incoh:.2%}")
    if p_ok <= 0.99:
        r.append("    → vrais prix décalés du HA : mauvais ajustement du contrat continu ? (cf. bug V3)")
    return bon


def controle_trous(df: pd.DataFrame, r: list, ut_min: float | None) -> bool:
    dt = df.index.to_series().diff().dt.total_seconds().div(60).iloc[1:]
    if not ut_min:
        ut_min = float(dt.mode().iloc[0])
    trous = dt[dt > ut_min * 1.01]
    t = trous.index
    prec = t - pd.to_timedelta(trous.values, unit="m")
    weekend = (prec.dayofweek >= 4) & (trous.values >= 24 * 60)
    pause = trous.values <= 75            # pause quotidienne CME (1 h) et petites lacunes
    suspects = trous[~weekend & ~pause]
    bon = len(suspects) <= max(5, len(df) // 2000)
    r.append(f"{_ok(bon)}Temps : UT {ut_min:g} min, {len(trous)} interruptions dont {int(weekend.sum())} "
             f"week-ends, {int(pause.sum())} pauses ≤ 75 min, {len(suspects)} trous suspects")
    for tm, m in suspects.sort_values(ascending=False).head(5).items():
        r.append(f"    trou de {m / 60:.1f} h finissant le {tm}")
    return bon


def controle_colonnes(df: pd.DataFrame, r: list) -> bool:
    d = df.iloc[CHAUFFE:]
    num = d.select_dtypes(include=[np.number, bool])
    vides = [c for c in num.columns if num[c].isna().all()]
    mortes = [c for c in num.columns if c not in vides and num[c].nunique(dropna=True) <= 1]
    partiel = {c: num[c].isna().mean() for c in num.columns if 0.05 < num[c].isna().mean() < 1}
    # Colonnes légitimement constantes ou rares sur un export court.
    tolerees = {"graphique_ha", "ok_jour", "ok_macd10"} | {c for c in mortes if c.startswith(("ok_", "py", "cross"))}
    graves = [c for c in vides + mortes if c not in tolerees and not c.startswith(("py", "pm"))]
    bon = not graves
    r.append(f"{_ok(bon)}Colonnes : {len(num.columns)} numériques ; vides {vides or '—'} ; "
             f"constantes {mortes or '—'}")
    if partiel:
        r.append("    partiellement vides (>5 %) : " + ", ".join(f"{k} {v:.0%}" for k, v in sorted(partiel.items())))
    return bon


def controle_signaux(df: pd.DataFrame, r: list) -> bool:
    d = df.iloc[CHAUFFE:]
    n = max(len(d), 1)
    freq = {k: 1000 * d[k].sum() / n for k in BITS["EVT"]}
    zero = [k for k, v in freq.items() if v == 0]
    essentiels = ["sig_long_fort", "sig_short_fort", "hei_flip_haut", "hei_flip_bas",
                  "clx_buy", "tl_cassure_haut", "tl_cassure_bas"]
    bon = not any(k in zero for k in essentiels) or n < 1000
    r.append(f"{_ok(bon)}Événements pour 1 000 bougies : " + ", ".join(f"{k} {v:.1f}" for k, v in freq.items()))
    lf, ls = d.feu_l.astype(float), d.feu_s.astype(float)
    r.append(f"    Feu : voix long moy. {lf.mean():.1f}, short {ls.mean():.1f}, somme max {int((lf + ls).max())} (≤ 29)")
    return bon


def controle_contexte(df: pd.DataFrame, r: list) -> bool:
    ha = bool(df["graphique_ha"].all())
    r.append(f"{_ok(ha)}Graphique Heiken Ashi sur toutes les bougies : {ha}")
    ok_cols = BITS["TF_OK"]
    taux = {c: df[c].mean() for c in ok_cols}
    tous = df[ok_cols].all(axis=1)
    debut = tous.idxmax() if tous.any() else None
    r.append(f"{_ok(tous.mean() > 0.5)}Multi-unités : toutes disponibles sur {tous.mean():.1%} des bougies "
             f"(à partir du {debut}) ; manques : " +
             (", ".join(f"{k} {1 - v:.0%}" for k, v in taux.items() if v < 0.999) or "aucun"))
    return ha


def _fichiers_jeu(df: pd.DataFrame, dossier: str) -> list[str]:
    sym, ut = df.attrs.get("symbole") or "", df.attrs.get("ut") or ""
    racine = sym.rstrip("!").rstrip("0123456789")
    cible = RACINE_JEU.get(racine)
    if not cible or not ut:
        return []
    return sorted(glob.glob(os.path.join(dossier, f"*_{cible}*, {ut}_*.csv")))


def _charger_jeu(f: str) -> pd.DataFrame:
    rows = list(csv.reader(open(f)))[1:]
    t = pd.to_datetime([x[0] for x in rows], utc=True).tz_convert("Europe/Paris")

    def col(i):
        return pd.to_numeric(pd.Series([x[i] if i < len(x) else "" for x in rows]), errors="coerce").to_numpy()
    d = {k: col(v) for k, v in JEU.items() if isinstance(v, int)}
    for k, v in JEU.items():
        if isinstance(v, tuple):
            for j, i in enumerate(v):
                d[f"{k}_{j}"] = col(i)
    out = pd.DataFrame(d, index=t)
    out["_rang"] = np.arange(len(out))
    return out[~out.index.duplicated(keep="last")]


def _cmp(a: pd.Series, b: pd.Series) -> str:
    a, b = a.astype(bool), b.astype(bool)
    return f"{int((a & b).sum())}/{int((a & ~b).sum())}/{int((~a & b).sum())}"


def comparer_jeu(df: pd.DataFrame, r: list, dossier: str) -> None:
    fichiers = _fichiers_jeu(df, dossier) if os.path.isdir(dossier) else []
    if not fichiers:
        r.append(f"-- Comparaison Jeu 15:10 : aucun export recouvrant ({df.attrs.get('symbole')}, UT {df.attrs.get('ut')})")
        return
    for f in fichiers:
        j = _charger_jeu(f)
        j = j[j._rang >= CHAUFFE]
        commun = df.index.intersection(j.index)
        commun = commun[df.index.get_indexer(commun) >= CHAUFFE]
        r.append(f"-- Comparaison avec {os.path.basename(f)} : {len(commun)} bougies communes")
        if len(commun) == 0:
            continue
        a, b = df.loc[commun], j.loc[commun]
        dc = (a.ha_c - b.close)
        r.append(f"   clôture HA : écart médian {dc.median():.3f}, max |écart| {dc.abs().max():.3f} "
                 "(≠ 0 si contrat différent : NQZ2026 ≠ MNQ1! ajusté ; volumes NQ ≠ MNQ)")
        de = (a.ema50 - b.ema50).abs()
        r.append(f"   EMA50 : |écart| médian {de.median():.4f}, max {de.max():.4f}")
        r.append("   signaux (communs / en trop chez nous / manqués), nous vs notre ancien Complet :")
        r.append("     " + ", ".join(f"{k} {_cmp(a[k], b[k].fillna(0) != 0)}" for k in
                                     ("sig_long_fort", "sig_short_fort", "sig_long_moyen", "sig_short_moyen")))
        for ref in ("orig_vd", "orig_vb"):
            r.append(f"   flèches nous vs original {ref[-2:].upper()} (Fort L, Fort S, Moyen L, Moyen S) : " +
                     ", ".join(_cmp(a[k], b[f"{ref}_{i}"].fillna(0) != 0) for i, k in enumerate(
                         ("sig_long_fort", "sig_short_fort", "sig_long_moyen", "sig_short_moyen"))))
        buy_old = (b.clx_buy_0.fillna(0) != 0) | (b.clx_buy_1.fillna(0) != 0)
        r.append(f"   Climax nous vs Climator de l'export : BUY {_cmp(a.clx_buy, buy_old)}, "
                 f"SELL {_cmp(a.clx_sell, b.clx_sell_0.fillna(0) != 0)} ; vs original confirmé : "
                 f"BUY {_cmp(a.clx_buy, b.orig_clx_0.fillna(0) != 0)}, SELL {_cmp(a.clx_sell, b.orig_clx_1.fillna(0) != 0)}")


def verifier(chemin: str, dossier_jeu: str = DOSSIER_JEU) -> bool:
    df = charger(chemin)
    r = [f"=== {df.attrs['fichier']} : {len(df)} bougies, {df.index[0]} → {df.index[-1]} ==="]
    ut = df.attrs.get("ut")
    ut_min = float(ut) if ut and ut.isdigit() else None
    bons = [controle_prix(df, r), controle_trous(df, r, ut_min), controle_colonnes(df, r),
            controle_signaux(df, r), controle_contexte(df, r)]
    comparer_jeu(df, r, dossier_jeu)
    r.append("VERDICT : " + ("exploitable" if all(bons) else "À EXAMINER (lignes marquées !!)"))
    print("\n".join(r))
    return all(bons)


if __name__ == "__main__":
    args = sys.argv[1:]
    dossier = DOSSIER_JEU
    if "--jeu" in args:
        i = args.index("--jeu")
        dossier = args[i + 1]
        args = args[:i] + args[i + 2:]
    if not args:
        print(__doc__)
        sys.exit(1)
    res = [verifier(f, dossier) for f in args]
    sys.exit(0 if all(res) else 1)
