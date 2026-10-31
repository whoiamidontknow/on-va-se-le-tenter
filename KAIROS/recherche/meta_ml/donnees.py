"""Accès aux données du méta-modèle ML — TOUT l'accès aux données passe par `charger_series()`.

Passage au DATASET : `charger_series(source='dataset')` (ou variable d'environnement META_ML_SOURCE=dataset).
Chaque série est renvoyée au format des colonnes de `dataset/charger.py` (noms identiques), coupée au
développement par `moteur.charger_recherche` (le scellé n'est JAMAIS lu ici).

Source 'cache' (provisoire) : séries 15 min de tools/strategie/cache_series.pkl (MES sept.-oct., NQZ sept.-oct.,
MES1 avr.-juil.), converties au format DATASET par `cache_vers_dataset` :
  - o/h/l/c/atr = vrais prix reconstitués (recon.reconstruct, LISSÉS : meilleure estimation, servent au MOTEUR) ;
  - c_causal/h_causal/l_causal/atr_causal = reconstitution CAUSALE (passe avant seule) : seules ces colonnes
    servent aux VARIABLES, pour qu'aucune information de la barre suivante ne fuie (leçon de
    tools/strategie/correlations/modele) ;
  - modules (Signator, Heishinator, Climax, trendlines, Detector, sessions, Monday) calculés sur HA (causal) ;
  - TREND/Dashator 60 et 240 min agrégés depuis les vrais prix CAUSAUX, bougie HTF clôturée seulement.
Colonnes du DATASET absentes du cache (Feu, voix SuperTrader/SIGNAL, STRENGTH, score…) : simplement absentes ;
le module de variables utilise ce qui existe.
"""
from __future__ import annotations

import datetime
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
RACINE = os.path.dirname(SB)
STRAT = os.path.join(RACINE, 'tools', 'strategie')
for p in (os.path.join(SB, 'moteur'), os.path.join(SB, 'dataset')):
    if p not in sys.path:
        sys.path.insert(0, p)
import moteur as M  # noqa: E402

DOSSIER_DATASET = os.path.expanduser('~/ERGON/KAIROS-data')
CACHE_DF = os.path.join(ICI, 'cache', 'series_cache.pkl')
INSTR = {'MES': 'MES', 'MES1': 'MES', 'NQZ': 'MNQ', 'MNQ1!': 'MNQ', 'MES1!': 'MES', 'NQ1!': 'MNQ',
         'MESZ2026': 'MES', 'NQZ2026': 'MNQ'}


# ════════════════════════════════════════════════════════════════════════════
# POINT D'ACCÈS UNIQUE
# ════════════════════════════════════════════════════════════════════════════
def charger_series(source=None, ut='15'):
    """-> liste de dicts {nom, instrument, ut_min, df} ; df = DÉVELOPPEMENT seulement (75 %)."""
    source = source or os.environ.get('META_ML_SOURCE', 'cache')
    if source == 'dataset':
        from charger import charger
        out = []
        for f in sorted(glob.glob(os.path.join(DOSSIER_DATASET, '*.csv'))):
            full = charger(f)
            if str(full.attrs.get('ut')) != str(ut):
                continue
            sym = str(full.attrs.get('symbole'))
            dev = M.charger_recherche(full, agent='meta_ml')
            out.append(dict(nom='%s_%s' % (sym, ut), instrument=INSTR.get(sym, 'MNQ'), ut_min=int(ut), df=dev))
        if not out:
            raise FileNotFoundError('aucun export DATASET %s min dans %s' % (ut, DOSSIER_DATASET))
        return out
    if source != 'cache':
        raise ValueError(source)
    if os.path.exists(CACHE_DF):
        full = pickle.load(open(CACHE_DF, 'rb'))
    else:
        full = _construire_cache()
        os.makedirs(os.path.dirname(CACHE_DF), exist_ok=True)
        pickle.dump(full, open(CACHE_DF, 'wb'))
    return [dict(s, df=M.charger_recherche(s['df'], agent='meta_ml')) for s in full]


# ════════════════════════════════════════════════════════════════════════════
# Conversion cache_series -> format DATASET
# ════════════════════════════════════════════════════════════════════════════
def _construire_cache():
    sys.path.insert(0, STRAT)
    sys.path.insert(0, os.path.join(RACINE, 'tools', 'ephore_api'))
    S_all = pickle.load(open(os.path.join(STRAT, 'cache_series.pkl'), 'rb'))
    choix = [(s['sym'], s['n']) for s in S_all if s['tf'] == '15' and s['n'] > 1000]   # MES, MES1 avr-juil, NQZ
    out = []
    for s in S_all:
        if (s['sym'], s['n']) in choix and s['tf'] == '15':
            df = cache_vers_dataset(s)
            out.append(dict(nom='%s_15_%s' % (s['sym'], s['T'][0].strftime('%m%d')), instrument=INSTR[s['sym']],
                            ut_min=15, df=df))
    return out


