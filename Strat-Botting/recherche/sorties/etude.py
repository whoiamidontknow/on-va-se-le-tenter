"""Agent « Sorties et protection » (SOR) — quelle gestion de trade pour la propfirm ?

    ~/venv-quant/bin/python etude.py [etapes]      # etapes parmi prep A B C D E (défaut : tout)

Données : donnees_sor.charger_series() (un seul point d'accès ; SOR_SOURCE=dataset pour le DATASET),
puis moteur.charger_recherche (développement = 75 % le plus ancien de chaque série, scellé jamais lu).
Moteur commun (Strat-Botting/moteur) et simulateur propfirm commun (Strat-Botting/propfirm), non modifiés.

Étapes (A2 entre A et B : placebo des meilleurs stops sur niveau, qui décide des stops gardés pour B)
  prep  séries de développement + déclencheurs -> resultats/series_dev_<UT>.pkl
  A     STOPS : ATR fixes (1 à 3) contre stop derrière le niveau le plus proche de chaque famille (marge,
        fourchette min/max en ATR, repli ATR 2 ou trade sauté), avec deux sorties de référence (Heishinator,
        objectif 2R). Placebo : mêmes déclencheurs, distance du stop PERMUTÉE entre les signaux (même
        distribution de distances en ATR, mais plus liée au niveau). -> A_stops.csv, A_placebo.csv
  B     OBJECTIFS / GESTION : R fixe, prochain niveau (ratio min), Heishinator, partiel + suiveur, break-even,
        sortie temporelle, suiveur ATR ; placebo des objectifs sur niveau (multiple de R permuté). -> B_*.csv
  C     PROPFIRM : Tradeify Select Flex, taille = nombre de micros pour un risque fixe en $ ; P(réussite),
        P(1er payout), valeur espérée ; choix par valeur espérée. -> C_propfirm.csv
  D     SITUATIONS : meilleure gestion par famille de déclencheur, régime de volatilité, séance ; contrôle
        chronologique (choix sur les 2/3 anciens des jours, test sur le 1/3 récent). -> D_*.csv
  E     Contrôle du biais de sélection (bootstrap de White) + référence au hasard + registre. -> E_*.csv
"""
from __future__ import annotations

import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
for p in (ICI, os.path.join(SB, 'moteur'), os.path.join(SB, 'propfirm')):
    if p not in sys.path:
        sys.path.insert(0, p)
import moteur as M          # noqa: E402
import simulateur as SIM    # noqa: E402

OUT = os.path.join(ICI, 'resultats')
os.makedirs(OUT, exist_ok=True)
TICK = 0.25
PLAGES = [('08:00', '22:00')]          # entrées 08:00-22:00 Paris pour TOUTES les gestions (même univers)
N_PLACEBO = 20
RISQUES = (100, 150, 200, 250, 300, 400, 500)
VARIANTE = 'tradeify_50k_select_flex'
ECHANTILLON = 'dev_cache' if os.environ.get('SOR_SOURCE', 'cache') == 'cache' else 'dev_dataset'

FAM_STOP = ['DET', 'PW', 'PM', 'PY', 'PWR', 'PMR', 'SES', 'MON', 'ORB', 'TL', 'RD', 'RF', 'SW', 'PIV', 'TOUT']
GROUPES = {'PIV': ['PW', 'PM', 'PY'],
           'TOUT': ['DET', 'PW', 'PM', 'PY', 'PWR', 'PMR', 'SES', 'MON', 'ORB', 'TL', 'RD', 'SW']}
MARGES = [('t', 2), ('a', 0.1), ('a', 0.25)]
FOURCHETTES = [(0.5, 3.0), (1.0, 3.0), (0.75, 2.0)]
REPLIS = [2.0, None]
K_ATR = [1.0, 1.5, 2.0, 2.5, 3.0]
FAM_TP = ['TOUT', 'PIV', 'DET', 'SES', 'RD', 'SW']
RMIN_TP = [1.0, 1.5, 2.0]

TYPE_DECL = {'sigF': 'tendance', 'hei': 'tendance', 'A_clx_trend': 'retournement', 'clx_buy': 'retournement',
             'clx_sell': 'retournement', 'tl': 'cassure', 'orb': 'cassure', 'mon': 'cassure', 'hasard': 'témoin'}


# ═══════════════════════════════════════ préparation ═══════════════════════════════════════
def _premier_par_jour(sig, index):
    j = index.tz_convert('America/Chicago').normalize()
    vu = set(); out = np.zeros(len(sig), bool)
    for i in np.flatnonzero(sig):
        if j[i] not in vu:
            vu.add(j[i]); out[i] = True
    return out


def declencheurs(df, graine=0):
    n = len(df)
    z = np.zeros(n, bool)
    B = lambda k: df[k].to_numpy(bool) if k in df else z.copy()
    nb = ~B('blackout')
    rng = np.random.default_rng(graine)
    alea = rng.random(n) < 1 / 12
    sens = rng.random(n) < 0.5
    D = {'sigF': (B('sig_long_fort'), B('sig_short_fort')),
         'A_clx_trend': (B('clx_buy') & B('trend_60'), z),
         'clx_buy': (B('clx_buy'), z), 'clx_sell': (z, B('clx_sell')),
         'tl': (B('tl_cassure_haut'), B('tl_cassure_bas')),
         'hei': (B('hei_flip_haut') & nb, B('hei_flip_bas') & nb),
         'orb': (_premier_par_jour(B('orb_cassure_haut'), df.index), _premier_par_jour(B('orb_cassure_bas'), df.index)),
         'mon': (B('mon_cassure_haut'), B('mon_cassure_bas')),
         'hasard': (alea & sens, alea & ~sens)}
    D = {k: (np.array(l, bool), np.array(s, bool)) for k, (l, s) in D.items()}
    for k in list(D):
        l, s = D[k]
        l[:110] = False; s[:110] = False           # chauffe des indicateurs
        if l.sum() + s.sum() == 0:
            del D[k]
    return D


