"""Les 20 votes de BIAIS_GLOBAL.md, calculés sans regard vers le futur.

  FOND (9)      : TREND, Dashator, STRENGTH sur 60, 240, 1D   (dernière bougie CLÔTURÉE de chaque unité)
  INTRADAY (11) : TREND + Dashator sur 5 et 15 min (4) + 7 lignes SIGNAL (SuperTrend, EMA50, VWAP, Lin Regress,
                  CPR, ORB, PDH/PDL)

Source DATASET : les colonnes exportées (trend_*, dash_*, str_*, s_*) sont lues telles quelles.
Source CACHE   : TREND / Dashator = colonnes trend_* / dash_* du chargeur ; STRENGTH recalculé ici sur les séries
HA (exportées si elles existent, sinon agrégées depuis les vrais prix) ; lignes SIGNAL recalculées (voir plus bas).
Ce que le cache NE permet PAS : voir `LIMITES_CACHE` (les votes concernés valent 0).
"""
from __future__ import annotations

import os
import pickle

import numpy as np
import pandas as pd

import donnees_wrx as D

DX = D.DX
M = D.M

LIMITES_CACHE = [
    "TREND/Dashator 5 min sur un graphique 15 min : pas de série 5 min alignée sur 15 min (le cache 5 min ne couvre"
    " que ~8 jours) -> vote 0 (2 voix sur 11 perdues).",
    "STRENGTH 60/240/1D : recalculé sur les séries HA exportées (ou agrégées des vrais prix) ; avant 50 bougies de"
    " l'unité (échauffement EMA50) -> 0.",
    "SuperTrend / VWAP : repli du chargeur (HA, pas les valeurs exactes de l'indicateur) ; EMA50 = close HA > EMA50 ;"
    " Lin Regress = close réel > régression linéaire 100 barres du graphique ; CPR sur la veille CME ; ORB = plage"
    " 09:30-09:45 NY (vrais prix) ; PDH/PDL = veille CME (vrais prix).",
]

_SER = {}


def _series_cache():
    if 'S' not in _SER:
        with open(os.path.join(DX.STRAT, 'cache_series.pkl'), 'rb') as fh:
            _SER['S'] = pickle.load(fh)
    return _SER['S']


# ───────────────────────────── STRENGTH (0-4) sur une série HA ─────────────────────────────
def _ema(x, p):
    return pd.Series(x).ewm(span=p, adjust=False).mean().to_numpy()


def _rsi(c, p=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.where(d > 0, d, 0.0)).ewm(alpha=1 / p, adjust=False).mean()
    dn = pd.Series(np.where(d < 0, -d, 0.0)).ewm(alpha=1 / p, adjust=False).mean()
    with np.errstate(invalid='ignore', divide='ignore'):
        rs = up / dn
    return (100 - 100 / (1 + rs)).fillna(50.0).to_numpy()


def _score_strength(ho, hc):
    macd = _ema(hc, 12) - _ema(hc, 26)
    sig = _ema(macd, 9)
    s = (hc > ho).astype(int) + (macd > sig) + (hc > _ema(hc, 50)) + (_rsi(hc) > 50)
    return s.astype(float)


def _etat_strength_export(S):
    T = pd.DatetimeIndex(pd.to_datetime([t.isoformat() for t in S['T']], utc=True))
    clo = T.as_unit('ns').asi8 + int(S['tfm']) * M.NS_MIN
    ho = np.array(S['o'], float); hc = np.array(S['c'], float)
    sc = _score_strength(ho, hc)
    sc[np.arange(S['n']) < 50] = np.nan
    return pd.DataFrame(dict(str=sc), index=clo)


