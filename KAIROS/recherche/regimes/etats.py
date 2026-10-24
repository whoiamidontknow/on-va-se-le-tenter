"""États de marché observables à la CLÔTURE de chaque barre (aucune donnée future).

Toutes les grandeurs sont lues sur la barre i à sa clôture ; les seuils sont FIXÉS À L'AVANCE (pas optimisés) :
ADX 20, pente EMA50 sur 5 barres, terciles de volatilité par rang glissant sur les 960 barres PASSÉES
(≈ 10 jours de 15 min), Feu dominant si |voix long - voix short| >= 6 sur 29.

Briques (colonnes ajoutées par `briques(df)`) :
  tendance   +1 haussière (ADX >= 20, pente EMA50 > 0, clôture HA > EMA50), -1 baissière (miroir), 0 range
  aligne     +1 / -1 si TREND 15 (clôture HA > EMA50), TREND 60 et TREND 240 sont dans le même sens, 0 sinon
  hei60      +1 / -1 couleur Heishinator de la dernière bougie 1 h clôturée (0 si inconnue)
  vol        0 basse / 1 moyenne / 2 haute : tercile du rang de ATR14 / moyenne(ATR14, 100) sur 960 barres passées
  seance     0 Asie (17:00-02:00 NY) / 1 Londres (02:00-09:30 NY) / 2 ouverture US (09:30-11:30 NY) /
             3 après-midi US (11:30-17:00 NY)
  jour       0 lundi ... 4 vendredi (journée CME : la séance du dimanche soir compte pour lundi)
  pos_orb    +1 clôture > haut de l'ORB du jour, -1 < bas, 0 dedans ou ORB pas encore formé
             (ORB = bougie 09:30-09:45 NY sur VRAIS prix, connue à sa clôture)
  pos_mon    +1 clôture > Monday High, -1 < Monday Low, 0 dedans / niveaux pas prêts (vrais prix,
             lundi 00:00 -> mardi 07:30 Paris, comme DATASET.pine)
  feu        +1 / -1 Feu dominant long / short, 0 neutre (source cache : PROXY à 12 voix ramené sur 29)
  au_ema     +1 clôture HA > EMA50, -1 sinon

Partitions (6 à 12 états) : voir PARTITIONS ; 'UNIQUE' = un seul état (= meilleur setup unique).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

NS_MIN = 60_000_000_000


def _rang_glissant(x: pd.Series, fenetre=960, min_obs=200) -> pd.Series:
    """Rang (0-1) de x[i] parmi les `fenetre` valeurs PASSÉES (i exclu)."""
    v = x.to_numpy(float)
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        a = v[max(0, i - fenetre):i]
        a = a[~np.isnan(a)]
        if len(a) >= min_obs and not np.isnan(v[i]):
            out[i] = (a < v[i]).mean()
    return pd.Series(out, index=x.index)


def _jour_cme(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    t = idx.tz_convert('America/Chicago').tz_localize(None)
    return (t + pd.Timedelta(hours=7)).normalize()


def _orb(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Haut / bas de l'ORB du jour (1re bougie qui ouvre à 09:30 NY), connus à partir de sa clôture."""
    ny = df.index.tz_convert('America/New_York')
    m = ny.hour * 60 + ny.minute
    jour = ny.normalize()
    ut = int(np.median(np.diff(df.index.asi8)) // NS_MIN) or 15
    H = np.full(len(df), np.nan); L = np.full(len(df), np.nan)
    h = df['h'].to_numpy(float); l = df['l'].to_numpy(float)
    cur = None; curj = None
    for i in range(len(df)):
        if jour[i] != curj:
            curj = jour[i]; cur = None
        if 570 <= m[i] < 585:                 # barre(s) de la plage 09:30-09:45
            cur = [max(h[i], cur[0]) if cur else h[i], min(l[i], cur[1]) if cur else l[i], m[i] + ut >= 585]
        if cur and (cur[2] or m[i] >= 585) and m[i] < 1020:
            H[i], L[i] = cur[0], cur[1]
    return H, L


def _monday(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Monday High / Low sur vrais prix : lundi 00:00 -> mardi 07:30 Paris, prêts ensuite jusqu'à la fin de semaine."""
    p = df.index.tz_convert('Europe/Paris')
    wd = p.weekday; m = p.hour * 60 + p.minute
    sem = p.isocalendar().week.to_numpy() + 100 * p.isocalendar().year.to_numpy()
    h = df['h'].to_numpy(float); l = df['l'].to_numpy(float)
    H = np.full(len(df), np.nan); L = np.full(len(df), np.nan)
    cur = None; wk = None; pret = False
    for i in range(len(df)):
        if sem[i] != wk:
            wk = sem[i]; cur = None; pret = False
        fen = wd[i] == 0 or (wd[i] == 1 and m[i] < 450)
        if fen:
            cur = [h[i], l[i]] if cur is None else [max(cur[0], h[i]), min(cur[1], l[i])]
        elif cur is not None:
            pret = True
        if pret:
            H[i], L[i] = cur
    return H, L


def briques(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les colonnes d'état élémentaires (et les niveaux ORB / Monday vrais prix) à une copie de df."""
    df = df.copy()
    hac, e50, adx = df['ha_c'], df['ema50'], df['adx']
    pente = (e50 - e50.shift(5)) / df['atr']
    haus = (adx >= 20) & (pente > 0) & (hac > e50)
    bais = (adx >= 20) & (pente < 0) & (hac < e50)
    df['tendance'] = np.where(haus, 1, np.where(bais, -1, 0))
    t15 = hac > e50
    t60, t240 = df['trend_60'].astype(bool), df['trend_240'].astype(bool)
    ok = df.get('ok_trend_60', True) & df.get('ok_trend_240', True)
    df['aligne'] = np.where(ok & t15 & t60 & t240, 1, np.where(ok & ~t15 & ~t60 & ~t240, -1, 0))
    df['hei60'] = np.where(df.get('ok_hei_60', True), np.where(df['hei_60'].astype(bool), 1, -1), 0)
    ratio = df['atr'] / df['atr'].rolling(100, min_periods=50).mean()
    rg = _rang_glissant(ratio)
    df['vol'] = np.where(rg < 1 / 3, 0, np.where(rg < 2 / 3, 1, 2))
    df.loc[rg.isna(), 'vol'] = 1
    ny = df.index.tz_convert('America/New_York')
    m = ny.hour * 60 + ny.minute
    df['seance'] = np.where((m >= 120) & (m < 570), 1, np.where((m >= 570) & (m < 690), 2,
                            np.where((m >= 690) & (m < 1020), 3, 0)))
    df['jour'] = np.clip(_jour_cme(df.index).weekday, 0, 4)
    df['orb_h_r'], df['orb_l_r'] = _orb(df)
    c = df['c']
    df['pos_orb'] = np.where(c > df['orb_h_r'], 1, np.where(c < df['orb_l_r'], -1, 0))
    df['mon_h_r'], df['mon_l_r'] = _monday(df)
    df['pos_mon'] = np.where(c > df['mon_h_r'], 1, np.where(c < df['mon_l_r'], -1, 0))
    diff = (df['feu_l'].astype(float) - df['feu_s'].astype(float)).fillna(0)
    df['feu'] = np.where(diff >= 6, 1, np.where(diff <= -6, -1, 0))
    df['au_ema'] = np.where(hac > e50, 1, -1)
    return df


# ─── Partitions : nom -> (fonction df_briques -> codes entiers, libellés) ───
def _p(f, noms):
    return (f, noms)


PARTITIONS = {
    'UNIQUE': _p(lambda d: np.zeros(len(d), int), ['tout']),
    # tendance (ADX + pente EMA50) x volatilité basse / non basse : 6 états
    'TENDANCE_VOL': _p(lambda d: (d['tendance'].to_numpy() + 1) * 2 + (d['vol'].to_numpy() > 0),
                       ['baisse_volbasse', 'baisse_vol', 'range_volbasse', 'range_vol',
                        'hausse_volbasse', 'hausse_vol']),
    # séance x TREND multi-unités aligné (dans un sens ou l'autre) ou non : 8 états
    'SEANCE_ALIGNE': _p(lambda d: d['seance'].to_numpy() * 2 + (d['aligne'].to_numpy() != 0),
                        ['asie_nonal', 'asie_al', 'londres_nonal', 'londres_al', 'ouvUS_nonal', 'ouvUS_al',
                         'apmUS_nonal', 'apmUS_al']),
    # composite : régime multi-UT (tendance alignée haussière / baissière, range calme / agité) x séance active : 8
    'COMPOSITE': _p(lambda d: np.select([(d['aligne'] == 1) & (d['adx'] >= 20), (d['aligne'] == -1) & (d['adx'] >= 20),
                                         d['vol'] == 0], [0, 1, 2], 3) * 2 + (d['seance'].to_numpy() > 0),
                    ['th_asie', 'th_actif', 'tb_asie', 'tb_actif', 'rcalme_asie', 'rcalme_actif',
                     'ragite_asie', 'ragite_actif']),
    # position par rapport à l'ORB x Heishinator 1 h : 6 états
    'ORB_HEI60': _p(lambda d: (d['pos_orb'].to_numpy() + 1) * 2 + (d['hei60'].to_numpy() > 0),
                    ['sousORB_h60bas', 'sousORB_h60haut', 'dansORB_h60bas', 'dansORB_h60haut',
                     'surORB_h60bas', 'surORB_h60haut']),
    # position par rapport au Monday High/Low x volatilité basse / non basse : 6 états
    'MONDAY_VOL': _p(lambda d: (d['pos_mon'].to_numpy() + 1) * 2 + (d['vol'].to_numpy() > 0),
                     ['sousMon_volbasse', 'sousMon_vol', 'dansMon_volbasse', 'dansMon_vol',
                      'surMon_volbasse', 'surMon_vol']),
    # Feu de Confluence x ADX >= 20 : 6 états
    'FEU_ADX': _p(lambda d: (d['feu'].to_numpy() + 1) * 2 + (d['adx'].to_numpy() >= 20),
                  ['feuS_adxbas', 'feuS_adxhaut', 'feuN_adxbas', 'feuN_adxhaut', 'feuL_adxbas', 'feuL_adxhaut']),
    # jour de semaine x séance US (ouverture + après-midi) ou non : 10 états
    'JOUR_US': _p(lambda d: d['jour'].to_numpy() * 2 + (d['seance'].to_numpy() >= 2),
                  ['lun_horsUS', 'lun_US', 'mar_horsUS', 'mar_US', 'mer_horsUS', 'mer_US', 'jeu_horsUS', 'jeu_US',
                   'ven_horsUS', 'ven_US']),
}


def etiquettes(dfb: pd.DataFrame) -> pd.DataFrame:
    """Code d'état de chaque barre pour chaque partition (colonnes = noms de partition)."""
    return pd.DataFrame({k: np.asarray(f(dfb), int) for k, (f, _) in PARTITIONS.items()}, index=dfb.index)
