"""Candidats (union de tous les déclencheurs), variables au moment du signal, issues par le moteur.

Entrée : un DataFrame au format DATASET (voir donnees.py). Tout est calculé à la CLÔTURE de la barre signal ;
les variables de prix utilisent les colonnes *_causal si elles existent (source cache), sinon les vrais prix.

Variables « orientées » : toute variable directionnelle est multipliée par le sens (+1 long, -1 short), de sorte
que « positif = dans le sens du trade ». Les distances aux niveaux sont exprimées en ATR, orientées
(positif = niveau devant le trade, négatif = niveau derrière).
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
sys.path.insert(0, os.path.join(SB, 'moteur'))
import moteur as M  # noqa: E402

TYPES = ['sig_fort', 'sig_moyen', 'hei_flip', 'clx', 'tl', 'orb', 'sess', 'mon', 'det_rebond', 'det_cassure', 'div']


def _col(df, nom, defaut=np.nan):
    return df[nom].to_numpy(dtype=float) if nom in df.columns else np.full(len(df), defaut)


def _b(df, nom):
    return df[nom].fillna(False).to_numpy(dtype=bool) if nom in df.columns else np.zeros(len(df), bool)


def _jour_cme(idx):
    ch = idx.tz_convert('America/Chicago')
    return (ch + pd.Timedelta(hours=7)).normalize().tz_localize(None).to_numpy()


def _px(df):
    g = lambda k: _col(df, k + '_causal') if k + '_causal' in df.columns else _col(df, k)
    return g('o'), g('h'), g('l'), g('c'), (_col(df, 'atr_causal') if 'atr_causal' in df.columns else _col(df, 'atr'))


# ════════════════════════════════════════════════════════════════════════════
# Niveaux (stops/objectifs sur niveaux + distances)
# ════════════════════════════════════════════════════════════════════════════
def niveaux(df):
    """dict nom -> tableau de niveaux de prix connus à la clôture (vrais prix si disponibles)."""
    o, h, l, c, _ = _px(df)
    jour = _jour_cme(df.index)
    N = {}
    for k in ('zh_sup_h', 'zh_sup_b', 'zh_inf_h', 'zh_inf_b', 'zb_sup_h', 'zb_sup_b', 'zb_inf_h', 'zb_inf_b',
              'tl_res', 'tl_sup'):
        if k in df.columns:
            N[k] = _col(df, k)
    for k in ('as_h', 'as_l', 'ld_h', 'ld_l', 'us_h', 'us_l', 'mon_h', 'mon_l', 'orb_h', 'orb_l'):
        kv = k[:-2] + '_' + k[-1] + '_vrai'
        if kv in df.columns:
            N[k] = _col(df, kv)
        elif k in df.columns:
            N[k] = _col(df, k)
    for fam in ('pwr', 'pmr'):
        for k in ('dessus', 'dessous'):
            if '%s_%s' % (fam, k) in df.columns:
                N['%s_%s' % (fam, k)] = _col(df, '%s_%s' % (fam, k))
    # jour précédent (journée CME), pivots hebdo sur vrais prix si absents du dataset
    s = pd.DataFrame(dict(h=h, l=l, c=c, j=jour))
    dj = s.groupby('j').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last'))
    prev = dj.shift(1)
    N['pdh'] = prev['h'].reindex(jour).to_numpy(); N['pdl'] = prev['l'].reindex(jour).to_numpy()
    if 'pwr_dessus' not in N:
        wk = pd.DatetimeIndex(jour).to_period('W-SUN')
        s['w'] = wk
        dw = s.groupby('w').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).shift(1)
        hh, ll, cc = (dw[x].reindex(wk).to_numpy() for x in ('h', 'l', 'c'))
        p = (hh + ll + cc) / 3
        piv = np.column_stack([p, 2 * p - ll, 2 * p - hh, p + (hh - ll), p - (hh - ll)])
        N['pwr_dessus'] = np.where(piv > c[:, None], piv, np.inf).min(1)
        N['pwr_dessous'] = np.where(piv < c[:, None], piv, -np.inf).max(1)
        for k in ('pwr_dessus', 'pwr_dessous'):
            N[k] = np.where(np.isfinite(N[k]), N[k], np.nan)
    N['rond_dessous'] = np.floor(c / 100) * 100
    N['rond_dessus'] = N['rond_dessous'] + 100
    return N


# ════════════════════════════════════════════════════════════════════════════
# Déclencheurs
# ════════════════════════════════════════════════════════════════════════════
def _premiere_cassure(c, niv, jour, autorise=None):
    """1re clôture au-delà d'un niveau inchangé depuis la barre précédente (par niveau et par jour)."""
    n = len(c); up = np.zeros(n, bool); dn = np.zeros(n, bool)
    vu = set()
    for i in range(1, n):
        v, vp = niv[i], niv[i - 1]
        if not (np.isfinite(v) and v == vp) or (autorise is not None and not autorise[i]):
            continue
        if c[i] > v >= c[i - 1] and (jour[i], v, 1) not in vu:
            up[i] = True; vu.add((jour[i], v, 1))
        elif c[i] < v <= c[i - 1] and (jour[i], v, -1) not in vu:
            dn[i] = True; vu.add((jour[i], v, -1))
    return up, dn