def _recon_causal(S, tick=0.25):
    """recon.reconstruct sans la passe arrière (copie de correlations/modele/dataset.py)."""
    import recon
    bars = [dict(o=S['o'][i], h=S['h'][i], l=S['l'][i], c=S['c'][i]) for i in range(S['n'])]
    n = len(bars); g = tick; eps = tick / 10; breaks = S['brk']
    boxes = [recon._box(b, eps) for b in bars]
    F = [None] * n; out = []
    for i in range(n):
        fr = recon._free(boxes[i]) or (bars[i]['l'], bars[i]['h'])
        if i == 0 or breaks[i] or F[i - 1] is None:
            F[i] = fr
        else:
            r = recon._prop(F[i - 1][0] - g, F[i - 1][1] + g, boxes[i]); F[i] = r if r is not None else fr
        lo, hi = F[i]; out.append(lo + recon.pos_dir(bars, i) * (hi - lo))
    ro, rh, rl, rc = [], [], [], []
    for i in range(n):
        K, Hlo, Hhi, Llo, Lhi = boxes[i]; c = out[i]
        o = out[i - 1] if (i > 0 and not breaks[i]) else K / 4
        hk, lk = Hlo == Hhi, Llo == Lhi; h, l = Hlo, Llo
        if hk and not lk:
            l = min(max(K - o - c - h, Llo), min(Lhi, o, c))
        elif lk and not hk:
            h = max(min(K - o - c - l, Hhi), max(Hlo, o, c))
        elif not hk and not lk:
            rest = K - o - c
            h = max(min(rest / 2 + (Hhi - Lhi) / 4, Hhi), Hlo, o, c); l = min(max(rest - h, Llo), Lhi, o, c)
        o = min(max(o, l), h); c = min(max(c, l), h)
        ro.append(o); rh.append(h); rl.append(l); rc.append(c)
    return np.array(ro), np.array(rh), np.array(rl), np.array(rc)


def _ema(x, p):
    return pd.Series(x).ewm(span=p, adjust=False).mean().to_numpy()


def _htf(T, tfm, ro, rh, rl, rc, m):
    """TREND / Dashator / Heishinator de la dernière bougie de m minutes CLÔTURÉE à la clôture de chaque barre,
    depuis les vrais prix CAUSAUX. NaN avant 50 bougies HTF."""
    NY = __import__('zoneinfo').ZoneInfo('America/New_York')
    n = len(T)

    def key(t):
        if m >= 1440:
            d = t.astimezone(NY) + datetime.timedelta(hours=6)
            return (d.year, d.month, d.day)
        return int(t.timestamp() // 60) // m
    bars = []
    jof = np.zeros(n, int)
    for i in range(n):
        k = key(T[i])
        if bars and bars[-1][0] == k:
            b = bars[-1]; bars[-1] = (k, b[1], max(b[2], rh[i]), min(b[3], rl[i]), rc[i], i)
        else:
            bars.append((k, ro[i], rh[i], rl[i], rc[i], i))
        jof[i] = len(bars) - 1
    ha = []
    for j, b in enumerate(bars):
        hc = (b[1] + b[2] + b[3] + b[4]) / 4
        ho = (b[1] + b[4]) / 2 if j == 0 else (ha[-1][0] + ha[-1][1]) / 2
        ha.append((ho, hc))
    hc = np.array([x[1] for x in ha]); e50 = _ema(hc, 50)
    s4 = np.array([(b[1] + b[2] + b[3] + b[4]) / 4 for b in bars])
    bull = _ema(s4, 4) > _ema(s4, 32)
    trend = np.full(n, np.nan); dash = np.full(n, np.nan); hei = np.full(n, np.nan)
    for i in range(n):
        j = jof[i]; k = bars[j][0]
        if m >= 1440:
            fin = (i + 1 < n and key(T[i + 1]) != k)
        else:
            fin = (T[i].timestamp() // 60 + tfm) >= (k + 1) * m
        cur = j if fin else j - 1
        if cur >= 32:
            hei[i] = float(bull[cur]); dash[i] = float(ha[cur][1] > ha[cur][0])
        if cur >= 50:
            trend[i] = float(hc[cur] > e50[cur])
    return trend, dash, hei


def _rsi(x, p=14):
    d = np.diff(x, prepend=x[0])
    up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / p, adjust=False).mean()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / p, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).to_numpy()


def _cci(x, p=30):
    s = pd.Series(x); ma = s.rolling(p).mean()
    md = s.rolling(p).apply(lambda w: np.mean(np.abs(w - w.mean())), raw=True)
    return ((s - ma) / (0.015 * md)).to_numpy()