def preparer(ut=None):
    import donnees_sor as DN
    ut = ut or DN.UT
    series = []
    for k, s in enumerate(DN.charger_series(ut)):
        df = M.charger_recherche(s['df'])
        lv = {}
        for f in DN.FAMILLES:
            cols = [c for c in df.columns if c.startswith('lv_%s_' % f)]
            lv[f] = df[cols].to_numpy(float)
        a = df['atr'].to_numpy(float)
        a100 = pd.Series(a).rolling(100, min_periods=50).mean().to_numpy()
        hp = df.index.hour + df.index.minute / 60
        base = df[['o', 'h', 'l', 'c', 'atr', 'hei_flip_haut', 'hei_flip_bas', 'trend_60']].copy()
        series.append(dict(nom=s['nom'], instrument=s['instrument'], df=base, lv=lv,
                           c=df['c'].to_numpy(float), a=a, vol=a / a100, heure=np.asarray(hp, float),
                           trend=df['trend_60'].to_numpy(bool), decl=declencheurs(df, graine=k)))
    pickle.dump(series, open(os.path.join(OUT, 'series_dev_%s.pkl' % ut), 'wb'))
    for s in series:
        print(s['nom'], len(s['df']), s['df'].index[0], '->', s['df'].index[-1],
              {k: int(l.sum() + sh.sum()) for k, (l, sh) in s['decl'].items()})
    return series


_SERIES = {}
UT_ETUDE = int(os.environ.get('SOR_UT', '15'))


def series_dev(ut=None):
    ut = ut or UT_ETUDE
    if ut not in _SERIES:
        f = os.path.join(OUT, 'series_dev_%s.pkl' % ut)
        _SERIES[ut] = pickle.load(open(f, 'rb')) if os.path.exists(f) else preparer(ut)
    return _SERIES[ut]


# ═══════════════════════════════════════ stops et objectifs ═══════════════════════════════════════
def matrice(P, fam):
    fams = GROUPES.get(fam, [fam])
    return np.hstack([P['lv'][f] for f in fams])


def stop_niveau(P, fam, marge, mn, mx, repli):
    """Distances de stop depuis la clôture du signal (long : dl, short : ds), niveau le plus proche de la
    famille au-delà duquel on se place avec la marge, gardé si mn <= distance <= mx (en ATR)."""
    c, a = P['c'], P['a']
    L = matrice(P, fam)
    mg = marge[1] * TICK if marge[0] == 't' else marge[1] * a
    mg = np.broadcast_to(mg, c.shape)[:, None]
    C = c[:, None]; A = a[:, None]
    with np.errstate(invalid='ignore'):
        dl = C - (L - mg); dl = np.where((L < C) & (dl >= mn * A) & (dl <= mx * A), dl, np.inf).min(1)
        ds = (L + mg) - C; ds = np.where((L > C) & (ds >= mn * A) & (ds <= mx * A), ds, np.inf).min(1)
    hl, hs = np.isfinite(dl), np.isfinite(ds)
    dl = np.where(hl, dl, np.nan); ds = np.where(hs, ds, np.nan)
    if repli is not None:
        dl = np.where(hl, dl, repli * a); ds = np.where(hs, ds, repli * a)
    return dict(dl=dl, ds=ds, hl=hl, hs=hs)


def stop_atr(P, k):
    a = P['a']
    return dict(dl=k * a, ds=k * a, hl=np.zeros(len(a), bool), hs=np.zeros(len(a), bool))


def permuter(D, L, S, rng, ul, us):
    """Placebo : permute les distances, exprimées en unités ul (longs) / us (shorts) — ATR pour un stop,
    distance du stop (R) pour un objectif — entre les signaux qui ont un niveau ; les autres signaux gardent
    leur valeur (repli). Même distribution de distances, mais plus liée au niveau."""
    out = {k: v.copy() for k, v in D.items()}
    il = np.flatnonzero(L & D['hl']); is_ = np.flatnonzero(S & D['hs'])
    k = np.r_[D['dl'][il] / ul[il], D['ds'][is_] / us[is_]]
    if len(k) < 2:
        return out
    k = k[rng.permutation(len(k))]
    out['dl'][il] = k[:len(il)] * ul[il]
    out['ds'][is_] = k[len(il):] * us[is_]
    return out


def obj_niveau(P, fam, rmin, St, repli_R=None):
    """Distances d'objectif : 1er niveau de la famille au-delà de l'entrée à >= rmin x distance du stop,
    objectif 1 tick avant le niveau. hl/hs : un niveau a été trouvé."""
    c = P['c']; L = matrice(P, fam); C = c[:, None]
    with np.errstate(invalid='ignore'):
        tl = (L - TICK) - C; tl = np.where((L > C) & (tl >= rmin * St['dl'][:, None]), tl, np.inf).min(1)
        ts = C - (L + TICK); ts = np.where((L < C) & (ts >= rmin * St['ds'][:, None]), ts, np.inf).min(1)
    hl, hs = np.isfinite(tl), np.isfinite(ts)
    tl = np.where(hl, tl, np.nan); ts = np.where(hs, ts, np.nan)
    if repli_R:
        tl = np.where(hl, tl, repli_R * St['dl']); ts = np.where(hs, ts, repli_R * St['ds'])
    return dict(dl=tl, ds=ts, hl=hl, hs=hs)