def declencheurs(df):
    """dict type -> (long_bool, short_bool), calculés sur le HA (comme l'indicateur)."""
    n = len(df); jour = _jour_cme(df.index)
    hc = _col(df, 'ha_c'); hl = _col(df, 'ha_l'); hh = _col(df, 'ha_h')
    D = {}
    D['sig_fort'] = (_b(df, 'sig_long_fort'), _b(df, 'sig_short_fort'))
    D['sig_moyen'] = (_b(df, 'sig_long_moyen'), _b(df, 'sig_short_moyen'))
    D['hei_flip'] = (_b(df, 'hei_flip_haut'), _b(df, 'hei_flip_bas'))
    D['clx'] = (_b(df, 'clx_buy'), _b(df, 'clx_sell'))
    D['tl'] = (_b(df, 'tl_cassure_haut'), _b(df, 'tl_cassure_bas'))
    D['div'] = (_b(df, 'div_haus'), _b(df, 'div_bais'))
    # ORB : 1re clôture HA hors de la plage du jour
    oh, ol = _col(df, 'orb_h'), _col(df, 'orb_l')
    u1, _ = _premiere_cassure(hc, oh, jour); _, d1 = _premiere_cassure(hc, ol, jour)
    D['orb'] = (u1, d1)
    # sessions : 1re clôture au-delà du haut / bas de la dernière session TERMINÉE
    U = np.zeros(n, bool); Dn = np.zeros(n, bool)
    for k, drap in (('as', 'en_asie'), ('ld', 'en_londres'), ('us', 'en_us')):
        aut = ~_b(df, drap) if drap in df.columns else None
        u, _ = _premiere_cassure(hc, _col(df, k + '_h'), jour, aut)
        _, d = _premiere_cassure(hc, _col(df, k + '_l'), jour, aut)
        U |= u; Dn |= d
    D['sess'] = (U, Dn)
    if 'mon_cassure_haut' in df.columns:
        D['mon'] = (_b(df, 'mon_cassure_haut'), _b(df, 'mon_cassure_bas'))
    else:
        semaine = pd.DatetimeIndex(jour).to_period('W-SUN').astype(str).to_numpy()
        u, _ = _premiere_cassure(hc, _col(df, 'mon_h'), semaine)
        _, d = _premiere_cassure(hc, _col(df, 'mon_l'), semaine)
        D['mon'] = (u, d)
    # Detector : rebond (mèche dans la zone de la barre précédente, clôture au-delà) et cassure (mitigation)
    zib, zih = np.r_[np.nan, _col(df, 'zh_inf_b')[:-1]], np.r_[np.nan, _col(df, 'zh_inf_h')[:-1]]
    zsb, zsh = np.r_[np.nan, _col(df, 'zb_sup_b')[:-1]], np.r_[np.nan, _col(df, 'zb_sup_h')[:-1]]
    with np.errstate(invalid='ignore'):
        rl = (hl <= zih) & (hl >= zib) & (hc > zih)
        rs = (hh >= zsb) & (hh <= zsh) & (hc < zsb)
    D['det_rebond'] = (rl, rs)
    D['det_cassure'] = (_b(df, 'zb_mitigee'), _b(df, 'zh_mitigee'))
    return D


