"""Chargement d'un export CSV de DATASET.pine (« Dataset Strat-Botting »).

Usage :
    from charger import charger
    df = charger("~/Ephore/Strat-Botting-data/CME_MINI_MNQ1!, 15_ab12c.csv")

    ~/venv-quant/bin/python charger.py <fichier.csv>     # résumé en ligne de commande

Renvoie un DataFrame indexé par l'heure de Paris (tz-aware, Europe/Paris), une ligne par
bougie, avec les colonnes décrites dans COLONNES ci-dessous (le détail des sources est dans
INVENTAIRE.md). Les colonnes brutes empaquetées (EVT, ETAT, …) sont décodées puis retirées
(garder_brut=True pour les conserver).

Attributs posés sur df.attrs : symbole, ut (unité en minutes, texte TradingView), fichier.
"""
from __future__ import annotations

import os
import re
import sys

import numpy as np
import pandas as pd

# ─── En-têtes des plots de DATASET.pine (NE PAS changer sans changer le Pine) ───
PLOTS = [
    "RO", "RH", "RL", "RC", "RV", "RATR",
    "EMA50", "EMA60", "ADX", "DIP", "DIM", "RSI", "CCI", "SCORE",
    "FEU_L", "FEU_S", "TL_RES", "TL_SUP",
    "ZH_SUP_H", "ZH_SUP_B", "ZH_INF_H", "ZH_INF_B",
    "ZB_SUP_H", "ZB_SUP_B", "ZB_INF_H", "ZB_INF_B",
    "ORB_H", "ORB_L", "AS_H", "AS_L", "LD_H", "LD_L", "US_H", "US_L", "MON_H", "MON_L",
    "PW_H", "PW_L", "PW_C", "PM_H", "PM_L", "PM_C", "PY_H", "PY_L", "PY_C",
    "PWR_H", "PWR_L", "PWR_C", "PMR_H", "PMR_L", "PMR_C", "PYR_H", "PYR_L", "PYR_C",
    "RND_DN",
    "EVT", "ETAT", "TF_TD", "TF_OK", "TF_STR", "V_ST", "V_SIG", "ST_ETAT",
]
EMPAQUETEES = ["EVT", "ETAT", "TF_TD", "TF_OK", "TF_STR", "V_ST", "V_SIG", "ST_ETAT"]

BITS = {
    "EVT": ["sig_long_fort", "sig_short_fort", "sig_long_moyen", "sig_short_moyen",
            "hei_flip_haut", "hei_flip_bas", "clx_buy", "clx_sell",
            "tl_cassure_haut", "tl_cassure_bas", "tl_res_nouvelle", "tl_sup_nouvelle",
            "zh_nouvelle", "zb_nouvelle", "zh_mitigee", "zb_mitigee",
            "mon_cassure_haut", "mon_cassure_bas", "div_haus", "div_bais"],
    "ETAT": ["hei_bleu", "blackout", "tl_res_active", "tl_sup_active", "dans_zh", "dans_zb",
             "orb_forme", "orb_en_cours", "en_asie", "en_londres", "en_us", "lundi_en_cours",
             "monday_pret", "au_dessus_ema50", "sig_conv", "sig_satur", "graphique_ha", "sig_run2"],
    "TF_TD": ["trend_3", "trend_5", "trend_15", "trend_60", "trend_240", "trend_1D",
              "dash_1", "dash_5", "dash_15", "dash_60", "dash_240", "dash_1D"],
    "TF_OK": ["ok_trend_3", "ok_trend_5", "ok_trend_15", "ok_trend_60", "ok_trend_240", "ok_trend_1D",
              "ok_dash_1", "ok_dash_5", "ok_dash_15", "ok_dash_60", "ok_dash_240", "ok_dash_1D",
              "ok_pa_1", "ok_pa_5", "ok_pa_15", "ok_macd10", "ok_jour"],
}
STR_NOMS = ["str_3", "str_5", "str_15", "str_60", "str_240", "str_1D"]
V_ST_NOMS = ["v_trend", "v_cross", "v_cci", "v_rsi", "v_macd", "v_gap", "v_pa1", "v_pa2", "v_pa3", "v_div"]
V_SIG_NOMS = ["s_supertrend", "s_ma", "s_vwap", "s_linreg", "s_cpr", "s_orb", "s_pd"]
MACD_ETATS = {0: "Bearish", 1: "Bullish", 2: "SUPERBULL", 3: "Basing"}
PA_ETATS = {0: "neut", 1: "super", 2: "warn", 3: "bull", 4: "bear"}
DIV_ETATS = {0: "neut", 1: "bull", 2: "bear"}
CROSS_ETATS = {0: "aucun", 1: "Golden", 2: "Death"}