def cache_vers_dataset(S):
    n = S['n']; T = S['T']
    A = lambda k: np.array([np.nan if v is None else v for v in S[k]], float)
    idx = pd.DatetimeIndex(T).tz_convert('Europe/Paris')
    d = dict(ha_o=A('o'), ha_h=A('h'), ha_l=A('l'), ha_c=A('c'), v=A('v'),
             o=A('ro'), h=A('rh'), l=A('rl'), c=A('rc'), atr=A('ratr'),
             ema50=A('e50'), ema60=A('e60'), adx=A('adx'), dip=A('dip'), dim=A('dim'))
    co, ch, cl, cc = _recon_causal(S)
    d.update(o_causal=co, h_causal=ch, l_causal=cl, c_causal=cc, atr_causal=M.atr_wilder(ch, cl, cc))
    bull = np.array(S['bull'], bool)
    d['hei_bleu'] = bull
    d['hei_flip_haut'] = bull & ~np.r_[True, bull[:-1]]
    d['hei_flip_bas'] = ~bull & np.r_[False, bull[:-1]]
    d['au_dessus_ema50'] = d['ha_c'] > d['ema50']
    sig = S['sig']
    for nom, f, s_ in (('sig_long_fort', 'F', 1), ('sig_short_fort', 'F', -1), ('sig_long_moyen', 'M', 1),
                       ('sig_short_moyen', 'M', -1)):
        d[nom] = np.array([x is not None and x[0] == f and x[1] == s_ for x in sig])
    clx = np.array(S['clx']); d['clx_buy'] = clx == 1; d['clx_sell'] = clx == -1
    d['tl_cassure_haut'] = np.array(S['rB'], bool); d['tl_cassure_bas'] = np.array(S['sB'], bool)
    d['zh_mitigee'] = np.array(S['mitB'], bool); d['zb_mitigee'] = np.array(S['mitS'], bool)
    # zones Detector : la plus proche au-dessus / au-dessous de la clôture HA
    for pre, Z in (('zh', S['Zb']), ('zb', S['Zs'])):
        sh, sb, ih, ib = (np.full(n, np.nan) for _ in range(4)); dans = np.zeros(n, bool)
        for i in range(n):
            c = d['ha_c'][i]; best_s = best_i = None
            for top, btm in (Z[i] or []):
                if btm <= c <= top:
                    dans[i] = True
                if btm > c and (best_s is None or btm < best_s[1]):
                    best_s = (top, btm)
                if top < c and (best_i is None or top > best_i[0]):
                    best_i = (top, btm)
            if best_s:
                sh[i], sb[i] = best_s
            if best_i:
                ih[i], ib[i] = best_i
        d[pre + '_sup_h'], d[pre + '_sup_b'], d[pre + '_inf_h'], d[pre + '_inf_b'] = sh, sb, ih, ib
        d['dans_' + pre] = dans
    # sessions (dernière session terminée, HA) + drapeaux
    for k, nom in (('AS', 'as'), ('LD', 'ld'), ('US', 'us')):
        d[nom + '_h'] = np.array([np.nan if x is None else x[0] for x in S['SL'][k]])
        d[nom + '_l'] = np.array([np.nan if x is None else x[1] for x in S['SL'][k]])
    d['mon_h'] = np.array([np.nan if x is None else x[0] for x in S['MHL']])
    d['mon_l'] = np.array([np.nan if x is None else x[1] for x in S['MHL']])
    d['monday_pret'] = np.isfinite(d['mon_h'])
    # ORB 09:30-09:45 NY (bougie HA du graphique 15 min), remis à zéro chaque jour
    ny = idx.tz_convert('America/New_York')
    mny = ny.hour * 60 + ny.minute
    jour = ny.date
    orb_h = np.full(n, np.nan); orb_l = np.full(n, np.nan); cur = None; jc = None; forme = False
    for i in range(n):
        if jour[i] != jc:
            jc = jour[i]; cur = None; forme = False
        if 570 <= mny[i] < 585:
            cur = (d['ha_h'][i], d['ha_l'][i]) if cur is None else (max(cur[0], d['ha_h'][i]), min(cur[1], d['ha_l'][i]))
            if mny[i] + S['tfm'] >= 585:
                forme = True          # plage formée à la clôture de sa dernière barre
        if forme and cur is not None and mny[i] < 960:
            orb_h[i], orb_l[i] = cur
    d['orb_h'], d['orb_l'] = orb_h, orb_l
    d['orb_forme'] = np.isfinite(orb_h)
    # oscillateurs (HA), multi-unités (vrais prix causaux)
    d['rsi'] = _rsi(d['ha_c'], 14); d['cci'] = _cci(d['ha_c'], 30)
    d['trend_15'] = d['au_dessus_ema50'].astype(float)
    for m in (60, 240):
        tr, da, he = _htf(T, S['tfm'], co, ch, cl, cc, m)
        d['trend_%d' % m], d['dash_%d' % m], d['hei_%d' % m] = tr, da, he
    df = pd.DataFrame(d, index=idx)
    df.index.name = 'time'
    df['blackout'] = [bool(__import__('features').news(t, S['tfm'])) for t in T]
    return df


if __name__ == '__main__':
    for s in charger_series():
        df = s['df']
        print(s['nom'], s['instrument'], len(df), df.index[0], df.index[-1], df.shape[1], 'colonnes')