# ════════════════════════════════════════════════════════════════════════════
# Variables
# ════════════════════════════════════════════════════════════════════════════
GROUPES = {}      # nom de variable -> module (pour l'importance par groupe)


def _g(nom, groupe):
    GROUPES[nom] = groupe
    return nom


def variables_barres(df):
    """Variables par barre : (non orientées V, directionnelles W à multiplier par le sens)."""
    n = len(df)
    o, h, l, c, atr = _px(df)
    idx = df.index
    V, W = {}, {}
    a = np.where(atr > 0, atr, np.nan)
    V[_g('atr_rel', 'Volatilité')] = atr / pd.Series(atr).rolling(100, min_periods=30).mean().to_numpy()
    V[_g('atr_pct', 'Volatilité')] = atr / c * 1e4
    rng = h - l
    V[_g('range_atr', 'Volatilité')] = rng / a
    vol = _col(df, 'v')
    if np.isfinite(vol).sum() > 0.5 * n:
        V[_g('vol_rel', 'Volatilité')] = vol / pd.Series(vol).rolling(20, min_periods=10).mean().to_numpy()
    for k in (1, 4, 16, 48):
        W[_g('ret_%d' % k, 'Prix récent')] = (c - np.r_[np.full(k, np.nan), c[:-k]]) / a
    W[_g('corps_atr', 'Prix récent')] = (c - o) / a
    hi20 = pd.Series(h).rolling(20, min_periods=5).max().to_numpy()
    lo20 = pd.Series(l).rolling(20, min_periods=5).min().to_numpy()
    W[_g('pos_range20', 'Prix récent')] = ((c - lo20) / (hi20 - lo20) - 0.5) * 2
    ema50 = _col(df, 'ema50'); hc = _col(df, 'ha_c')
    W[_g('dist_ema50', 'Moyenator')] = (hc - ema50) / a
    W[_g('pente_ema50', 'Moyenator')] = (ema50 - np.r_[np.full(5, np.nan), ema50[:-5]]) / a
    V[_g('adx', 'ADX/DMI')] = _col(df, 'adx')
    W[_g('di_diff', 'ADX/DMI')] = _col(df, 'dip') - _col(df, 'dim')
    W[_g('rsi_c', 'Oscillateurs')] = _col(df, 'rsi') - 50
    W[_g('cci', 'Oscillateurs')] = _col(df, 'cci')
    if 'score' in df.columns:
        V[_g('score_sig', 'Signator')] = _col(df, 'score')
    bull = _b(df, 'hei_bleu')
    W[_g('hei_bleu', 'Heishinator')] = np.where(bull, 1.0, -1.0)
    run = np.ones(n)
    for i in range(1, n):
        run[i] = run[i - 1] + 1 if bull[i] == bull[i - 1] else 1
    V[_g('hei_age', 'Heishinator')] = np.minimum(run, 50)
    for u in ('3', '5', '15', '60', '240', '1D'):
        for pre, grp in (('trend', 'TREND multi-UT'), ('dash', 'Dashator multi-UT'), ('hei', 'Heishinator')):
            k = '%s_%s' % (pre, u)
            if k in df.columns and not (pre == 'hei' and u in ('3', '5', '15')):
                x = _col(df, k)
                W[_g(k, grp)] = np.where(np.isfinite(x), 2 * x - 1, np.nan)
        if 'str_' + u in df.columns:
            W[_g('str_' + u, 'TREND multi-UT')] = _col(df, 'str_' + u) - 2
    if 'feu_l' in df.columns:
        W[_g('feu_net', 'Feu')] = _col(df, 'feu_l') - _col(df, 'feu_s')
        V[_g('feu_tot', 'Feu')] = _col(df, 'feu_l') + _col(df, 'feu_s')
    for k in [x for x in df.columns if x.startswith('v_') or x.startswith('s_')]:
        if k in ('v',):
            continue
        W[_g('voix_' + k, 'Feu' if k.startswith('v_') else 'SIGNAL')] = _col(df, k)
    # niveaux : distance orientée (niveau - close) / ATR -> W (positif = au-dessus = devant un long)
    N = niveaux(df)
    fam = {'zh_sup_b': 'Detector', 'zh_inf_h': 'Detector', 'zb_sup_b': 'Detector', 'zb_inf_h': 'Detector',
           'tl_res': 'Trendlines', 'tl_sup': 'Trendlines', 'as_h': 'Sessions', 'as_l': 'Sessions',
           'ld_h': 'Sessions', 'ld_l': 'Sessions', 'us_h': 'Sessions', 'us_l': 'Sessions', 'mon_h': 'Monday',
           'mon_l': 'Monday', 'orb_h': 'ORB', 'orb_l': 'ORB', 'pwr_dessus': 'Pivots', 'pwr_dessous': 'Pivots',
           'pmr_dessus': 'Pivots', 'pmr_dessous': 'Pivots', 'pdh': 'Jour précédent', 'pdl': 'Jour précédent',
           'rond_dessus': 'Ronds', 'rond_dessous': 'Ronds'}
    for k, grp in fam.items():
        if k in N:
            d = (N[k] - c) / a
            W[_g('d_' + k, grp)] = np.clip(d, -20, 20)
    V[_g('dans_zh', 'Detector')] = _b(df, 'dans_zh').astype(float)
    V[_g('dans_zb', 'Detector')] = _b(df, 'dans_zb').astype(float)
    V[_g('tl_res_active', 'Trendlines')] = np.isfinite(N['tl_res']).astype(float) if 'tl_res' in N else np.full(n, np.nan)
    # temps
    ny = idx.tz_convert('America/New_York')
    hn = ny.hour + ny.minute / 60
    V[_g('heure_sin', 'Heure/séance')] = np.sin(2 * np.pi * hn / 24)
    V[_g('heure_cos', 'Heure/séance')] = np.cos(2 * np.pi * hn / 24)
    par = idx.tz_convert('Europe/Paris'); hp = par.hour + par.minute / 60
    V[_g('seance_londres', 'Heure/séance')] = ((hp >= 8) & (hp < 14.5)).astype(float)
    V[_g('seance_us', 'Heure/séance')] = ((hn >= 9.5) & (hn < 16)).astype(float)
    V[_g('seance_nuit', 'Heure/séance')] = ((hp >= 0) & (hp < 8)).astype(float)
    V[_g('jour_sem', 'Heure/séance')] = ny.dayofweek.to_numpy().astype(float)
    V[_g('blackout', 'Heure/séance')] = _b(df, 'blackout').astype(float)
    return V, W