def _etat_strength_agrege(S, H):
    """Agrège les vrais prix de la série S en unité H, puis HA et STRENGTH. Index = clôture. Dernière bougie ouverte exclue."""
    T = pd.DatetimeIndex(pd.to_datetime([t.isoformat() for t in S['T']], utc=True))
    t = T.as_unit('ns').asi8
    if H >= 1440:
        ny = T.tz_convert('America/New_York') + pd.Timedelta(hours=6)
        cle = (ny.year * 10000 + ny.month * 100 + ny.day).to_numpy()
    else:
        cle = t // (H * M.NS_MIN)
    g = pd.DataFrame(dict(k=cle, o=S['ro'], h=S['rh'], l=S['rl'], c=S['rc'], t=t)).groupby('k', sort=False)
    b = pd.DataFrame(dict(o=g['o'].first(), h=g['h'].max(), l=g['l'].min(), c=g['c'].last(), t=g['t'].last()))
    if len(b) < 2:
        return None
    ut = float(np.median(np.diff(t)))
    hc = (b.o + b.h + b.l + b.c).to_numpy() / 4
    ho = np.empty(len(b)); ho[0] = (b.o.iloc[0] + b.c.iloc[0]) / 2
    for j in range(1, len(b)):
        ho[j] = (ho[j - 1] + hc[j - 1]) / 2
    sc = _score_strength(ho, hc)
    sc[np.arange(len(b)) < 50] = np.nan
    sc[-1] = np.nan
    return pd.DataFrame(dict(str=sc), index=(b.t.to_numpy() + ut).astype(np.int64))


def strength_cache(df, marche):
    """{60: tableau, 240: …, 1440: …} de STRENGTH (0-4, NaN = pas de donnée) pour un jeu du cache."""
    SER = _series_cache()
    rac = {'MES': 'MES', 'NQ': 'NQ'}[marche]
    RAC = lambda s: D.DX.RACINE_SYM[s['sym']]  # noqa: E731
    out = {}
    for H in (60, 240, 1440):
        res = np.full(len(df), np.nan)
        for s in [s for s in SER if RAC(s) == rac and s['tfm'] == H]:
            o = DX._asof(df, _etat_strength_export(s))['str']
            res = np.where(np.isnan(res), o, res)
        if np.isnan(res).any():
            src = sorted([s for s in SER if RAC(s) == rac and 5 <= s['tfm'] < H and H % s['tfm'] == 0],
                         key=lambda s: -s['tfm'])
            for s in src:
                if not np.isnan(res).any():
                    break
                e = _etat_strength_agrege(s, H)
                if e is None:
                    continue
                res = np.where(np.isnan(res), DX._asof(df, e)['str'], res)
        out[H] = res
    return out


# ───────────────────────────── lignes SIGNAL (repli cache) ─────────────────────────────
def _linreg_fin(c, L=100):
    n = len(c); out = np.full(n, np.nan)
    if n < L:
        return out
    x = np.arange(L, dtype=float); xm = x.mean(); sxx = ((x - xm) ** 2).sum()
    w = np.lib.stride_tricks.sliding_window_view(c, L)
    ym = w.mean(1)
    slope = ((w - ym[:, None]) * (x - xm)).sum(1) / sxx
    out[L - 1:] = ym + slope * (L - 1 - xm)
    return out


def signaux_cache(df):
    """7 votes SIGNAL (+1 / -1 / 0) recalculés depuis le cache."""
    c = df['c'].to_numpy(float); n = len(df)
    v = {}
    v['s_supertrend'] = df['s_supertrend'].to_numpy(float)
    v['s_ma'] = np.where(df['au_dessus_ema50'].to_numpy(bool), 1.0, -1.0)
    v['s_vwap'] = df['s_vwap'].to_numpy(float)
    lr = _linreg_fin(c)
    v['s_linreg'] = np.where(np.isnan(lr), 0.0, np.where(c > lr, 1.0, -1.0))
    # CPR de la veille CME
    idx = df.index
    jc = (idx.tz_convert('America/Chicago') + pd.Timedelta(hours=7)).normalize()
    jcn = (jc.year * 10000 + jc.month * 100 + jc.day).to_numpy()
    g = pd.DataFrame(dict(j=jcn, h=df['h'].to_numpy(), l=df['l'].to_numpy(), c=c)).groupby('j')
    H, L, C = g['h'].max(), g['l'].min(), g['c'].last()
    jours = list(H.index)
    prev = {jours[k]: jours[k - 1] for k in range(1, len(jours))}
    pj = np.array([prev.get(x, -1) for x in jcn])
    ok = pj >= 0
    ph = np.where(ok, H.reindex(pj).to_numpy(), np.nan); pl = np.where(ok, L.reindex(pj).to_numpy(), np.nan)
    pc = np.where(ok, C.reindex(pj).to_numpy(), np.nan)
    pv = (ph + pl + pc) / 3; bc = (ph + pl) / 2; tc = 2 * pv - bc
    hi, lo = np.maximum(tc, bc), np.minimum(tc, bc)
    v['s_cpr'] = np.where(np.isnan(hi), 0.0, np.where(c > hi, 1.0, np.where(c < lo, -1.0, 0.0)))
    # ORB : la plage reste valable jusqu'à la fin de la journée (comme le Pine) -> propagée dans la journée CME
    oh = pd.Series(df['n_orb_h'].to_numpy(float)).groupby(jcn).ffill().to_numpy()
    ol = pd.Series(df['n_orb_l'].to_numpy(float)).groupby(jcn).ffill().to_numpy()
    v['s_orb'] = np.where(np.isnan(oh), 0.0, np.where(c > oh, 1.0, np.where(c < ol, -1.0, 0.0)))
    ph2, pl2 = df['n_pd_h'].to_numpy(float), df['n_pd_l'].to_numpy(float)
    v['s_pd'] = np.where(np.isnan(ph2), 0.0, np.where(c > ph2, 1.0, np.where(c < pl2, -1.0, 0.0)))
    return v