RENOMMER = {
    "open": "ha_o", "high": "ha_h", "low": "ha_l", "close": "ha_c",
    "RO": "o", "RH": "h", "RL": "l", "RC": "c", "RV": "v", "RATR": "atr",
    "EMA50": "ema50", "EMA60": "ema60", "ADX": "adx", "DIP": "dip", "DIM": "dim",
    "RSI": "rsi", "CCI": "cci", "SCORE": "score", "FEU_L": "feu_l", "FEU_S": "feu_s",
    "TL_RES": "tl_res", "TL_SUP": "tl_sup",
    "ZH_SUP_H": "zh_sup_h", "ZH_SUP_B": "zh_sup_b", "ZH_INF_H": "zh_inf_h", "ZH_INF_B": "zh_inf_b",
    "ZB_SUP_H": "zb_sup_h", "ZB_SUP_B": "zb_sup_b", "ZB_INF_H": "zb_inf_h", "ZB_INF_B": "zb_inf_b",
    "ORB_H": "orb_h", "ORB_L": "orb_l", "AS_H": "as_h", "AS_L": "as_l", "LD_H": "ld_h",
    "LD_L": "ld_l", "US_H": "us_h", "US_L": "us_l", "MON_H": "mon_h", "MON_L": "mon_l",
    "RND_DN": "rond_dessous",
}
for _fam in ("W", "M", "Y"):
    for _k in ("H", "L", "C"):
        RENOMMER[f"P{_fam}_{_k}"] = f"p{_fam.lower()}_{_k.lower()}_prec"
        RENOMMER[f"P{_fam}R_{_k}"] = f"p{_fam.lower()}r_{_k.lower()}_prec"

# Documentation des colonnes du DataFrame renvoyé.
COLONNES = {
    "index (time)": "ouverture de la bougie, heure de Paris (Europe/Paris)",
    "ha_o ha_h ha_l ha_c": "bougie Heiken Ashi du graphique (colonnes open/high/low/close de l'export)",
    "o h l c v": "VRAIS prix et volume (contrat continu, ajustement du graphique conservé)",
    "atr": "ATR(14) des vrais prix (RMA du true range)",
    "ema50 ema60": "Moyenator (EMA du close HA)",
    "adx dip dim rsi cci": "oscillateurs sur bougies HA (DMI 14/14, RSI 14, CCI 30)",
    "score": "score Signator 0-100",
    "feu_l feu_s": "nombre de voix long / short du Feu (sur 29)",
    "tl_res tl_sup": "prix courant de la droite de résistance / support (na si aucune)",
    "zh_* zb_*": "bornes (h = haut, b = bas) des zones Detector haussières (zh) / baissières (zb) "
                 "les plus proches au-dessus (sup) et au-dessous (inf) de la clôture HA",
    "orb_h orb_l": "plage d'ouverture US (HA) ; *_vrai = même plage sur vrais prix",
    "as_h … us_l": "haut / bas de la session en cours ou de la dernière terminée (HA) ; *_vrai = vrais prix",
    "mon_h mon_l": "Monday High / Low (HA) ; mon_h_vrai mon_l_vrai = vrais prix",
    "p{w,m,y}_{h,l,c}_prec": "haut / bas / clôture HA de la période précédente (Pivator)",
    "p{w,m,y}r_{h,l,c}_prec": "idem sur vrais prix",
    "p{w,m,y}[r]_{p,r1..r5,s1..s5}": "pivots Traditionnels calculés depuis la période précédente",
    "p{w,m,y}[r]_dessus / _dessous": "pivot (P, R1-R5, S1-S5) le plus proche au-dessus / au-dessous du vrai close c",
    "rond_dessous rond_dessus": "niveau rond inférieur (arrondi du vrai close) et supérieur (+ intervalle)",
    "bits EVT / ETAT / TF_TD / TF_OK": "booléens nommés (voir BITS et INVENTAIRE.md)",
    "str_*": "STRENGTH 0-4 par unité TREND (NaN = pas de donnée)",
    "v_* s_*": "voix du Feu : +1 long, -1 short, 0 neutre",
    "macd_etat pa1_etat pa2_etat pa3_etat div_etat cross_etat": "états détaillés SuperTrader (texte)",
    "heure_paris heure_ny minute_ny": "heure décimale Paris / New York ; minute_ny = HHMM New York",
}