def candidats(df, nom_serie='', instrument='MNQ'):
    """Table des candidats : une ligne par (barre, sens) où au moins un déclencheur est vrai."""
    D = declencheurs(df)
    V, W = variables_barres(df)
    n = len(df)
    lignes = []
    for d, j in ((1, 0), (-1, 1)):
        flags = {t: D[t][j] if t in D else np.zeros(n, bool) for t in TYPES}
        anyf = np.zeros(n, bool)
        for t in TYPES:
            anyf |= flags[t]
        anyf[:150] = False                    # chauffe des indicateurs
        ii = np.flatnonzero(anyf)
        if not len(ii):
            continue
        tab = pd.DataFrame({'i': ii, 'sens': d})
        for t in TYPES:
            tab[_g('trig_' + t, 'Type de déclencheur')] = flags[t][ii].astype(float)
        tab[_g('n_trig', 'Type de déclencheur')] = sum(flags[t][ii].astype(float) for t in TYPES)
        for k, x in V.items():
            tab[k] = np.asarray(x, float)[ii]
        for k, x in W.items():
            tab[k] = np.asarray(x, float)[ii] * d
        lignes.append(tab)
    C = pd.concat(lignes, ignore_index=True).sort_values(['i', 'sens']).reset_index(drop=True)
    GROUPES['sens'] = 'Sens'
    C['sens_long'] = (C['sens'] == 1).astype(float)
    C['t_signal'] = df.index[C['i'].to_numpy()]
    C['serie'] = nom_serie
    C['instrument'] = instrument
    GROUPES['est_nq'] = 'Instrument'
    C['est_nq'] = float(instrument in ('MNQ', 'NQ'))
    C['jour'] = _jour_cme(df.index)[C['i'].to_numpy()]
    return C