SORTIES_FIXES = {
    'heure': {},
    'R1': dict(objectif={'mode': 'R', 'k': 1.0}), 'R1.5': dict(objectif={'mode': 'R', 'k': 1.5}),
    'R2': dict(objectif={'mode': 'R', 'k': 2.0}), 'R3': dict(objectif={'mode': 'R', 'k': 3.0}),
    'R4': dict(objectif={'mode': 'R', 'k': 4.0}),
    'hei': dict(sortie_signal={'long': 'hei_flip_bas', 'short': 'hei_flip_haut'}),
    'N8': dict(sortie_barres=8), 'N16': dict(sortie_barres=16), 'N32': dict(sortie_barres=32),
    'BE0.5+hei': dict(break_even={'R': 0.5, 'ticks': 1}, sortie_signal={'long': 'hei_flip_bas', 'short': 'hei_flip_haut'}),
    'BE1+hei': dict(break_even={'R': 1.0, 'ticks': 1}, sortie_signal={'long': 'hei_flip_bas', 'short': 'hei_flip_haut'}),
    'BE1+R2': dict(break_even={'R': 1.0, 'ticks': 1}, objectif={'mode': 'R', 'k': 2.0}),
    'BE1+R3': dict(break_even={'R': 1.0, 'ticks': 1}, objectif={'mode': 'R', 'k': 3.0}),
    'P1+BE+tr2': dict(partiel={'R': 1.0, 'fraction': 0.5, 'be_apres': True}, suiveur={'k': 2.0, 'activation_R': 1.0}),
    'P1+BE+tr3': dict(partiel={'R': 1.0, 'fraction': 0.5, 'be_apres': True}, suiveur={'k': 3.0, 'activation_R': 1.0}),
    'P1+BE+hei': dict(partiel={'R': 1.0, 'fraction': 0.5, 'be_apres': True},
                      sortie_signal={'long': 'hei_flip_bas', 'short': 'hei_flip_haut'}),
    'P1+BE+R3': dict(partiel={'R': 1.0, 'fraction': 0.5, 'be_apres': True}, objectif={'mode': 'R', 'k': 3.0}),
    'tr2@1R': dict(suiveur={'k': 2.0, 'activation_R': 1.0}),
    'tr3': dict(suiveur={'k': 3.0, 'activation_R': 0.0}),
    'tr2@1R+hei': dict(suiveur={'k': 2.0, 'activation_R': 1.0}, sortie_signal={'long': 'hei_flip_bas', 'short': 'hei_flip_haut'}),
}
NOMS_SORTIES = list(SORTIES_FIXES) + ['niv:%s:%g%s' % (f, r, h) for f in FAM_TP for r in RMIN_TP for h in ('', '+hei')]


def spec_stop(nom):
    """'atr2' | 'niv:FAM:marge:mn-mx:repli' -> tuple."""
    if nom.startswith('atr'):
        return ('atr', float(nom[3:]))
    _, fam, mg, fr, rp = nom.split(':')
    mn, mx = map(float, fr.split('-'))
    marge = ('t', int(mg[:-1])) if mg.endswith('t') else ('a', float(mg[:-1]))
    return ('niv', fam, marge, mn, mx, None if rp == 'saute' else float(rp))


def nom_stop_niv(fam, marge, fr, repli):
    mg = '%dt' % marge[1] if marge[0] == 't' else '%ga' % marge[1]
    return 'niv:%s:%s:%g-%g:%s' % (fam, mg, fr[0], fr[1], 'saute' if repli is None else '%g' % repli)


def distances_stop(P, nom):
    sp = spec_stop(nom)
    return stop_atr(P, sp[1]) if sp[0] == 'atr' else stop_niveau(P, *sp[1:])


def gestion(P, St, nom_sortie, Ob=None):
    """Dictionnaire de gestion du moteur. Stop et objectif sur niveau passés en PRIX par barre signal."""
    c = P['c']
    g = dict(instrument=P['instrument'], plages_autorisees=PLAGES,
             stop={'mode': 'niveau', 'long': {'stop': c - St['dl']}, 'short': {'stop': c + St['ds']},
                   'marge_ticks': 0, 'min_atr': None, 'max_atr': None, 'sauter': True})
    if nom_sortie.startswith('niv:'):
        parts = nom_sortie.split(':')
        fam, rmin = parts[1], float(parts[2].replace('+hei', ''))
        if Ob is None:
            Ob = obj_niveau(P, fam, rmin, St)
        g['objectif'] = {'mode': 'niveau', 'long': {'obj': c + Ob['dl']}, 'short': {'obj': c - Ob['ds']},
                         'ratio_min': 0.0, 'si_absent': 'aucun'}
        if nom_sortie.endswith('+hei'):
            g['sortie_signal'] = {'long': 'hei_flip_bas', 'short': 'hei_flip_haut'}
    else:
        g.update(SORTIES_FIXES[nom_sortie])
    return g


def lancer(P, decl, St, nom_sortie, Ob=None):
    L, S = P['decl'][decl]
    g = gestion(P, St, nom_sortie, Ob)
    T = M.backtest(P['df'], L, S, g, details=True)
    if len(T):
        i = T['i_signal'].to_numpy()
        T['serie'] = P['nom']; T['decl'] = decl
        T['vol'] = P['vol'][i]; T['heure_sig'] = P['heure'][i]
        T['avec_tendance'] = np.where(T['sens'] == 'long', P['trend'][i], ~P['trend'][i])
        T['dist_atr'] = T['risque_usd'] / (M.INSTRUMENTS[P['instrument']]['point'] * P['a'][i])
    return T


def stats(T):
    if not len(T):
        return dict(n=0)
    r = T['r'].to_numpy(float); p = T['pnl_usd'].to_numpy(float)
    g, l = r[r > 0].sum(), -r[r < 0].sum()
    m = T['motif_sortie'].astype(str)
    return dict(n=len(T), r_moyen=float(r.mean()), r_med=float(np.median(r)), pf_r=float(g / l) if l > 0 else np.nan,
                pct_gagnants=float((r > 0).mean()), pct_stop=float(m.str.contains('stop').mean()),
                dist_atr=float(T['dist_atr'].mean()), r_std=float(r.std(ddof=1)) if len(r) > 1 else np.nan)


def tous(decl, f, series=None):
    """Concatène les trades d'un déclencheur sur toutes les séries : f(P) -> trades."""
    out = [f(P) for P in (series or series_dev()) if decl in P['decl']]
    out = [t for t in out if len(t)]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def liste_decl():
    ds = []
    for P in series_dev():
        for k in P['decl']:
            if k not in ds:
                ds.append(k)
    return ds


# ═══════════════════════════════════════ étape A : stops ═══════════════════════════════════════
def noms_stops():
    noms = ['atr%g' % k for k in K_ATR]
    for fam in FAM_STOP:
        for mg in MARGES:
            for fr in FOURCHETTES:
                for rp in REPLIS:
                    noms.append(nom_stop_niv(fam, mg, fr, rp))
    return noms


CENTRAUX = [nom_stop_niv(f, ('a', 0.1), (0.5, 3.0), rp) for f in FAM_STOP for rp in REPLIS]


