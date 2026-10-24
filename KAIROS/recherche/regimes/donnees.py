"""Accès aux données de l'agent Régimes (REG) — TOUT l'accès aux données passe par `charger_series`.

Passage au DATASET : lancer avec `--source dataset` (ou changer SOURCE_DEFAUT ci-dessous). Rien d'autre à
modifier : les deux sources rendent des DataFrames aux NOMS DE COLONNES de `dataset/charger.py`.

- source 'cache'   : séries 15 min de tools/strategie/cache_series.pkl (modules recalculés en Python sur les
                     exports HA, vrais prix reconstitués). Colonnes absentes du cache reconstruites ici :
                     TREND / Dashator 60 et 240 (bougie clôturée de l'unité supérieure, vrais prix agrégés,
                     comme tools/strategie/features.resample_real), Feu = PROXY à 12 voix de strat.ensure_feu
                     (l'original en a 29), pas de STRENGTH, pas de Signator Moyen (0 dans le cache).
- source 'dataset' : exports DATASET.pine 15 min de ~/Ephore/KAIROS-data (dataset/charger.py).

Seul le DÉVELOPPEMENT (75 %) est rendu (moteur.charger_recherche, scellé fermé).
"""
from __future__ import annotations

import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
RACINE = os.path.abspath(os.path.join(SB, '..'))
STRAT = os.path.join(RACINE, 'tools', 'strategie')
sys.path[:0] = [os.path.join(SB, 'moteur'), os.path.join(SB, 'dataset'), os.path.join(SB, 'propfirm')]
import moteur as M  # noqa: E402

SOURCE_DEFAUT = 'cache'
DOSSIER_DATASET = os.path.expanduser('~/Ephore/KAIROS-data')

# séries 15 min retenues dans le cache (MES1 21/09-30/09 écartée : recouvre MES 15/09-15/10)
CACHE_SERIES = [('MES1', '15', '2026-04-29', 'MES', 'MES1_avr-juil'),
                ('MES', '15', '2026-09-15', 'MES', 'MES_sep-oct'),
                ('NQZ', '15', '2026-09-18', 'MNQ', 'NQ_sep-oct')]


def _instrument_depuis_symbole(sym: str) -> str:
    s = (sym or '').upper()
    return 'MNQ' if 'NQ' in s else 'MES'


def _cache_vers_df(S) -> pd.DataFrame:
    sys.path[:0] = [STRAT, os.path.join(RACINE, 'tools', 'ephore_api')]
    import strat as ST
    ST.ensure_htf(S)
    ST.ensure_feu(S)
    n = S['n']
    idx = pd.DatetimeIndex(S['T']).tz_convert('Europe/Paris')
    f = lambda x: np.array([np.nan if v is None else v for v in x], float)
    sig = S['sig']
    d = dict(
        o=S['ro'], h=S['rh'], l=S['rl'], c=S['rc'], atr=f(S['ratr']),
        ha_o=S['o'], ha_h=S['h'], ha_l=S['l'], ha_c=S['c'],
        ema50=f(S['e50']), ema60=f(S['e60']), adx=f(S['adx']), dip=f(S['dip']), dim=f(S['dim']),
        hei_bleu=np.array(S['bull'], bool),
        sig_long_fort=np.array([bool(x) and x[0] == 'F' and x[1] == 1 for x in sig]),
        sig_short_fort=np.array([bool(x) and x[0] == 'F' and x[1] == -1 for x in sig]),
        sig_long_moyen=np.array([bool(x) and x[0] == 'M' and x[1] == 1 for x in sig]),
        sig_short_moyen=np.array([bool(x) and x[0] == 'M' and x[1] == -1 for x in sig]),
        clx_buy=np.array([x == 1 for x in S['clx']]), clx_sell=np.array([x == -1 for x in S['clx']]),
        tl_cassure_haut=np.array(S['rB'], bool), tl_cassure_bas=np.array(S['sB'], bool),
        zh_mitigee=np.array(S['mitB'], bool), zb_mitigee=np.array(S['mitS'], bool),
    )
    bull = d['hei_bleu']
    d['hei_flip_haut'] = bull & ~np.r_[True, bull[:-1]]
    d['hei_flip_bas'] = ~bull & np.r_[False, bull[:-1]]
    for nom, cle in (('60', 'htf'), ('240', 'htf2')):
        H = S[cle]
        d['trend_' + nom] = np.array([bool(x and x['trend']) for x in H])
        d['dash_' + nom] = np.array([bool(x and x['dash']) for x in H])
        d['ok_trend_' + nom] = np.array([x is not None for x in H])
        d['hei_' + nom] = np.array([bool(x and x['heishi']) for x in H])
        d['ok_hei_' + nom] = d['ok_trend_' + nom]
    feu = S['feu']
    fl = np.array([np.nan if x is None else round(29 * x) for x in feu], float)
    d['feu_l'] = fl
    d['feu_s'] = 29 - fl
    df = pd.DataFrame(d, index=idx)
    df.index.name = 'time'
    df.attrs['feu_proxy'] = True
    return df