# ════════════════════════════════════════════════════════════════════════════
# Gestions de référence et issues isolées (chaque candidat seul dans le moteur)
# ════════════════════════════════════════════════════════════════════════════
def gestions(df, instrument):
    N = niveaux(df)
    noms = list(N)
    base = dict(instrument=instrument, heure_sortie='15:59')
    return {
        'A15R2': dict(base, stop={'mode': 'atr', 'k': 1.5}, objectif={'mode': 'R', 'k': 2.0}),
        'A1R1': dict(base, stop={'mode': 'atr', 'k': 1.0}, objectif={'mode': 'R', 'k': 1.0}),
        'NIV': dict(base, stop={'mode': 'niveau', 'long': {k: N[k] for k in noms}, 'short': {k: N[k] for k in noms},
                                'marge_ticks': 2, 'min_atr': 0.5, 'max_atr': 3.0, 'choix': 'proche', 'repli_k': 1.5},
                    objectif={'mode': 'niveau', 'long': {k: N[k] for k in noms}, 'short': {k: N[k] for k in noms},
                              'ratio_min': 1.0, 'si_absent': ('R', 2.0)}),
    }


def _tranche_gestion(g, a, b):
    g = dict(g)
    for cle in ('stop', 'objectif'):
        cfg = dict(g[cle])
        for s in ('long', 'short'):
            if isinstance(cfg.get(s), dict):
                cfg[s] = {k: v[a:b] for k, v in cfg[s].items()}
        g[cle] = cfg
    return g


def issues_isolees(df, C, G, ut_min=15):
    """Pour chaque candidat et chaque gestion : r, pnl, sortie_t du trade pris SEUL (pas d'interaction)."""
    W = int(math.ceil(26 * 60 / ut_min)) + 3
    px = df[['o', 'h', 'l', 'c', 'atr']].rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close'})
    out = {}
    for gn, g in G.items():
        r = np.full(len(C), np.nan); pnl = np.full(len(C), np.nan); st = [pd.NaT] * len(C); risk = np.full(len(C), np.nan)
        for q, (i, d) in enumerate(zip(C['i'].to_numpy(), C['sens'].to_numpy())):
            b = min(i + W, len(df))
            sl = px.iloc[i:b]
            sig = np.zeros(len(sl), bool); sig[0] = True
            gg = _tranche_gestion(g, i, b)
            T = M.backtest(sl, long=sig if d == 1 else None, short=sig if d == -1 else None, gestion=gg)
            if len(T):
                r[q] = T['r'].iloc[0]; pnl[q] = T['pnl_usd'].iloc[0]; st[q] = T['sortie_t'].iloc[0]
                risk[q] = T['risque_usd'].iloc[0]
        out[gn] = pd.DataFrame({'r_' + gn: r, 'pnl_' + gn: pnl, 'sortie_' + gn: st, 'risque_' + gn: risk})
    return pd.concat([out[k] for k in G], axis=1)