def _tache_A(decl):
    rows, plac = [], []
    for ns in noms_stops():
        for so in ('hei', 'R2'):
            T = tous(decl, lambda P: lancer(P, decl, distances_stop(P, ns), so))
            st = stats(T)
            if ns.startswith('niv') and len(T):
                st['pct_niveau'] = _part_niveau(decl, ns, T)
            rows.append(dict(decl=decl, stop=ns, sortie=so, **st))
            if ns in CENTRAUX and st.get('n', 0) >= 5:
                pr = []
                for s in range(N_PLACEBO):
                    def f(P, s=s):
                        D = distances_stop(P, ns)
                        L, S = P['decl'][decl]
                        Dp = permuter(D, L, S, np.random.default_rng(1000 + s), P['a'], P['a'])
                        return lancer(P, decl, Dp, so)
                    Tp = tous(decl, f)
                    pr.append(stats(Tp).get('r_moyen', np.nan))
                pr = np.array(pr)
                plac.append(dict(decl=decl, stop=ns, sortie=so, n=st['n'], r_moyen=st['r_moyen'],
                                 placebo_moy=float(np.nanmean(pr)), placebo_p05=float(np.nanpercentile(pr, 5)),
                                 placebo_p95=float(np.nanpercentile(pr, 95)),
                                 p_placebo=float((1 + (pr >= st['r_moyen']).sum()) / (1 + len(pr)))))
    return rows, plac


def _part_niveau(decl, ns, T):
    """Part des trades dont le stop vient d'un niveau (et non du repli)."""
    tot = 0; niv = 0
    for P in series_dev():
        if decl not in P['decl']:
            continue
        D = distances_stop(P, ns)
        t = T[T['serie'] == P['nom']]
        if not len(t):
            continue
        i = t['i_signal'].to_numpy(); lg = (t['sens'] == 'long').to_numpy()
        niv += int(np.where(lg, D['hl'][i], D['hs'][i]).sum()); tot += len(t)
    return niv / tot if tot else np.nan


def etape_A():
    t0 = time.time()
    rows, plac = [], []
    with ProcessPoolExecutor(max_workers=min(9, len(liste_decl()))) as ex:
        for r, p in ex.map(_tache_A, liste_decl()):
            rows += r; plac += p
    A = pd.DataFrame(rows); P = pd.DataFrame(plac)
    A.to_csv(os.path.join(OUT, 'A_stops.csv'), index=False)
    P.to_csv(os.path.join(OUT, 'A_placebo.csv'), index=False)
    print('étape A : %d lignes, %d placebos, %.0f s' % (len(A), len(P), time.time() - t0))
    return A, P


# ═══════════════════════════════════════ étape B : objectifs et gestion ═══════════════════════════════════════
def _panel_A():
    A = pd.read_csv(os.path.join(OUT, 'A_stops.csv'))
    A = A[(A['decl'] != 'hasard') & (A['n'] >= 5)]
    niv = A[A['stop'].str.startswith('niv')]
    g = niv.groupby('stop').agg(r=('r_moyen', 'mean'), nd=('decl', 'nunique'))
    return g[g['nd'] >= 6].sort_values('r', ascending=False)


def _classement_placebo():
    """Stops sur niveau classés par l'étape A2 : écart moyen R réel - R placebo (mêmes trades, distance
    permutée) sur les déclencheurs réels ; on ne garde que ceux dont l'écart ET le R moyen sont positifs.
    Le classement brut de l'étape A favorisait les stops qui gagnent seulement en filtrant les trades
    (Monday « sauté ») et dont le placebo fait aussi bien. None si A2 n'a pas tourné."""
    f = os.path.join(OUT, 'A_placebo_top.csv')
    if not os.path.exists(f):
        return None
    P = pd.read_csv(f)
    P = P[P['decl'] != 'hasard']
    P['ecart'] = P['r_moyen'] - P['placebo_moy']
    g = P.groupby('stop').agg(r=('r_moyen', 'mean'), ecart=('ecart', 'mean'), nd=('decl', 'nunique'))
    g = g[(g['nd'] >= 6) & (g['ecart'] > 0) & (g['r'] > 0)]
    return g.sort_values('ecart', ascending=False)


def stops_B():
    """Stops gardés pour l'étape B : ATR 1,5 / 2 / 3 + les 2 meilleurs stops sur niveau AVEC repli ATR 2 (même
    ensemble de trades que l'ATR) + les 2 meilleurs « trade sauté sans niveau ». Classement : écart contre le
    placebo de l'étape A2 (repli : R moyen brut de l'étape A si A2 absent)."""
    g = _classement_placebo()
    if g is None or not len(g):
        g = _panel_A()
    rep = [k for k in g.index if k.endswith(':2')][:2]
    sau = [k for k in g.index if k.endswith(':saute')][:2]
    return ['atr1.5', 'atr2', 'atr3'] + rep + sau


def _tache_A2(args):
    decl, stops = args
    plac = []
    for ns in stops:
        for so in ('hei', 'R2'):
            T = tous(decl, lambda P: lancer(P, decl, distances_stop(P, ns), so))
            st = stats(T)
            if st.get('n', 0) < 5:
                continue
            pr = []
            for s in range(N_PLACEBO):
                def f(P, s=s):
                    D = distances_stop(P, ns)
                    L, S = P['decl'][decl]
                    return lancer(P, decl, permuter(D, L, S, np.random.default_rng(1000 + s), P['a'], P['a']), so)
                pr.append(stats(tous(decl, f)).get('r_moyen', np.nan))
            pr = np.array(pr)
            plac.append(dict(decl=decl, stop=ns, sortie=so, n=st['n'], r_moyen=st['r_moyen'],
                             placebo_moy=float(np.nanmean(pr)), placebo_p05=float(np.nanpercentile(pr, 5)),
                             placebo_p95=float(np.nanpercentile(pr, 95)),
                             p_placebo=float((1 + (pr >= st['r_moyen']).sum()) / (1 + len(pr)))))
    return plac