def _hei_htf(df: pd.DataFrame, minutes: int) -> tuple[np.ndarray, np.ndarray]:
    """Heishinator de l'unité supérieure (EMA(ohlc4,4) > EMA(ohlc4,32) sur HA des vrais prix agrégés), lu sur
    la dernière bougie de l'unité supérieure CLÔTURÉE à la clôture de chaque barre (aucun regard vers le futur).
    Sert pour la source 'dataset' (absent de DATASET.pine)."""
    t = df.index.tz_convert('UTC')
    if minutes >= 1440:
        k = (df.index.tz_convert('America/New_York') + pd.Timedelta(hours=6)).normalize().asi8
    else:
        k = (t.asi8 // 60_000_000_000) // minutes
    g = pd.DataFrame(dict(k=k, o=df['o'].to_numpy(), h=df['h'].to_numpy(), l=df['l'].to_numpy(),
                          c=df['c'].to_numpy()))
    b = g.groupby('k', sort=False).agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'))
    hc = (b.o + b.h + b.l + b.c).to_numpy() / 4
    ho = np.empty(len(b))
    for j in range(len(b)):
        ho[j] = (b.o.iat[j] + b.c.iat[j]) / 2 if j == 0 else (ho[j - 1] + hc[j - 1]) / 2
    hh = np.maximum.reduce([b.h.to_numpy(), ho, hc]); hl = np.minimum.reduce([b.l.to_numpy(), ho, hc])
    s4 = pd.Series((ho + hh + hl + hc) / 4)
    bullh = (s4.ewm(span=4, adjust=False).mean() > s4.ewm(span=32, adjust=False).mean()).to_numpy()
    # état connu à partir de la DERNIÈRE barre de chaque bougie HTF (sauf la dernière, peut-être incomplète)
    pos = pd.Series(np.arange(len(g))).groupby(g['k'].to_numpy(), sort=False).max().to_numpy()
    out = np.full(len(g), np.nan)
    for j in range(len(b) - 1):
        if j >= 32:
            out[pos[j]] = bullh[j]
    s = pd.Series(out).ffill().to_numpy()
    return s == 1, ~np.isnan(s)


def charger_series(source: str | None = None, ut: str = '15') -> list[dict]:
    """Liste de dict(nom, instrument, df) — df = DÉVELOPPEMENT seulement, colonnes au format dataset/charger.py,
    + colonnes hei_60/hei_240 (et ok_*) ajoutées si absentes."""
    source = source or os.environ.get('REG_SOURCE', SOURCE_DEFAUT)
    out = []
    if source == 'cache':
        S_all = pickle.load(open(os.path.join(STRAT, 'cache_series.pkl'), 'rb'))
        for sym, tf, debut, inst, nom in CACHE_SERIES:
            S = next(s for s in S_all if s['sym'] == sym and s['tf'] == tf
                     and str(s['T'][0].date()) == debut)
            df = _cache_vers_df(S)
            out.append(dict(nom=nom, instrument=inst, df=M.charger_recherche(df, agent='regimes')))
    elif source == 'dataset':
        from charger import charger
        for f in sorted(glob.glob(os.path.join(DOSSIER_DATASET, '*, %s_*.csv' % ut))):
            df = charger(f)
            for m in (60, 240):
                if 'hei_%d' % m not in df:
                    df['hei_%d' % m], df['ok_hei_%d' % m] = _hei_htf(df, m)
            sym = df.attrs.get('symbole') or os.path.basename(f)
            out.append(dict(nom='%s_%s' % (sym, os.path.basename(f)[-9:-4]), instrument=_instrument_depuis_symbole(sym),
                            df=M.charger_recherche(df, agent='regimes')))
        if not out:
            raise FileNotFoundError('aucun export DATASET %s min dans %s' % (ut, DOSSIER_DATASET))
    else:
        raise ValueError(source)
    return out


if __name__ == '__main__':
    for s in charger_series(sys.argv[1] if len(sys.argv) > 1 else None):
        df = s['df']
        print(s['nom'], s['instrument'], len(df), df.index[0], df.index[-1])