# ───────────────────────────── assemblage ─────────────────────────────
def _bin(df, nom):
    """Colonne booléenne/0-1 -> +1/-1 (NaN -> 0). None si absente."""
    if nom not in df:
        return None
    x = df[nom].to_numpy(float)
    ok = df['ok_' + nom].to_numpy(bool) if ('ok_' + nom) in df else np.ones(len(df), bool)
    return np.where(np.isnan(x) | ~ok, 0.0, np.where(x > 0.5, 1.0, -1.0))


def calculer_votes(df, jeu, source):
    """DataFrame (une colonne par vote, valeurs -1/0/+1) + F (somme/9), I (somme/11). Aucune donnée future."""
    n = len(df); ut = jeu['ut']
    V = {}
    # ---- FOND
    if source == 'cache':
        st = strength_cache(df, jeu['marche'])
    for u, lib in ((60, '60'), (240, '240'), (1440, '1D')):
        V['trend_' + lib] = _bin(df, 'trend_' + lib) if 'trend_' + lib in df else np.zeros(n)
        V['dash_' + lib] = _bin(df, 'dash_' + lib) if 'dash_' + lib in df else np.zeros(n)
        if source == 'cache':
            s = st[u]
        else:
            s = df['str_' + lib].to_numpy(float) if 'str_' + lib in df else np.full(n, np.nan)
        V['str_' + lib] = np.where(np.isnan(s), 0.0, np.where(s >= 3, 1.0, np.where(s <= 1, -1.0, 0.0)))
    # ---- INTRADAY : TREND + Dashator 5 et 15 min
    propre = {'trend': np.where(df['au_dessus_ema50'].to_numpy(bool), 1.0, -1.0),
              'dash': np.where(df['ha_c'].to_numpy(float) > df['ha_o'].to_numpy(float), 1.0, -1.0)}
    for u in (5, 15):
        for k in ('trend', 'dash'):
            nom = '%s_%d' % (k, u)
            x = None
            if u != ut:
                x = _bin(df, nom)
            elif source == 'dataset':
                x = _bin(df, nom)
            V[nom] = x if x is not None else (propre[k] if u == ut else np.zeros(n))
    # ---- 7 lignes SIGNAL
    noms = ["s_supertrend", "s_ma", "s_vwap", "s_linreg", "s_cpr", "s_orb", "s_pd"]
    if source == 'dataset' and all(k in df for k in noms):
        for k in noms:
            V[k] = np.nan_to_num(df[k].to_numpy(float))
    else:
        V.update(signaux_cache(df))
    V = pd.DataFrame({k: np.asarray(x, float) for k, x in V.items()}, index=df.index)
    fond = [c for c in V if c.endswith(('_60', '_240', '_1D')) and not c.endswith(('_15',))]
    fond = ['trend_60', 'dash_60', 'str_60', 'trend_240', 'dash_240', 'str_240', 'trend_1D', 'dash_1D', 'str_1D']
    intra = ['trend_5', 'dash_5', 'trend_15', 'dash_15', "s_supertrend", "s_ma", "s_vwap", "s_linreg", "s_cpr",
             "s_orb", "s_pd"]
    assert len(fond) == 9 and len(intra) == 11
    V['F'] = V[fond].sum(axis=1) / 9.0
    V['I'] = V[intra].sum(axis=1) / 11.0
    return V