def etape_A2():
    """Placebo des 12 meilleurs stops sur niveau du panel (le classement brut favorise la chance)."""
    t0 = time.time()
    g = _panel_A()
    top = list(dict.fromkeys(list(g.index[:12]) + [k for k in g.index if k.endswith(':2')][:4]))
    plac = []
    with ProcessPoolExecutor(max_workers=9) as ex:
        for p in ex.map(_tache_A2, [(d, top) for d in liste_decl()]):
            plac += p
    P = pd.DataFrame(plac)
    P.to_csv(os.path.join(OUT, 'A_placebo_top.csv'), index=False)
    print('étape A2 : %d placebos, %.0f s' % (len(P), time.time() - t0))
    return P


def _tache_B(args):
    decl, stops = args
    rows, plac = [], []
    for ns in stops:
        for so in NOMS_SORTIES:
            T = tous(decl, lambda P: lancer(P, decl, distances_stop(P, ns), so))
            st = stats(T)
            rows.append(dict(decl=decl, stop=ns, sortie=so, **st))
            if so.startswith('niv:') and ns == 'atr2' and st.get('n', 0) >= 5:
                fam = so.split(':')[1]; rmin = float(so.split(':')[2].replace('+hei', ''))
                pr = []
                for s in range(N_PLACEBO):
                    def f(P, s=s):
                        St = distances_stop(P, ns)
                        Ob = obj_niveau(P, fam, rmin, St)
                        L, S = P['decl'][decl]
                        # placebo : multiple de R de l'objectif permuté entre signaux qui ont un niveau
                        Obp = permuter(Ob, L, S, np.random.default_rng(2000 + s), St['dl'], St['ds'])
                        return lancer(P, decl, St, so, Obp)
                    pr.append(stats(tous(decl, f)).get('r_moyen', np.nan))
                pr = np.array(pr)
                plac.append(dict(decl=decl, stop=ns, sortie=so, n=st['n'], r_moyen=st['r_moyen'],
                                 placebo_moy=float(np.nanmean(pr)), placebo_p05=float(np.nanpercentile(pr, 5)),
                                 placebo_p95=float(np.nanpercentile(pr, 95)),
                                 p_placebo=float((1 + (pr >= st['r_moyen']).sum()) / (1 + len(pr)))))
    return rows, plac


def etape_B():
    t0 = time.time()
    stops = stops_B()
    print('stops gardés pour B :', stops)
    rows, plac = [], []
    with ProcessPoolExecutor(max_workers=9) as ex:
        for r, p in ex.map(_tache_B, [(d, stops) for d in liste_decl()]):
            rows += r; plac += p
    B = pd.DataFrame(rows); P = pd.DataFrame(plac)
    B.to_csv(os.path.join(OUT, 'B_sorties.csv'), index=False)
    P.to_csv(os.path.join(OUT, 'B_placebo.csv'), index=False)
    print('étape B : %d lignes, %d placebos, %.0f s' % (len(B), len(P), time.time() - t0))
    return B, P


# ═══════════════════════════════════════ étape C : propfirm ═══════════════════════════════════════
_REGLES = None


def regles():
    global _REGLES
    if _REGLES is None:
        _REGLES = SIM.charge_regles()[VARIANTE]
    return _REGLES


def eval_propfirm(T, risques=RISQUES, n_sim=400, graine=0):
    """Pour chaque risque fixe en $ : P(réussite), P(1er payout), VE. Renvoie (lignes, meilleure par VE)."""
    out = []
    for rq in risques:
        if not len(T):
            break
        pris = int((np.floor(rq / T['risque_usd'].astype(float)) > 0).sum())
        if pris < 5:          # (le simulateur plante quand aucun trade ne passe le risque fixe)
            out.append(dict(risque_usd=rq, n_pris=pris, p_reussite=np.nan, p_1er_payout=np.nan, ve=np.nan,
                            delai=np.nan))
            continue
        r = SIM.monte_carlo(T, regles(), risque_usd=rq, n_sim=n_sim, graine=graine)
        out.append(dict(risque_usd=rq, n_pris=r.get('n_trades', 0), p_reussite=r.get('p_reussite', np.nan),
                        p_1er_payout=r.get('p_1er_payout', np.nan), ve=r.get('valeur_esperee_usd', np.nan),
                        delai=r.get('delai_median_jours', np.nan)))
    if not out:
        return [], {}
    best = max(out, key=lambda x: -1e18 if x['ve'] != x['ve'] else x['ve'])
    return out, best


def candidats_C():
    """Gestions évaluées en propfirm, par déclencheur : références fixes + 8 meilleures de l'étape B (R moyen,
    n >= 8) — le classement final se fait sur la valeur espérée propfirm, pas sur le R."""
    B = pd.read_csv(os.path.join(OUT, 'B_sorties.csv'))
    refs = [('atr2', 'hei'), ('atr2', 'R2'), ('atr1.5', 'R2'), ('atr2', 'heure'), ('atr3', 'hei'), ('atr2', 'P1+BE+tr2')]
    out = {}
    for d, g in B[B['n'] >= 8].groupby('decl'):
        top = g.sort_values('r_moyen', ascending=False).head(8)
        out[d] = list(dict.fromkeys(refs + list(zip(top['stop'], top['sortie']))))
    # gestions « panel » : les 6 meilleures en moyenne sur les déclencheurs réels
    pan = B[(B['decl'] != 'hasard') & (B['n'] >= 5)].groupby(['stop', 'sortie'])['r_moyen'].mean()
    pan = list(pan.sort_values(ascending=False).index[:6])
    for d in out:
        out[d] = list(dict.fromkeys(out[d] + pan))
    return out


def _tache_C(args):
    decl, gests = args
    rows = []
    for ns, so in gests:
        T = tous(decl, lambda P: lancer(P, decl, distances_stop(P, ns), so))
        st = stats(T)
        lignes, best = eval_propfirm(T)
        for li in lignes:
            rows.append(dict(decl=decl, stop=ns, sortie=so, **st, **li, meilleur=li is best))
    return rows


def etape_C():
    t0 = time.time()
    cand = candidats_C()
    rows = []
    with ProcessPoolExecutor(max_workers=9) as ex:
        for r in ex.map(_tache_C, list(cand.items())):
            rows += r
    C = pd.DataFrame(rows)
    C.to_csv(os.path.join(OUT, 'C_propfirm.csv'), index=False)
    print('étape C : %d lignes, %.0f s' % (len(C), time.time() - t0))
    return C


