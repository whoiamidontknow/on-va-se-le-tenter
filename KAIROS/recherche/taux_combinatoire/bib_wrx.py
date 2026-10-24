"""Bibliothèque WRX : déclencheurs et filtres de STRATEGIE_V1.pine, géométries « à fort taux », tables d'issues.

Table d'issues : pour un jeu et une géométrie, l'issue (gagnant ?, R, $, barre de fin) d'un trade qui serait
pris sur CHAQUE barre, dans chaque sens, calculée par le MOTEUR COMMUN (`moteur.backtest`) : on lance le moteur
avec un signal toutes les K barres (K > une journée, donc jamais deux trades en même temps), K fois en décalant.
Un trade du moteur ne dépend que de sa barre de signal : la table est donc exacte. Les trades d'une variante =
les lignes de la table aux barres de ses signaux, avec la règle « une position à la fois » du moteur
(signal ignoré tant que k < k_libre). Vérifié contre `moteur.backtest` sur les signaux réels (verif_table).
Placebo : `moteur.reference_hasard` tire, pour chaque signal, une barre au hasard de même heure (Paris, heure de
clôture de la barre signal) et de même sens ; sa moyenne exacte est donc la moyenne de la table sur ces barres.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from donnees_wrx import M

# ════════════════════════════════════════════════════════════════════════════════════════
# DÉCLENCHEURS (clés du préréglage Pine entre parenthèses)
# ════════════════════════════════════════════════════════════════════════════════════════
DECL = {
    'sig_fort': ('sig_long_fort', 'sig_short_fort'),        # sig=1;sigNiv=Fort seulement
    'hei_flip': ('hei_flip_haut', 'hei_flip_bas'),          # hei=1
    'tl': ('tl_cassure_haut', 'tl_cassure_bas'),            # tl=1
    'lvl': ('lvl_up', 'lvl_dn'),                            # lvl=1 (sessions + Monday)
    'clx': ('clx_buy', 'clx_sell'),                         # clx=1
}
DECL_PINE = {'sig_fort': 'sig=1;sigNiv=Fort seulement', 'hei_flip': 'hei=1', 'tl': 'tl=1', 'lvl': 'lvl=1',
             'clx': 'clx=1'}
TOUS = ('sig_fort', 'hei_flip', 'tl', 'lvl', 'clx')
DECLENCHEURS = list(DECL) + ['tous']
SENS = ('long', 'short', 'les_deux')


def declencheur(df, nom):
    """(L, S) bruts d'un déclencheur (ou de l'union « tous »)."""
    noms = TOUS if nom == 'tous' else (nom,)
    L = np.zeros(len(df), bool); S = np.zeros(len(df), bool)
    for k in noms:
        a, b = DECL[k]
        L |= df[a].to_numpy(bool); S |= df[b].to_numpy(bool)
    return L, S


# ════════════════════════════════════════════════════════════════════════════════════════
# FILTRES, par groupe (au plus un filtre par groupe dans une combinaison)
# ════════════════════════════════════════════════════════════════════════════════════════
def _plage(df, a, b):
    m = df['min_paris'].to_numpy()          # heure d'OUVERTURE de la bougie signal (comme time(…, session))
    ok = (m >= a) & (m < b) if a < b else (m >= a) | (m < b)
    return ok, ok


def _feu(s):
    return lambda df: (df['feu_pL'].to_numpy() >= s, df['feu_pS'].to_numpy() >= s)


def _trend(k):
    def f(df):
        if k not in df:
            return None
        x = df[k].to_numpy(float)
        return np.nan_to_num(x) > 0.5, np.where(np.isnan(x), False, x < 0.5)   # Pine : tr_okS = not trUp
    return f


def _adx(s):
    return lambda df: (lambda m: (m, m))(np.nan_to_num(df['adx'].to_numpy(float)) >= s)


def _det(k):
    """Pine f_det_bloque : pas de long si une zone baissière est à moins de k ATR au-dessus (ou si dedans)."""
    def f(df):
        c = df['ha_c'].to_numpy(float); a = df['atr'].to_numpy(float)
        with np.errstate(invalid='ignore'):
            blL = df['dans_zb'].to_numpy(bool) | ((df['zb_sup_b'].to_numpy(float) - c) < k * a)
            blS = df['dans_zh'].to_numpy(bool) | ((c - df['zh_inf_h'].to_numpy(float)) < k * a)
        return ~blL, ~blS
    return f


def _ema(df):
    x = df['au_dessus_ema50'].to_numpy(bool)
    return x, ~x


def _clx(df):
    d = df['clx_dernier'].to_numpy(float)
    return d != -1, d != 1


def _bo(df):
    ok = ~df['blackout'].to_numpy(bool)
    return ok, ok


GROUPES = {
    'feu': {'feu50': _feu(50), 'feu60': _feu(60), 'feu70': _feu(70)},
    'tr': {'tr60': _trend('trend_60'), 'tr240': _trend('trend_240')},
    'ema': {'ema50': _ema},
    'adx': {'adx20': _adx(20), 'adx25': _adx(25)},
    'det': {'det1': _det(1.0), 'det2': _det(2.0)},
    'clx': {'clxpas': _clx},
    'bo': {'bo': _bo},
    'hr': {'nuit0_8': lambda df: _plage(df, 0, 480), 'ldn8_1430': lambda df: _plage(df, 480, 870),
           'horsldn1430_8': lambda df: _plage(df, 870, 480), 'us1530_22': lambda df: _plage(df, 930, 1320)},
}
FILTRE_GROUPE = {f: g for g, d in GROUPES.items() for f in d}
FILTRE_PINE = {
    'feu50': 'feu=1;feuMode=Part dans le sens ≥ seuil;feuSeuil=50',
    'feu60': 'feu=1;feuMode=Part dans le sens ≥ seuil;feuSeuil=60',
    'feu70': 'feu=1;feuMode=Part dans le sens ≥ seuil;feuSeuil=70',
    'tr60': 'tr=1', 'tr240': 'tr=1', 'ema50': 'ema=1', 'adx20': 'adx=1;adxMin=20', 'adx25': 'adx=1;adxMin=25',
    'det1': 'det=1;detK=1', 'det2': 'det=1;detK=2', 'clxpas': 'clxF=1;clxAge=0', 'bo': 'bo=1',
    'nuit0_8': 'hr=1;hr1On=1;hr1=0000-0800;hr2On=0', 'ldn8_1430': 'hr=1;hr1On=1;hr1=0800-1430;hr2On=0',
    'horsldn1430_8': 'hr=1;hr1On=1;hr1=1430-0800;hr2On=0', 'us1530_22': 'hr=1;hr1On=1;hr1=1530-2200;hr2On=0',
}


def combinaisons(max_f=3):
    """Toutes les combinaisons de 0 à max_f filtres, au plus un par groupe (tuples triés)."""
    gs = list(GROUPES)
    out = [()]
    for k in range(1, max_f + 1):
        for gg in itertools.combinations(gs, k):
            for fs in itertools.product(*[list(GROUPES[g]) for g in gg]):
                out.append(tuple(fs))
    return out


def masques_filtres(df):
    """{filtre: (okL, okS)} ; None si la colonne manque (ex. tr60 sur un graphique 60 min)."""
    out = {}
    for g, d in GROUPES.items():
        for f, fn in d.items():
            r = fn(df)
            if r is not None:
                out[f] = (np.asarray(r[0], bool), np.asarray(r[1], bool))
    return out


# ════════════════════════════════════════════════════════════════════════════════════════
# GÉOMÉTRIES
# ════════════════════════════════════════════════════════════════════════════════════════
STOPS = (1.0, 1.5, 2.0, 3.0)
OBJECTIFS = (0.5, 0.75, 1.0, 1.5)
EXTRAS = ('rien', 'be', 'hei', 'temps')
BE_R = 0.5                                     # break-even : stop à l'entrée + 1 tick dès +0,5 R
TEMPS_MIN = 120                                # sortie temporelle : après 2 h de position


def geometries():
    out = []
    for s in STOPS:
        for o in OBJECTIFS:
            for x in EXTRAS:
                if x == 'be' and o < 1.0:
                    continue
                out.append((s, o, x))
    return out


def nom_geo(g):
    s, o, x = g
    return 'SL %g ATR, TP %gR%s' % (s, o, {'rien': '', 'be': ', BE %gR' % BE_R, 'hei': ', sortie Hei',
                                            'temps': ', sortie %d min' % TEMPS_MIN}[x])


def gestion(df, instrument, g, ut):
    s, o, x = g
    G = dict(instrument=instrument, stop={'mode': 'atr', 'k': s}, objectif={'mode': 'R', 'k': o})
    if x == 'be':
        G['break_even'] = {'R': BE_R, 'ticks': 1}
    elif x == 'hei':
        G['sortie_signal'] = {'long': df['hei_flip_bas'].to_numpy(bool), 'short': df['hei_flip_haut'].to_numpy(bool)}
    elif x == 'temps':
        G['sortie_barres'] = max(1, TEMPS_MIN // ut)
    return G


def geo_pine(g):
    s, o, x = g
    t = 'stop=ATR × k;atrK=%g;tp=En R;tpR=%g;trail=Aucun;oppArr=0;fin=0;pf=1;part=0' % (s, o)
    t += ';be=1;beR=%g' % BE_R if x == 'be' else ';be=0'
    t += ';oppHei=1' if x == 'hei' else ';oppHei=0'
    return t


# ════════════════════════════════════════════════════════════════════════════════════════
# TABLE D'ISSUES (moteur commun)
# ════════════════════════════════════════════════════════════════════════════════════════
def table_issues(df, instrument, g, ut):
    """dict de tableaux (2, n) [0 = long, 1 = short] : ok, gagne, r, pnl, klibre ; + heure, jour (n,)."""
    n = len(df)
    G = gestion(df, instrument, g, ut)
    K = int(1440 // ut) + 3
    ar = np.arange(n)
    ok = np.zeros((2, n), bool); r = np.zeros((2, n)); pnl = np.zeros((2, n)); kl = np.zeros((2, n), np.int64)
    for di, cle in enumerate(('long', 'short')):
        for dec in range(K):
            sig = (ar % K) == dec
            T = M.backtest(df, **{cle: sig}, gestion=G, details=True)
            if not len(T):
                continue
            i = T['i_signal'].to_numpy(); ke = T['k_entree'].to_numpy(); ks = T['k_sortie'].to_numpy()
            ouv = T['barres'].to_numpy() == (ks - ke)
            ok[di, i] = True
            r[di, i] = T['r'].to_numpy(); pnl[di, i] = T['pnl_usd'].to_numpy()
            kl[di, i] = np.where(ouv, ks - 1, ks)
    b = M.barres(df)
    heure = pd.DatetimeIndex(pd.to_datetime(b.t_clo, unit='ns', utc=True)).tz_convert('Europe/Paris').hour.to_numpy()
    return dict(ok=ok, gagne=pnl > 0, r=r, pnl=pnl, klibre=kl, heure=heure, jour=b.jour_cme())


def glouton(idx, d, kl):
    """Règle « une position à la fois » du moteur. idx : barres signal triées (entrée possible), d : 0/1."""
    garde = np.zeros(len(idx), bool)
    k_libre = -1
    il = idx.tolist(); dl = d.tolist()
    for t in range(len(il)):
        i = il[t]
        if i >= k_libre:
            garde[t] = True
            k_libre = kl[dl[t], i]
    return garde


def placebo_moyen(tab, masque_jours=None):
    """Moyennes (gagne, r) de la table par (sens, heure) : ce qu'un tirage au hasard de même heure et même sens
    donne en moyenne. masque_jours : barres candidates (période). Repli : toutes heures."""
    ok = tab['ok'].copy()
    if masque_jours is not None:
        ok &= masque_jours[None, :]
    h = tab['heure']
    pw = np.zeros((2, 24)); pr = np.zeros((2, 24)); pq = np.zeros((2, 24))
    for d in range(2):
        m = ok[d]
        cnt = np.bincount(h[m], minlength=24).astype(float)
        sw = np.bincount(h[m], weights=tab['gagne'][d][m].astype(float), minlength=24)
        sr = np.bincount(h[m], weights=tab['r'][d][m], minlength=24)
        tot = max(cnt.sum(), 1.0)
        gw = sw.sum() / tot; gr = sr.sum() / tot
        with np.errstate(invalid='ignore', divide='ignore'):
            pw[d] = np.where(cnt > 0, sw / cnt, gw); pr[d] = np.where(cnt > 0, sr / cnt, gr)
        pq[d] = cnt
    return pw, pr, pq