def _infos_fichier(chemin: str) -> tuple[str | None, str | None]:
    """Symbole et unité depuis le nom par défaut de TradingView : 'CME_MINI_MNQ1!, 15_ab12c.csv'."""
    b = os.path.basename(chemin)
    m = re.match(r"(?:[A-Z_]+?_)?([A-Z0-9!]+), ?([0-9]+[A-Z]?|[0-9]*[DWM])_", b)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def _lire_temps(s: pd.Series) -> pd.DatetimeIndex:
    """Heure de l'export : ISO avec décalage (ex. 2026-10-06T12:45:00+02:00) ou UNIX en secondes."""
    if pd.api.types.is_numeric_dtype(s):
        t = pd.to_datetime(s.astype("int64"), unit="s", utc=True)
    else:
        t = pd.to_datetime(s, utc=True)
    return pd.DatetimeIndex(t).tz_convert("Europe/Paris")


def _entiers(x: pd.Series) -> np.ndarray:
    return x.fillna(0).round().astype("int64").to_numpy()


def _bits(x: pd.Series, k: int) -> pd.Series:
    return pd.Series(((_entiers(x) >> k) & 1).astype(bool), index=x.index)


def _champ(x: pd.Series, k: int, largeur: int) -> pd.Series:
    return pd.Series((_entiers(x) >> (k * largeur)) & ((1 << largeur) - 1), index=x.index)


def _voix(x: pd.Series, k: int) -> pd.Series:
    c = _champ(x, k, 2)
    return c.map({0: 0, 1: 1, 2: -1}).fillna(0).astype("int8")


def _pivots_trad(df: pd.DataFrame, pre: str, out: dict) -> None:
    """Formule Traditionnelle du Pivator (identique à f_piv_trad de STRATEGIE_V1)."""
    h, l, c = df[f"{pre}_h_prec"], df[f"{pre}_l_prec"], df[f"{pre}_c_prec"]
    p = (h + l + c) / 3
    r1, s1 = 2 * p - l, 2 * p - h
    r2, s2 = p + (h - l), p - (h - l)
    r3, s3 = h + 2 * (p - l), l - 2 * (h - p)
    r4, s4 = r3 + (p - l), s3 - (h - p)
    r5, s5 = r4 + (p - l), s4 - (h - p)
    noms = []
    for n, v in (("p", p), ("r1", r1), ("s1", s1), ("r2", r2), ("s2", s2), ("r3", r3), ("s3", s3),
                 ("r4", r4), ("s4", s4), ("r5", r5), ("s5", s5)):
        out[f"{pre}_{n}"] = v
        noms.append(v.to_numpy(dtype=float))
    # Niveau le plus proche au-dessus / au-dessous du vrai close.
    m = np.column_stack(noms)
    ref = df["c"].to_numpy(dtype=float)[:, None]
    dessus = np.where(m > ref, m, np.inf).min(axis=1)
    dessous = np.where(m < ref, m, -np.inf).max(axis=1)
    out[f"{pre}_dessus"] = np.where(np.isfinite(dessus), dessus, np.nan)
    out[f"{pre}_dessous"] = np.where(np.isfinite(dessous), dessous, np.nan)


def _niveau_vrai(df: pd.DataFrame, drapeau: str, nom: str, out: dict, garde: pd.Series | None = None) -> None:
    """Haut / bas sur VRAIS prix d'une fenêtre repérée par un drapeau booléen (session, lundi,
    ORB) : cumul pendant la fenêtre, valeur gelée ensuite jusqu'au début de la suivante —
    même logique que DATASET.pine sur le HA."""
    inn = df[drapeau].to_numpy()
    debut = inn & ~np.r_[False, inn[:-1]]
    run = np.cumsum(debut)
    run_s = pd.Series(np.where(inn, run, 0), index=df.index)
    hh = df["h"].where(inn).groupby(run_s).cummax()
    ll = df["l"].where(inn).groupby(run_s).cummin()
    hh = hh.where(inn).ffill().where(run > 0)
    ll = ll.where(inn).ffill().where(run > 0)
    if garde is not None:
        hh = hh.where(garde)
        ll = ll.where(garde)
    out[f"{nom}_h_vrai"] = hh
    out[f"{nom}_l_vrai"] = ll