# ═══════════════════════════════════════ étape D : situations ═══════════════════════════════════════
MENU_D = [('atr2', 'hei'), ('atr2', 'R2'), ('atr1.5', 'R2'), ('atr2', 'R1'), ('atr3', 'hei'), ('atr2', 'P1+BE+tr2'),
          ('atr2', 'BE1+hei'), ('atr2', 'N16'), ('atr2', 'heure'), ('atr2', 'tr2@1R')]


def _menu_D():
    m = list(MENU_D)
    for ns in stops_B()[3:5]:
        m += [(ns, 'hei'), (ns, 'R2')]
    return m


def _tache_D(decl):
    rows = []
    for ns, so in _menu_D():
        T = tous(decl, lambda P: lancer(P, decl, distances_stop(P, ns), so))
        if len(T):
            T['stop'] = ns; T['sortie'] = so
            rows.append(T)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def etape_D():
    """Trades de chaque gestion du menu, découpés par situation (type de déclencheur, volatilité, séance,
    tendance 1H) ; meilleure gestion par situation choisie sur les 2/3 les plus anciens des jours de chaque
    série et vérifiée sur le 1/3 récent."""
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=9) as ex:
        parts = list(ex.map(_tache_D, [d for d in liste_decl() if d != 'hasard']))
    T = pd.concat([p for p in parts if len(p)], ignore_index=True)
    T['type'] = T['decl'].map(TYPE_DECL)
    T['regime_vol'] = pd.cut(T['vol'], [0, 0.9, 1.2, 99], labels=['vol_basse', 'vol_normale', 'vol_haute']).astype(str)
    T['seance'] = np.where((T['heure_sig'] >= 8) & (T['heure_sig'] < 14.5), 'Londres', 'US')
    T['tendance'] = np.where(T['avec_tendance'], 'avec_trend1H', 'contre_trend1H')
    # 2/3 anciens / 1/3 récent, par série
    T['periode'] = 'app'
    for s, g in T.groupby('serie'):
        cut = g['entree_t'].quantile(2 / 3)
        T.loc[g.index[g['entree_t'] > cut], 'periode'] = 'test'
    T.to_pickle(os.path.join(OUT, 'D_trades.pkl'))
    rows = []
    for dim in ('type', 'regime_vol', 'seance', 'tendance'):
        for val, g in T.groupby(dim):
            for (ns, so), h in g.groupby(['stop', 'sortie']):
                a, t = h[h.periode == 'app'], h[h.periode == 'test']
                rows.append(dict(dimension=dim, situation=val, stop=ns, sortie=so, n=len(h), r_moyen=h['r'].mean(),
                                 n_app=len(a), r_app=a['r'].mean() if len(a) else np.nan,
                                 n_test=len(t), r_test=t['r'].mean() if len(t) else np.nan))
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(OUT, 'D_situations.csv'), index=False)
    # choix sur app, vérif sur test (vs référence atr2+hei et atr2+R2)
    ch = []
    for (dim, val), g in D.groupby(['dimension', 'situation']):
        g = g[g['n_app'] >= 8]
        if not len(g):
            continue
        b = g.sort_values('r_app', ascending=False).iloc[0]
        ref = g[(g.stop == 'atr2') & (g.sortie == 'hei')]
        ref2 = g[(g.stop == 'atr2') & (g.sortie == 'R2')]
        ch.append(dict(dimension=dim, situation=val, choix='%s + %s' % (b.stop, b.sortie), r_app=b.r_app,
                       n_test=b.n_test, r_test=b.r_test,
                       ref_hei_test=ref['r_test'].iloc[0] if len(ref) else np.nan,
                       ref_R2_test=ref2['r_test'].iloc[0] if len(ref2) else np.nan))
    CH = pd.DataFrame(ch)
    CH.to_csv(os.path.join(OUT, 'D_choix.csv'), index=False)
    print('étape D : %.0f s' % (time.time() - t0))
    print(CH.to_string())
    return D, CH


# ═══════════════════════════════════════ étape E : biais de sélection, hasard, registre ═══════════════════════════════════════
def white_rc(B, n_boot=2000, graine=0):
    """Bootstrap de White (reality check) sur le panel : pour chaque gestion de l'étape B, gain moyen de R
    par signal contre la référence atr2+hei, apparié par (série, déclencheur, signal) ; rééchantillonnage
    par blocs de journées. p = probabilité que la MEILLEURE gestion ait un gain aussi grand par hasard."""
    return None   # calcul fait dans _white() (besoin des trades), voir etape_E


def _trades_panel(ns, so, decls):
    out = []
    for d in decls:
        T = tous(d, lambda P: lancer(P, d, distances_stop(P, ns), so))
        if len(T):
            out.append(T)
    T = pd.concat(out, ignore_index=True)
    T['cle'] = T['serie'] + '|' + T['decl'] + '|' + T['i_signal'].astype(str)
    return T


def _white(gests, decls, n_boot=2000, graine=0):
    ref = _trades_panel('atr2', 'hei', decls).set_index('cle')['r']
    jours = None
    diffs = {}
    for ns, so in gests:
        T = _trades_panel(ns, so, decls)
        s = T.set_index('cle')
        com = s.index.intersection(ref.index)
        dif = s.loc[com, 'r'] - ref.loc[com]
        j = M._jour_cme_serie(s.loc[com, 'entree_t'])
        diffs[(ns, so)] = pd.Series(dif.to_numpy(), index=pd.Index(j.to_numpy()))
    tousj = sorted(set().union(*[set(v.index) for v in diffs.values()]))
    pos = {j: k for k, j in enumerate(tousj)}
    nj = len(tousj)
    S = np.zeros((len(gests), nj)); N = np.zeros((len(gests), nj))
    for g, (k, v) in enumerate(diffs.items()):
        ix = np.array([pos[j] for j in v.index])
        np.add.at(S[g], ix, v.to_numpy()); np.add.at(N[g], ix, 1)
    obs = S.sum(1) / np.maximum(N.sum(1), 1)
    rng = np.random.default_rng(graine)
    bl = 3; nb = int(np.ceil(nj / bl))
    mx = np.empty(n_boot)
    for b in range(n_boot):
        deb = rng.integers(0, max(nj - bl + 1, 1), nb)
        ix = (deb[:, None] + np.arange(bl)).ravel()[:nj]
        m = S[:, ix].sum(1) / np.maximum(N[:, ix].sum(1), 1)
        mx[b] = (m - obs).max()
    best = int(np.argmax(obs))
    p = float((1 + (mx >= obs[best]).sum()) / (1 + n_boot))
    return pd.DataFrame(dict(stop=[g[0] for g in gests], sortie=[g[1] for g in gests], gain_r=obs)), gests[best], p


