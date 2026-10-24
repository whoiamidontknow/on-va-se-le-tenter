"""Accès aux données de l'explorateur exhaustif (EXH).

TOUT l'accès aux données passe par `charger_jeux()`. Pour passer au DATASET : SOURCE = 'dataset'
(ou `charger_jeux(source='dataset')`) ; le reste du code ne change pas.

Chaque jeu = dict(nom, marche ('MES'|'NQ'), instrument (micro du moteur : 'MES'|'MNQ'), ut (minutes), df).
`df` : index = OUVERTURE de la bougie (Europe/Paris), colonnes au format de `dataset/charger.py`
(o h l c = VRAIS prix, atr, ha_*, ema50, ema60, adx, dip, dim, hei_bleu, hei_flip_haut/bas, sig_*, clx_*,
tl_cassure_*, dans_zh/zb, zh_/zb_mitigee, zh_inf_*, zb_sup_*, blackout, trend_*, dash_*, …), puis complété
par `enrichir()` (niveaux de sessions / ORB / Monday / veille sur vrais prix, volatilité relative, RSI,
CCI, SuperTrend, VWAP et Feu de substitution si absents, HTF Heishinator). Aucune donnée future :
multi-UT = dernière bougie CLÔTURÉE, niveaux = dernière fenêtre TERMINÉE avant la bougie.

Seule la partie DÉVELOPPEMENT (75 %) est renvoyée (moteur.charger_recherche, scellé non ouvert).
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
sys.path[:0] = [os.path.join(SB, 'moteur'), os.path.join(SB, 'dataset'), STRAT]
import moteur as M  # noqa: E402

SOURCE = 'cache'            # 'cache' (séries Python ≈ 2 mois) | 'dataset' (exports DATASET.pine)
DOSSIER_DATASET = os.path.expanduser('~/Ephore/KAIROS-data')
UT_RETENUES = (5, 15, 30, 60)
CACHE_JEUX = os.path.join(ICI, 'cache_jeux_%s.pkl')


# ════════════════════════════════════════════════════════════════════════════════════════
# Point d'entrée UNIQUE
# ════════════════════════════════════════════════════════════════════════════════════════
def charger_jeux(source=None, uts=UT_RETENUES, recalcul=False):
    source = source or SOURCE
    chemin = CACHE_JEUX % source
    if not recalcul and os.path.exists(chemin) and source == 'cache':
        with open(chemin, 'rb') as fh:
            jeux = pickle.load(fh)
    else:
        jeux = _jeux_cache() if source == 'cache' else _jeux_dataset()
        for j in jeux:
            j['df'] = enrichir(j['df'], j['ut'], j['marche'])
            j['df'] = M.charger_recherche(j['df'], agent='EXH')          # développement seulement
        if source == 'cache':
            with open(chemin, 'wb') as fh:
                pickle.dump(jeux, fh)
    return [j for j in jeux if j['ut'] in uts]


# ════════════════════════════════════════════════════════════════════════════════════════
# Source 1 : DATASET.pine (dataset/charger.py)
# ════════════════════════════════════════════════════════════════════════════════════════
def _jeux_dataset():
    from charger import charger
    jeux = []
    for f in sorted(glob.glob(os.path.join(DOSSIER_DATASET, '*.csv'))):
        df = charger(f)
        sym, ut = str(df.attrs.get('symbole') or ''), str(df.attrs.get('ut') or '')
        marche = 'NQ' if 'NQ' in sym.upper() else 'MES' if 'ES' in sym.upper() else None
        if marche is None or not ut.isdigit():
            continue
        jeux.append(dict(nom='%s_%s' % (marche, ut), marche=marche, instrument='MNQ' if marche == 'NQ' else 'MES',
                         ut=int(ut), df=df))
    return jeux


# ════════════════════════════════════════════════════════════════════════════════════════
# Source 2 : cache_series.pkl (modules recalculés en Python, vrais prix reconstitués)
# ════════════════════════════════════════════════════════════════════════════════════════
JEUX_CACHE = [  # (nom, sym, tfm, indices des morceaux) — morceaux qui ne se recouvrent pas
    ('MES_5', 'MES', 5, None), ('NQ_5', 'NQZ', 5, None),
    ('MES_15', 'MES', 15, None), ('MES1_15', 'MES1', 15, [0]), ('NQ_15', 'NQZ', 15, None),
    ('MES_30', 'MES', 30, None), ('NQ_30', 'NQZ', 30, None),
    ('MES_60', 'MES', 60, None), ('NQ_60', 'NQZ', 60, None),
]
RACINE_SYM = {'MES': 'MES', 'MES1': 'MES', 'NQZ': 'NQ'}


def _arr(x):
    return np.array([np.nan if v is None else v for v in x], float)


def _df_serie(S):
    import features as F0
    T = pd.DatetimeIndex(pd.to_datetime([t.isoformat() for t in S['T']], utc=True)).tz_convert('Europe/Paris')
    n = S['n']
    bull = np.array(S['bull'], bool); run = np.array(S['run'])
    flip = (run == 1) & (np.arange(n) > 0)
    sig = S['sig']
    hc = np.array(S['c'], float)
    d = dict(o=_arr(S['ro']), h=_arr(S['rh']), l=_arr(S['rl']), c=_arr(S['rc']), atr=_arr(S['ratr']),
             ha_o=_arr(S['o']), ha_h=_arr(S['h']), ha_l=_arr(S['l']), ha_c=hc, v=_arr(S['v']),
             ema50=_arr(S['e50']), ema60=_arr(S['e60']), adx=_arr(S['adx']), dip=_arr(S['dip']), dim=_arr(S['dim']),
             hei_bleu=bull, hei_flip_haut=flip & bull, hei_flip_bas=flip & ~bull,
             sig_long_fort=np.array([bool(x) and x == ('F', 1) for x in sig]),
             sig_short_fort=np.array([bool(x) and x == ('F', -1) for x in sig]),
             sig_long_moyen=np.array([bool(x) and x == ('M', 1) for x in sig]),
             sig_short_moyen=np.array([bool(x) and x == ('M', -1) for x in sig]),
             clx_buy=np.array(S['clx']) == 1, clx_sell=np.array(S['clx']) == -1,
             tl_cassure_haut=np.array(S['rB'], bool), tl_cassure_bas=np.array(S['sB'], bool),
             zh_mitigee=np.array(S['mitB'], bool), zb_mitigee=np.array(S['mitS'], bool),
             blackout=np.array([F0.news(t, S['tfm']) for t in S['T']], bool))
    d['au_dessus_ema50'] = hc > d['ema50']
    # zones Detector (prix HA, comme l'indicateur)
    dzh = np.zeros(n, bool); dzb = np.zeros(n, bool)
    lv = {k: np.full(n, np.nan) for k in ('zh_inf_h', 'zh_inf_b', 'zh_sup_h', 'zh_sup_b',
                                          'zb_inf_h', 'zb_inf_b', 'zb_sup_h', 'zb_sup_b')}
    for i in range(n):
        c = hc[i]
        for nom, zones, dans in (('zh', S['Zb'][i] or [], dzh), ('zb', S['Zs'][i] or [], dzb)):
            inf = [z for z in zones if z[0] < c]; sup = [z for z in zones if z[1] > c]
            if any(b <= c <= t for t, b in zones):
                dans[i] = True
            if inf:
                t, b = max(inf, key=lambda z: z[0]); lv[nom + '_inf_h'][i] = t; lv[nom + '_inf_b'][i] = b
            if sup:
                t, b = min(sup, key=lambda z: z[1]); lv[nom + '_sup_h'][i] = t; lv[nom + '_sup_b'][i] = b
    d['dans_zh'] = dzh; d['dans_zb'] = dzb
    d.update(lv)
    if not S['hasv']:     # pas de volume : ni climax ni Detector exploitables
        for k in ('clx_buy', 'clx_sell', 'zh_mitigee', 'zb_mitigee', 'dans_zh', 'dans_zb'):
            d[k] = np.zeros(n, bool)
    return pd.DataFrame(d, index=T)


def _etats_htf_export(S):
    """États d'une série HTF exportée, indexés par l'instant de CLÔTURE (ns UTC) : trend, hei, dash."""
    T = pd.DatetimeIndex(pd.to_datetime([t.isoformat() for t in S['T']], utc=True))
    clo = T.as_unit('ns').asi8 + int(S['tfm']) * M.NS_MIN
    hc = np.array(S['c'], float); ho = np.array(S['o'], float); e50 = _arr(S['e50'])
    ok = np.arange(S['n']) >= 50
    return pd.DataFrame(dict(trend=np.where(ok, hc > e50, np.nan), hei=np.where(ok, np.array(S['bull'], float), np.nan),
                             dash=np.where(ok, hc > ho, np.nan)), index=clo)


def _ema(x, p):
    return pd.Series(x).ewm(span=p, adjust=False).mean().to_numpy()


def _etats_htf_reels(df, H):
    """Repli : agrège les vrais prix de df en unité H, puis HA, EMA50 du close HA, Heishinator. Index = clôture."""
    t = df.index.tz_convert('UTC').as_unit('ns').asi8
    if H >= 1440:
        ny = df.index.tz_convert('America/New_York') + pd.Timedelta(hours=6)
        cle = (ny.year * 10000 + ny.month * 100 + ny.day).to_numpy()
    else:
        cle = t // (H * M.NS_MIN)
    g = pd.DataFrame(dict(k=cle, o=df['o'].to_numpy(), h=df['h'].to_numpy(), l=df['l'].to_numpy(),
                          c=df['c'].to_numpy(), t=t)).groupby('k', sort=False)
    b = pd.DataFrame(dict(o=g['o'].first(), h=g['h'].max(), l=g['l'].min(), c=g['c'].last(), t=g['t'].last()))
    if len(b) < 2:
        return None
    ut = float(np.median(np.diff(t))) if len(t) > 1 else 0
    hc = (b.o + b.h + b.l + b.c).to_numpy() / 4
    ho = np.empty(len(b)); ho[0] = (b.o.iloc[0] + b.c.iloc[0]) / 2
    for j in range(1, len(b)):
        ho[j] = (ho[j - 1] + hc[j - 1]) / 2
    hh = np.maximum(b.h.to_numpy(), np.maximum(ho, hc)); hl = np.minimum(b.l.to_numpy(), np.minimum(ho, hc))
    s4 = (ho + hh + hl + hc) / 4
    e50 = _ema(hc, 50)
    ok = np.arange(len(b)) >= 50
    clo = (b.t.to_numpy() + ut).astype(np.int64)
    # la bougie HTF n'est close que si la suivante a commencé (la dernière reste ouverte)
    ok[-1] = False
    return pd.DataFrame(dict(trend=np.where(ok, hc > e50, np.nan), hei=np.where(ok, _ema(s4, 4) > _ema(s4, 32), np.nan),
                             dash=np.where(ok, hc > ho, np.nan)), index=clo)


def _asof(df, etats):
    """Dernier état HTF clôturé au plus tard à la clôture de chaque bougie de df."""
    ut = float(np.median(np.diff(df.index.tz_convert('UTC').as_unit('ns').asi8)))
    tc = df.index.tz_convert('UTC').as_unit('ns').asi8 + int(ut)
    e = etats[~etats.index.duplicated(keep='last')].sort_index()
    k = np.searchsorted(e.index.to_numpy(), tc, side='right') - 1
    out = {c: np.where(k >= 0, e[c].to_numpy()[np.clip(k, 0, None)], np.nan) for c in e.columns}
    return out


def _jeux_cache():
    with open(os.path.join(STRAT, 'cache_series.pkl'), 'rb') as fh:
        SER = pickle.load(fh)
    jeux = []
    for nom, sym, tfm, morceaux in JEUX_CACHE:
        ps = [s for s in SER if s['sym'] == sym and s['tfm'] == tfm]
        if morceaux is not None:
            ps = [ps[i] for i in morceaux]
        if not ps:
            continue
        df = pd.concat([_df_serie(s) for s in ps]).sort_index()
        df = df[~df.index.duplicated(keep='last')]
        rac = RACINE_SYM[sym]
        # multi-UT : séries exportées de la même racine, sinon repli sur les vrais prix
        for H, lib in ((15, '15'), (60, '60'), (240, '240'), (1440, '1D')):
            if H <= tfm:
                continue
            ex = [s for s in SER if RACINE_SYM[s['sym']] == rac and s['tfm'] == H]
            base = {k: np.full(len(df), np.nan) for k in ('trend', 'hei', 'dash')}
            for s in ex:
                o = _asof(df, _etats_htf_export(s))
                for k in base:
                    base[k] = np.where(np.isnan(base[k]), o[k], base[k])
            # repli : série exportée la plus fine de la racine qui couvre, puis la série elle-même
            sources = sorted([s for s in SER if RACINE_SYM[s['sym']] == rac and tfm <= s['tfm'] < H and H % s['tfm'] == 0],
                             key=lambda s: -s['tfm'])
            for s in sources:
                if not np.isnan(base['trend']).any():
                    break
                e = _etats_htf_reels(_df_serie(s), H)
                if e is None:
                    continue
                o = _asof(df, e)
                for k in base:
                    base[k] = np.where(np.isnan(base[k]), o[k], base[k])
            df['trend_' + lib] = base['trend']; df['hei_' + lib] = base['hei']; df['dash_' + lib] = base['dash']
        jeux.append(dict(nom=nom, marche=rac, instrument='MNQ' if rac == 'NQ' else 'MES', ut=tfm, df=df))
    return jeux


# ════════════════════════════════════════════════════════════════════════════════════════
# Enrichissement commun (les deux sources)
# ════════════════════════════════════════════════════════════════════════════════════════
def _minutes(idx, tz):
    x = idx.tz_convert(tz)
    return (x.hour * 60 + x.minute).to_numpy()


def _fenetre_terminee(df, dans, cle_validite=None):
    """Haut / bas (vrais prix) de la dernière fenêtre TERMINÉE avant chaque bougie (fenêtre = suite de True
    dans `dans`). cle_validite : niveau effacé quand la clé (jour, semaine) diffère de celle de la fenêtre."""
    n = len(df)
    h = df['h'].to_numpy(); l = df['l'].to_numpy()
    debut = dans & ~np.r_[False, dans[:-1]]
    rid = np.cumsum(debut)
    H = np.full(n, np.nan); L = np.full(n, np.nan); K = np.full(n, np.nan)
    fin = dans & ~np.r_[dans[1:], False]
    for j in np.flatnonzero(fin):
        r = rid[j]
        i0 = np.flatnonzero(debut[:j + 1])[-1]
        if j + 1 < n:
            H[j + 1] = np.nanmax(h[i0:j + 1]); L[j + 1] = np.nanmin(l[i0:j + 1])
            if cle_validite is not None:
                K[j + 1] = cle_validite[j]
    H = pd.Series(H).ffill().to_numpy(); L = pd.Series(L).ffill().to_numpy()
    if cle_validite is not None:
        K = pd.Series(K).ffill().to_numpy()
        bon = K == cle_validite
        H = np.where(bon, H, np.nan); L = np.where(bon, L, np.nan)
    return H, L


def _rsi(x, p=14):
    d = np.diff(x, prepend=x[0])
    up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / p, adjust=False).mean()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / p, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).to_numpy()


def _cci(h, l, c, p=30):
    tp = pd.Series((h + l + c) / 3)
    m = tp.rolling(p).mean()
    md = tp.rolling(p).apply(lambda w: np.abs(w - w.mean()).mean(), raw=True)
    return ((tp - m) / (0.015 * md)).to_numpy()


def _supertrend(h, l, c, k=3.0, p=10):
    n = len(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.r_[c[0], c[:-1]]), np.abs(l - np.r_[c[0], c[:-1]])))
    atr = pd.Series(tr).ewm(alpha=1 / p, adjust=False).mean().to_numpy()
    hl2 = (h + l) / 2
    up = hl2 - k * atr; dn = hl2 + k * atr
    d = np.ones(n)
    for i in range(1, n):
        up[i] = max(up[i], up[i - 1]) if c[i - 1] > up[i - 1] else up[i]
        dn[i] = min(dn[i], dn[i - 1]) if c[i - 1] < dn[i - 1] else dn[i]
        d[i] = 1 if (d[i - 1] == -1 and c[i] > dn[i - 1]) else -1 if (d[i - 1] == 1 and c[i] < up[i - 1]) else d[i - 1]
    return d


def enrichir(df, ut, marche):
    df = df.copy()
    n = len(df)
    idx = df.index
    o, h, l, c, a = (df[k].to_numpy(float) for k in ('o', 'h', 'l', 'c', 'atr'))
    hc = df['ha_c'].to_numpy(float) if 'ha_c' in df else c
    # ---- niveaux sur vrais prix (dernière fenêtre terminée)
    for nom, tz, a0, b0 in (('as', 'Asia/Tokyo', 540, 930), ('ld', 'Europe/London', 480, 990),
                            ('us', 'America/New_York', 570, 960)):
        m = _minutes(idx, tz)
        H, L = _fenetre_terminee(df, (m >= a0) & (m < b0))
        df['n_%s_h' % nom] = H; df['n_%s_l' % nom] = L
    ny = idx.tz_convert('America/New_York')
    jour_ny = (ny.year * 10000 + ny.month * 100 + ny.day).to_numpy()
    mny = _minutes(idx, 'America/New_York')
    if ut <= 30:
        w = max(15, ut)
        orb_ok = (mny >= 570) & (mny < 570 + w)
        H, L = _fenetre_terminee(df, orb_ok, cle_validite=jour_ny.astype(float))
        fin_us = mny >= 960
        df['n_orb_h'] = np.where(fin_us, np.nan, H); df['n_orb_l'] = np.where(fin_us, np.nan, L)
    else:
        df['n_orb_h'] = np.nan; df['n_orb_l'] = np.nan
    pa = idx.tz_convert('Europe/Paris')
    mpa = (pa.hour * 60 + pa.minute).to_numpy(); wd = pa.weekday.to_numpy()
    iso = pa.isocalendar()
    sem = (iso['year'].to_numpy() * 100 + iso['week'].to_numpy()).astype(float)
    lundi = (wd == 0) | ((wd == 1) & (mpa < 450))
    H, L = _fenetre_terminee(df, lundi, cle_validite=sem)
    df['n_mon_h'] = H; df['n_mon_l'] = L
    # veille (journée CME 17:00 Chicago)
    jc = (idx.tz_convert('America/Chicago') + pd.Timedelta(hours=7)).normalize()
    jcn = jc.year * 10000 + jc.month * 100 + jc.day
    g = pd.DataFrame(dict(j=jcn, h=h, l=l)).groupby('j')
    hj, lj = g['h'].max(), g['l'].min()
    pj = pd.Series(hj.index).shift(1)
    mp = dict(zip(hj.index, pj))
    prev = np.array([mp.get(x, np.nan) for x in jcn])
    df['n_pd_h'] = np.array([hj.get(p, np.nan) if p == p else np.nan for p in prev])
    df['n_pd_l'] = np.array([lj.get(p, np.nan) if p == p else np.nan for p in prev])
    pas = 100.0
    df['n_rond_bas'] = np.floor(c / pas) * pas
    df['n_rond_haut'] = df['n_rond_bas'] + pas
    # ---- volatilité relative, jour, heure
    df['vol_rel'] = a / pd.Series(a).rolling(100, min_periods=50).mean().to_numpy()
    df['min_paris'] = mpa; df['jour_sem'] = wd; df['min_ny'] = mny
    # ---- oscillateurs de repli (sur HA, comme l'indicateur)
    hh = df['ha_h'].to_numpy(float) if 'ha_h' in df else h
    hl = df['ha_l'].to_numpy(float) if 'ha_l' in df else l
    if 'rsi' not in df:
        df['rsi'] = _rsi(hc)
    if 'cci' not in df:
        df['cci'] = _cci(hh, hl, hc)
    if 's_supertrend' not in df:
        df['s_supertrend'] = _supertrend(hh, hl, hc)
    if 's_vwap' not in df:
        tp = (hh + hl + hc) / 3
        v = df['v'].to_numpy(float) if 'v' in df else np.ones(n)
        v = np.where(np.isfinite(v) & (v > 0), v, 1.0)
        g2 = pd.DataFrame(dict(j=jour_ny, pv=tp * v, v=v)).groupby('j')
        vw = (g2['pv'].cumsum() / g2['v'].cumsum()).to_numpy()
        df['s_vwap'] = np.where(hc > vw, 1, -1)
    # ---- Feu : vrai Feu du DATASET si présent, sinon substitut (vote par le sens des états disponibles)
    if 'feu_l' in df and 'feu_s' in df:
        df['feu_net'] = (df['feu_l'].astype(float) - df['feu_s'].astype(float)) / 29.0
        df['feu_proxy'] = False
    else:
        votes = [np.where(df['hei_bleu'], 1.0, -1.0), np.where(df['au_dessus_ema50'], 1.0, -1.0),
                 np.sign(df['dip'].to_numpy(float) - df['dim'].to_numpy(float)),
                 np.where(df['rsi'] >= 50, 1.0, -1.0), np.where(df['cci'] >= 0, 1.0, -1.0),
                 df['s_supertrend'].to_numpy(float), df['s_vwap'].to_numpy(float)]
        if 'ha_o' in df:
            votes.append(np.where(df['ha_c'] > df['ha_o'], 1.0, -1.0))
        for k in ('trend_15', 'trend_60', 'trend_240', 'trend_1D', 'dash_15', 'dash_60', 'dash_240', 'dash_1D'):
            if k in df:
                x = df[k].to_numpy(float)
                votes.append(np.where(np.isnan(x), np.nan, 2 * x - 1))
        V = np.vstack(votes)
        df['feu_net'] = np.nanmean(V, axis=0)
        df['feu_proxy'] = True
    return df