def charger(chemin: str, garder_brut: bool = False, intervalle_rond: float = 100.0,
            symbole: str | None = None, ut: str | None = None) -> pd.DataFrame:
    chemin = os.path.expanduser(chemin)
    brut = pd.read_csv(chemin)
    manquantes = [c for c in ["time", "open", "high", "low", "close"] + PLOTS if c not in brut.columns]
    if manquantes:
        raise ValueError(f"{os.path.basename(chemin)} : colonnes absentes {manquantes}. "
                         "L'export vient-il bien de « Dataset Strat-Botting » (V1) ? "
                         "Un en-tête suffixé « .1 » signale un doublon : retirer les autres indicateurs.")
    df = brut[["time", "open", "high", "low", "close"] + PLOTS].copy()
    df.index = _lire_temps(df.pop("time"))
    df.index.name = "time"
    df = df[~df.index.duplicated(keep="last")].sort_index()

    # Décodage des colonnes empaquetées (colonnes réunies puis ajoutées d'un bloc)
    dec: dict = {}
    for col, noms in BITS.items():
        for k, n in enumerate(noms):
            dec[n] = _bits(df[col], k)
    for k, n in enumerate(STR_NOMS):
        v = _champ(df["TF_STR"], k, 3).astype(float)
        dec[n] = v.where(v != 7)
    for k, n in enumerate(V_ST_NOMS):
        dec[n] = _voix(df["V_ST"], k)
    for k, n in enumerate(V_SIG_NOMS):
        dec[n] = _voix(df["V_SIG"], k)
    se = df["ST_ETAT"]
    dec["macd_etat"] = _champ(se, 0, 2).map(MACD_ETATS)
    dec["pa1_etat"] = pd.Series((_entiers(se) >> 2) & 7, index=df.index).map(PA_ETATS)
    dec["pa2_etat"] = pd.Series((_entiers(se) >> 5) & 7, index=df.index).map(PA_ETATS)
    dec["pa3_etat"] = pd.Series((_entiers(se) >> 8) & 7, index=df.index).map(PA_ETATS)
    dec["div_etat"] = pd.Series((_entiers(se) >> 11) & 3, index=df.index).map(DIV_ETATS)
    dec["cross_etat"] = pd.Series((_entiers(se) >> 13) & 3, index=df.index).map(CROSS_ETATS)
    df = pd.concat([df, pd.DataFrame(dec, index=df.index)], axis=1)

    df = df.rename(columns=RENOMMER)
    if not garder_brut:
        df = df.drop(columns=EMPAQUETEES)
    for c in ("feu_l", "feu_s"):
        df[c] = df[c].round().astype("Int64")

    # Dérivés
    der: dict = {}
    for pre in ("pw", "pm", "py", "pwr", "pmr", "pyr"):
        _pivots_trad(df, pre, der)
    der["rond_dessus"] = df["rond_dessous"] + intervalle_rond
    _niveau_vrai(df, "en_asie", "as", der)
    _niveau_vrai(df, "en_londres", "ld", der)
    _niveau_vrai(df, "en_us", "us", der)
    _niveau_vrai(df, "lundi_en_cours", "mon", der)
    _niveau_vrai(df, "orb_en_cours", "orb", der, garde=df["orb_h"].notna())

    idx = df.index
    ny = idx.tz_convert("America/New_York")
    der["heure_paris"] = idx.hour + idx.minute / 60
    der["heure_ny"] = ny.hour + ny.minute / 60
    der["minute_ny"] = ny.hour * 100 + ny.minute
    df = pd.concat([df, pd.DataFrame(der, index=df.index)], axis=1)

    s, u = _infos_fichier(chemin)
    df.attrs.update(symbole=symbole or s, ut=ut or u, fichier=os.path.basename(chemin))
    return df


def _resume(df: pd.DataFrame) -> str:
    lignes = [f"{df.attrs.get('fichier')} — symbole {df.attrs.get('symbole')}, UT {df.attrs.get('ut')}",
              f"{len(df)} bougies, du {df.index[0]} au {df.index[-1]} (heure de Paris), {df.shape[1]} colonnes"]
    ev = BITS["EVT"]
    lignes.append("Événements : " + ", ".join(f"{n} {int(df[n].sum())}" for n in ev))
    return "\n".join(lignes)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for f in sys.argv[1:]:
        print(_resume(charger(f)))