def ref_hasard_propfirm(decl, ns, so, risque, n_tirages=20):
    """Référence des CONSIGNES : moteur.reference_hasard (même gestion, mêmes heures, même sens) sur chaque série,
    tirages regroupés, puis le simulateur au même risque fixe. Renvoie P(réussite) moyenne et VE moyenne."""
    tir = [[] for _ in range(n_tirages)]
    for P in series_dev():
        if decl not in P['decl']:
            continue
        L, S = P['decl'][decl]
        g = gestion(P, distances_stop(P, ns), so)
        _, trs = M.reference_hasard(P['df'], n_tirages, g, graine=7, long=L, short=S, garder_trades=True)
        for k, t in enumerate(trs):
            if len(t):
                tir[k].append(t)
    tir = [pd.concat(t, ignore_index=True) for t in tir if t]
    ps, ves, rs = [], [], []
    for k, t in enumerate(tir):
        if (np.floor(risque / t['risque_usd'].astype(float)) > 0).sum() < 5:
            continue
        r = SIM.monte_carlo(t, regles(), risque_usd=risque, n_sim=300, graine=k)
        ps.append(r.get('p_reussite', np.nan)); ves.append(r.get('valeur_esperee_usd', np.nan)); rs.append(t['r'].mean())
    return dict(p_ref=float(np.nanmean(ps)), ve_ref=float(np.nanmean(ves)), r_ref=float(np.nanmean(rs)),
                ps=ps, ves=ves)


def etape_E(ecrire_registre=True):
    t0 = time.time()
    B = pd.read_csv(os.path.join(OUT, 'B_sorties.csv'))
    C = pd.read_csv(os.path.join(OUT, 'C_propfirm.csv'))
    decls = [d for d in liste_decl() if d != 'hasard']
    gests = list(B[['stop', 'sortie']].drop_duplicates().itertuples(index=False, name=None))
    W, best, p = _white(gests, decls)
    W.sort_values('gain_r', ascending=False).to_csv(os.path.join(OUT, 'E_white.csv'), index=False)
    print('White RC : meilleure gestion panel %s, gain %+.3f R/signal contre atr2+hei, p = %.3f (%d gestions)'
          % (best, W['gain_r'].max(), p, len(gests)))
    res = dict(white_best=best, white_p=p, white_n=len(gests))
    # recettes retenues : par déclencheur, meilleure VE propfirm
    best_c = C[C['meilleur']].sort_values('ve', ascending=False)
    rec = []
    for d, g in best_c.groupby('decl'):
        b = g.sort_values('ve', ascending=False).iloc[0]
        base = C[(C.decl == d) & (C.stop == 'atr2') & (C.sortie == 'hei') & (C.meilleur)]
        ref = ref_hasard_propfirm(d, b.stop, b.sortie, int(b.risque_usd))
        rec.append(dict(decl=d, stop=b.stop, sortie=b.sortie, risque_usd=int(b.risque_usd), n=int(b.n),
                        r_moyen=b.r_moyen, p_reussite=b.p_reussite, p_1er_payout=b.p_1er_payout, ve=b.ve,
                        base_ve=base['ve'].iloc[0] if len(base) else np.nan,
                        base_p=base['p_reussite'].iloc[0] if len(base) else np.nan,
                        p_ref_hasard=ref['p_ref'], ve_ref_hasard=ref['ve_ref'], r_ref_hasard=ref['r_ref'],
                        p_hasard_ve=float((1 + sum(v >= b.ve for v in ref['ves'])) / (1 + len(ref['ves'])))))
    R = pd.DataFrame(rec).sort_values('ve', ascending=False)
    R.to_csv(os.path.join(OUT, 'E_recettes.csv'), index=False)
    print(R.to_string())
    pickle.dump(res, open(os.path.join(OUT, 'E_white.pkl'), 'wb'))
    print('étape E : %.0f s' % (time.time() - t0))
    return R, res


# ═══════════════════════════════════════ étape F : panel propfirm, niveaux contre placebo ═══════════════════════════════════════
N_PLAC_F = 5


def menu_F():
    s = stops_B()
    rep, sau = s[3], s[5]
    m = [('atr2', 'hei'), ('atr2', 'R2'), ('atr1.5', 'R2'), ('atr3', 'hei'), ('atr2', 'heure'), ('atr2', 'P1+BE+tr2'),
         ('atr2', 'BE1+hei'), ('atr2', 'tr3'), ('atr2', 'niv:PIV:1.5+hei'), ('atr2', 'niv:DET:1.5+hei'),
         (rep, 'hei'), (rep, 'R2'), (sau, 'hei')]
    plac = [(rep, 'hei'), (rep, 'R2'), (sau, 'hei'), ('atr2', 'niv:PIV:1.5+hei'), ('atr2', 'niv:DET:1.5+hei')]
    return m, plac


def _trades_placebo(decl, ns, so, s, series=None):
    """Trades placebo : stop sur niveau -> distance permutée ; objectif sur niveau -> multiple de R permuté."""
    def f(P):
        St = distances_stop(P, ns)
        L, S = P['decl'][decl]
        if ns.startswith('niv'):
            St = permuter(St, L, S, np.random.default_rng(1000 + s), P['a'], P['a'])
        Ob = None
        if so.startswith('niv:'):
            fam = so.split(':')[1]; rmin = float(so.split(':')[2].replace('+hei', ''))
            Ob = obj_niveau(P, fam, rmin, distances_stop(P, ns))
            Ob = permuter(Ob, L, S, np.random.default_rng(2000 + s), St['dl'], St['ds'])
        return lancer(P, decl, St, so, Ob)
    return tous(decl, f, series)


def _tache_F(decl):
    m, plac = menu_F()
    rows = []
    for ns, so in m:
        T = tous(decl, lambda P: lancer(P, decl, distances_stop(P, ns), so))
        lignes, _ = eval_propfirm(T)
        for li in lignes:
            rows.append(dict(decl=decl, stop=ns, sortie=so, placebo=-1, n=len(T), r_moyen=T['r'].mean() if len(T) else np.nan, **li))
        if (ns, so) in plac:
            for s in range(N_PLAC_F):
                Tp = _trades_placebo(decl, ns, so, s)
                lignes, _ = eval_propfirm(Tp, graine=s + 1)
                for li in lignes:
                    rows.append(dict(decl=decl, stop=ns, sortie=so, placebo=s, n=len(Tp),
                                     r_moyen=Tp['r'].mean() if len(Tp) else np.nan, **li))
    return rows


def etape_F():
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=9) as ex:
        for r in ex.map(_tache_F, [d for d in liste_decl()]):
            rows += r
    F = pd.DataFrame(rows)
    F.to_csv(os.path.join(OUT, 'F_panel_propfirm.csv'), index=False)
    print('étape F : %d lignes, %.0f s' % (len(F), time.time() - t0))
    return F


# ═══════════════════════════════════════ étape G : entrées publiées par les autres agents ═══════════════════════════════════════
REG = os.path.join(SB, 'registre')
MENU_G = [('atr1', 'R4'), ('atr2', 'hei'), ('atr2', 'R2'), ('atr1.5', 'R2'), ('atr3', 'hei'), ('atr2', 'heure'),
          ('atr2', 'P1+BE+tr2'), ('atr2', 'BE1+hei'), ('atr2', 'niv:PIV:1.5+hei'), ('atr1', 'hei'), ('atr1', 'R2')]


def entrees_registre(id_, series):
    """Signaux (long, short) par série reconstitués depuis la liste de trades d'une recette du registre :
    barre signal = barre dont la CLÔTURE est l'heure d'entrée (entrée à l'ouverture suivante) ; la série
    (MES ou MNQ) est celle dont le prix est le plus proche du prix d'entrée du trade."""
    f = os.path.join(REG, 'trades', id_ + '.csv')
    if not os.path.exists(f):
        return 0, 0
    T = pd.read_csv(f)
    t = pd.to_datetime(T['entree_t'], utc=True)
    px = T['prix_entree'].to_numpy(float)
    cand = []                    # (k_trade, série, barre, écart relatif de prix)
    for P in series:
        P['decl'][id_] = (np.zeros(len(P['df']), bool), np.zeros(len(P['df']), bool))
        idx = P['df'].index
        ut = pd.Timedelta(minutes=float(np.median(np.diff(idx.as_unit('ns').asi8[:50]))) / 6e10)
        clo = pd.Index((idx + ut).tz_convert('UTC'))
        pos = clo.get_indexer(t)
        for k, p in enumerate(pos):
            if p >= 0:
                cand.append((k, id(P), p, abs(P['c'][p] / px[k] - 1)))
    par = {}
    for k, sid, p, e in cand:
        if k not in par or e < par[k][2]:
            par[k] = (sid, p, e)
    n_ok = 0
    for k, (sid, p, e) in par.items():
        if e > 0.02:
            continue
        P = next(x for x in series if id(x) == sid)
        (P['decl'][id_][0] if T['sens'].iloc[k] == 'long' else P['decl'][id_][1])[p] = True
        n_ok += 1
    return n_ok, len(T)


def etape_G(ids=None):
    global PLAGES
    PLAGES = None            # les entrées des autres agents gardent leurs propres heures
    t0 = time.time()
    R = pd.read_csv(os.path.join(REG, 'registre_tests.csv'))
    R = R[R['id'].str.match(r'^(EXH|REG|ML|MET|TEN|RET|CAS)-')] if ids is None else R[R['id'].isin(ids)]
    rows = []
    for _, rec in R.iterrows():
        try:
            ut = int(str(rec['ut_signal']).replace('m', ''))
        except ValueError:
            continue
        series = [dict(P, decl={}) for P in series_dev(ut)]
        n_ok, n_tot = entrees_registre(rec['id'], series)
        if n_ok < 5:
            print(rec['id'], 'entrées non retrouvées (%d/%d)' % (n_ok, n_tot)); continue
        for ns, so in MENU_G:
            T = tous(rec['id'], lambda P: lancer(P, rec['id'], distances_stop(P, ns), so), series)
            lignes, best = eval_propfirm(T, n_sim=400)
            st = stats(T)
            rows.append(dict(id=rec['id'], recette=rec['recette'], ut=ut, entrees=n_ok, stop=ns, sortie=so, **st,
                             risque_usd=best.get('risque_usd'), p_reussite=best.get('p_reussite'),
                             p_1er_payout=best.get('p_1er_payout'), ve=best.get('ve')))
        print(rec['id'], 'fait', n_ok, '/', n_tot)
    G = pd.DataFrame(rows)
    G.to_csv(os.path.join(OUT, 'G_entrees_agents.csv'), index=False)
    print('étape G : %d lignes, %.0f s' % (len(G), time.time() - t0))
    if len(G):
        print(G[['id', 'stop', 'sortie', 'n', 'r_moyen', 'risque_usd', 'p_reussite', 'p_1er_payout', 've']].to_string())
    return G


if __name__ == '__main__':
    etapes = sys.argv[1:] or ['prep', 'A', 'A2', 'B', 'C', 'D', 'E', 'F', 'G']
    if 'prep' in etapes:
        preparer()
    if 'A' in etapes:
        etape_A()
    if 'A2' in etapes:
        etape_A2()
    if 'B' in etapes:
        etape_B()
    if 'C' in etapes:
        etape_C()
    if 'D' in etapes:
        etape_D()
    if 'E' in etapes:
        etape_E()
    if 'F' in etapes:
        etape_F()
    if 'G' in etapes:
        etape_G()
