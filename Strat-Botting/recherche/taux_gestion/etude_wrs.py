"""Agent « Taux — géométrie et gestion » (WRS) : frontière taux de gagnants <-> espérance selon la gestion.

    ~/venv-quant/bin/python etude_wrs.py [etapes]     # parmi verif balayage synthese wf final (défaut : tout)

Données : donnees_wrs.charger(ut) (accès unique ; WRS_SOURCE=dataset pour le DATASET), développement seulement.
Moteur commun et simulateur propfirm commun, non modifiés.

Étapes
  verif     contrôle de la table « issue de chaque barre » contre des backtests à signal unique.
  balayage  pour chaque gestion (stop ATR x sortie, ~270) et chaque déclencheur (8 de SOR + témoin au hasard +
            ML-0001, EXH-0001..0003) : trades réels (moteur, une position à la fois) et PLACEBO DE MÊME GESTION
            (2000 tirages : chaque trade réel remplacé par une entrée au hasard, même série, même heure de
            Paris, même sens, mêmes heures autorisées ; issue lue dans la table des issues par barre, calculée
            par le moteur). -> resultats/balayage.csv, resultats/trades_balayage.pkl
  synthese  frontière taux <-> R par famille de gestion, réel contre placebo. -> resultats/frontiere*.csv
  wf        walk-forward 5 plis (blocs de journées, ratio 3) : sur l'apprentissage, gestion au taux 60-75 %
            de meilleur R ; test sur le bloc suivant. -> resultats/wf_*.csv
  final     candidats WF : placebo exact moteur.reference_hasard (>= 500 tirages, plis de test), White RC sur
            tout le balayage, simulateur Tradeify Select Flex (optimise_taille, risque fixe), registre.
"""
from __future__ import annotations

import copy
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import donnees_wrs as DW

E = DW.E
import moteur as M          # noqa: E402
import simulateur as SIM    # noqa: E402

OUT = DW.OUT
PLAGES_SOR = [('08:00', '22:00')]
VARIANTE = 'tradeify_50k_select_flex'
N_PLAC = 2000
BANDE = (0.60, 0.75)
HEI = {'long': 'hei_flip_bas', 'short': 'hei_flip_haut'}

# déclencheurs : nom -> (UT, plages d'entrée)
DECL_SOR = ['sigF', 'A_clx_trend', 'clx_buy', 'clx_sell', 'tl', 'hei', 'orb', 'mon', 'hasard']
DECLS = {d: (15, 'sor') for d in DECL_SOR}
DECLS.update({'ML-0001': (15, 'libre'), 'EXH-0001': (30, 'libre'), 'EXH-0002': (30, 'libre'),
              'EXH-0003': (60, 'libre')})
PLAGES = {'sor': PLAGES_SOR, 'libre': None}
NOMS_DECL = {'clx_buy': 'climax BUY (SOR-0001)', 'A_clx_trend': 'climax BUY + TREND 1H (SOR-0002, préréglage A)',
             'hei': 'flip Heishinator (SOR-0003)', 'clx_sell': 'climax SELL', 'sigF': 'Signator Fort',
             'tl': 'cassure de trendline', 'orb': 'cassure ORB', 'mon': 'cassure Monday', 'hasard': 'TÉMOIN au hasard',
             'ML-0001': 'ML-0001 (tous candidats)', 'EXH-0001': 'EXH-0001', 'EXH-0002': 'EXH-0002',
             'EXH-0003': 'EXH-0003'}


# ═══════════════════════════════════════ catalogue des gestions ═══════════════════════════════════════
def catalogue_sorties():
    """nom -> (famille, morceau de gestion). Les objectifs sur niveau sont construits à part (niv:...)."""
    S = {}
    for k in (0.3, 0.5, 0.7, 1.0, 1.5, 2.0):
        S['R%g' % k] = ('objectif R', dict(objectif={'mode': 'R', 'k': k}))
    S['hei'] = ('référence', dict(sortie_signal=HEI))
    S['heure'] = ('référence', {})
    for n in (4, 8, 16):
        S['N%d' % n] = ('temps', dict(sortie_barres=n))
    for n in (8, 16):
        S['N%d+BE0.5t2' % n] = ('temps', dict(sortie_barres=n, break_even={'R': 0.5, 'ticks': 2}))
    for x in (0.3, 0.5, 0.75, 1.0):
        for t in (2, 4):
            S['BE%gt%d+hei' % (x, t)] = ('break-even', dict(break_even={'R': x, 'ticks': t}, sortie_signal=HEI))
    for x in (0.3, 0.5):
        for t in (2, 4):
            for k in (1.0, 1.5, 2.0):
                S['BE%gt%d+R%g' % (x, t, k)] = ('break-even', dict(break_even={'R': x, 'ticks': t},
                                                                    objectif={'mode': 'R', 'k': k}))
        S['BE%gt2+tr2@1R' % x] = ('break-even', dict(break_even={'R': x, 'ticks': 2},
                                                     suiveur={'k': 2.0, 'activation_R': 1.0, 'ref': 'cloture'}))
    # partiels (moitié du contrat à p R ; le reste passe au break-even + 2 ticks, puis sortie du reste)
    BEP = {'R': 1e9, 'ticks': 2}         # ne déclenche jamais seul : fixe seulement les ticks du BE après partiel
    for p in (0.3, 0.5, 0.7):
        base = dict(partiel={'R': p, 'fraction': 0.5, 'be_apres': True}, break_even=BEP)
        S['P%g+hei' % p] = ('partiel', dict(base, sortie_signal=HEI))
        S['P%g+tr2' % p] = ('partiel', dict(base, suiveur={'k': 2.0, 'activation_R': p, 'ref': 'cloture'}))
        S['P%g+tr3' % p] = ('partiel', dict(base, suiveur={'k': 3.0, 'activation_R': p, 'ref': 'cloture'}))
        S['P%g+R1.5' % p] = ('partiel', dict(base, objectif={'mode': 'R', 'k': 1.5}))
        S['P%g+R2' % p] = ('partiel', dict(base, objectif={'mode': 'R', 'k': 2.0}))
        S['P%g+heure' % p] = ('partiel', dict(base))
        S['P%g+N16' % p] = ('partiel', dict(base, sortie_barres=16))
        S['P%gf75+hei' % p] = ('partiel', dict(partiel={'R': p, 'fraction': 0.75, 'be_apres': True},
                                               break_even=BEP, sortie_signal=HEI))
        S['P%gsansBE+hei' % p] = ('partiel', dict(partiel={'R': p, 'fraction': 0.5, 'be_apres': False},
                                                  sortie_signal=HEI))
    for k in (1.0, 1.5, 2.0, 3.0):
        for a in (0.0, 0.5):
            S['tr%g@%gR' % (k, a)] = ('suiveur ATR', dict(suiveur={'k': k, 'activation_R': a, 'ref': 'cloture'}))
    for fam in ('PIV', 'DET', 'SES', 'SW', 'RD', 'TOUT'):
        for rmin in (0.3, 0.5, 0.75):
            S['niv:%s:%g+hei' % (fam, rmin)] = ('objectif niveau', None)
    return S


SORTIES = catalogue_sorties()
STOPS = (1.5, 2.0, 3.0)
GESTIONS = [(k, so) for k in STOPS for so in SORTIES]


def gestion(P, k, so, plages):
    """Dictionnaire du moteur. Stop k ATR posé depuis la CLÔTURE du signal (comme STRATEGIE_V1.pine et SOR)."""
    c, a = P['c'], P['a']
    g = dict(instrument=P['instrument'], plages_autorisees=plages,
             stop={'mode': 'niveau', 'long': {'stop': c - k * a}, 'short': {'stop': c + k * a},
                   'marge_ticks': 0, 'min_atr': None, 'max_atr': None, 'sauter': True})
    if so.startswith('niv:'):
        _, fam, r = so.split(':')
        rmin = float(r.replace('+hei', ''))
        Ob = E.obj_niveau(P, fam, rmin, E.stop_atr(P, k))
        g['objectif'] = {'mode': 'niveau', 'long': {'obj': c + Ob['dl']}, 'short': {'obj': c - Ob['ds']},
                         'ratio_min': 0.0, 'si_absent': 'aucun'}
        g['sortie_signal'] = HEI
    else:
        g.update(copy.deepcopy(SORTIES[so][1]))
    return g


def famille(so):
    return SORTIES[so][0]


# ═══════════════════════════════════════ issues par barre ═══════════════════════════════════════
def issues(P, g, d):
    """Issue (r, pnl) d'une entrée au marché à CHAQUE barre signal possible, sens d (1 / -1), calculée par le
    moteur : passes successives d'un backtest « tout est signal » (une position à la fois), en retirant à chaque
    passe les barres tradées et celles qui n'étaient pas bloquées par une position (donc non tradables).
    NaN = barre où cette gestion ne peut pas entrer (heures, stop impossible)."""
    df = P['df']; n = len(df)
    r = np.full(n, np.nan); pnl = np.full(n, np.nan)
    R = np.ones(n, bool); R[:110] = False; R[-1] = False
    for _ in range(2000):
        if not R.any():
            break
        T = M.backtest(df, R if d == 1 else None, R if d == -1 else None, g, details=True)
        if not len(T):
            break
        i = T['i_signal'].to_numpy()
        r[i] = T['r'].to_numpy(); pnl[i] = T['pnl_usd'].to_numpy()
        R[i] = False
        bl = np.zeros(n + 1, np.int64)
        np.add.at(bl, i + 1, 1)
        np.add.at(bl, np.minimum(T['k_sortie'].to_numpy() + 1, n), -1)
        R &= np.cumsum(bl)[:n] > 0
    return r, pnl


def heure_clo(P):
    df = P['df']
    ut = pd.Timedelta(minutes=float(np.median(np.diff(df.index.as_unit('ns').asi8[:50]))) / 6e10)
    return (df.index + ut).tz_convert('Europe/Paris').hour.to_numpy()


def blocs(P, nb=8):
    """Bloc (0..nb-1) de journées CME consécutives de chaque barre (même découpage que moteur.walk_forward)."""
    j = M.barres(P['df']).jour_cme()
    uj = np.unique(j)
    bornes = np.linspace(0, len(uj), nb + 1).round().astype(int)
    b = np.zeros(len(j), int)
    for q in range(nb):
        b[np.isin(j, uj[bornes[q]:bornes[q + 1]])] = q
    return b


def stats_r(r, pnl):
    r = np.asarray(r, float); pnl = np.asarray(pnl, float)
    if not len(r):
        return dict(n=0)
    g, l = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), win=float((pnl > 0).mean()), r=float(r.mean()), pf_r=float(g / l) if l > 0 else np.nan,
                r_med=float(np.median(r)))


def placebo(reels, tables, n_plac=N_PLAC, graine=0):
    """reels : liste (serie, i_signal, sens) ; tables[serie] = dict(r1, p1, r_1, p_1, heure).
    Chaque trade réel -> barre au hasard de la même série, même heure de clôture (Paris), même sens, parmi les
    barres où la gestion peut entrer. Renvoie win, r, pf_r par tirage."""
    rng = np.random.default_rng(graine)
    R_ = []; W_ = []
    for (serie, d), grp in reels.groupby(['serie', 'd']):
        tb = tables[serie]
        rr = tb['r1'] if d == 1 else tb['r_1']; pp = tb['p1'] if d == 1 else tb['p_1']
        ok = np.isfinite(rr)
        for h, gh in grp.groupby('h'):
            pool = np.flatnonzero(ok & (tb['heure'] == h))
            if not len(pool):
                pool = np.flatnonzero(ok)
            if not len(pool):
                continue
            ix = pool[rng.integers(len(pool), size=(n_plac, len(gh)))]
            R_.append(rr[ix]); W_.append(pp[ix] > 0)
    if not R_:
        return None
    R_ = np.hstack(R_); W_ = np.hstack(W_)
    g = np.where(R_ > 0, R_, 0).sum(1); l = -np.where(R_ < 0, R_, 0).sum(1)
    return dict(win=W_.mean(1), r=R_.mean(1), pf_r=g / np.maximum(l, 1e-9))


# ═══════════════════════════════════════ vérification ═══════════════════════════════════════
def etape_verif(n_test=60):
    """La table des issues doit être identique au backtest à signal unique (même barre, même gestion)."""
    rng = np.random.default_rng(3)
    S = DW.charger(15)
    bad = 0; tot = 0
    for (k, so) in [(2.0, 'hei'), (2.0, 'P0.5+tr2'), (3.0, 'BE0.5t2+R1'), (1.5, 'niv:PIV:0.5+hei'), (2.0, 'N8')]:
        for P in S:
            g = gestion(P, k, so, PLAGES_SOR)
            for d in (1, -1):
                r, _ = issues(P, g, d)
                for i in rng.integers(110, len(P['df']) - 1, n_test // 4):
                    sig = np.zeros(len(P['df']), bool); sig[i] = True
                    T = M.backtest(P['df'], sig if d == 1 else None, sig if d == -1 else None, g)
                    v = T['r'].iloc[0] if len(T) else np.nan
                    tot += 1
                    if not ((np.isnan(v) and np.isnan(r[i])) or abs(v - r[i]) < 1e-9):
                        bad += 1
    print('vérif issues : %d / %d identiques' % (tot - bad, tot))
    return bad == 0


# ═══════════════════════════════════════ balayage ═══════════════════════════════════════
def _tache(args):
    k, so = args
    rows, trs = [], []
    for ut in sorted({u for u, _ in DECLS.values()}):
        S = DW.charger(ut)
        for pk in sorted({p for d, (u, p) in DECLS.items() if u == ut}):
            decls = [d for d, (u, p) in DECLS.items() if u == ut and p == pk]
            tables = {}
            reels = {d: [] for d in decls}
            for P in S:
                if not any(d in P['decl'] for d in decls):
                    continue
                g = gestion(P, k, so, PLAGES[pk])
                r1, p1 = issues(P, g, 1); r_1, p_1 = issues(P, g, -1)
                hc = heure_clo(P); bl = blocs(P)
                tables[P['nom']] = dict(r1=r1, p1=p1, r_1=r_1, p_1=p_1, heure=hc)
                for d in decls:
                    if d not in P['decl']:
                        continue
                    L, Sh = P['decl'][d]
                    T = M.backtest(P['df'], L, Sh, g, details=True)
                    if not len(T):
                        continue
                    i = T['i_signal'].to_numpy()
                    t = pd.DataFrame(dict(decl=d, stop=k, sortie=so, serie=P['nom'], i_signal=i,
                                          d=np.where(T['sens'] == 'long', 1, -1), h=hc[i], blk=bl[i],
                                          entree_t=T['entree_t'].to_numpy(), r=T['r'].to_numpy(),
                                          pnl=T['pnl_usd'].to_numpy(), motif=T['motif_sortie'].astype(str).to_numpy()))
                    reels[d].append(t)
            for d in decls:
                if not reels[d]:
                    continue
                t = pd.concat(reels[d], ignore_index=True)
                trs.append(t)
                st = stats_r(t['r'], t['pnl'])
                pl = placebo(t, tables, graine=hash((d, k, so)) % 2**31)
                row = dict(decl=d, ut=ut, stop=k, sortie=so, famille=famille(so), **st,
                           pct_stop=float(t['motif'].str.contains('stop').mean()))
                if pl is not None:
                    row.update(win_plac=float(pl['win'].mean()), r_plac=float(pl['r'].mean()),
                               pf_plac=float(np.median(pl['pf_r'])),
                               p_win=float((1 + (pl['win'] >= st['win'] - 1e-12).sum()) / (1 + N_PLAC)),
                               p_r=float((1 + (pl['r'] >= st['r'] - 1e-12).sum()) / (1 + N_PLAC)),
                               win_plac_p95=float(np.percentile(pl['win'], 95)))
                    row['ecart_win'] = row['win'] - row['win_plac']
                    row['ecart_r'] = row['r'] - row['r_plac']
                rows.append(row)
    return rows, (pd.concat(trs, ignore_index=True) if trs else pd.DataFrame())


def etape_balayage():
    t0 = time.time()
    for ut in (15, 30, 60):
        DW.charger(ut)
    rows, trs = [], []
    with ProcessPoolExecutor(max_workers=9) as ex:
        for q, (r, t) in enumerate(ex.map(_tache, GESTIONS, chunksize=2)):
            rows += r; trs.append(t)
            if q % 30 == 0:
                print('  %d / %d gestions, %.0f s' % (q + 1, len(GESTIONS), time.time() - t0), flush=True)
    B = pd.DataFrame(rows)
    B.to_csv(os.path.join(OUT, 'balayage.csv'), index=False)
    T = pd.concat(trs, ignore_index=True)
    T.to_pickle(os.path.join(OUT, 'trades_balayage.pkl'))
    print('balayage : %d lignes, %d trades, %.0f s' % (len(B), len(T), time.time() - t0))
    return B


# ═══════════════════════════════════════ synthèse : frontière ═══════════════════════════════════════
def etape_synthese():
    B = pd.read_csv(os.path.join(OUT, 'balayage.csv'))
    reels = B[~B['decl'].isin(['hasard'])]
    # 1. par gestion, moyenne sur les déclencheurs réels (panel)
    G = reels.groupby(['stop', 'sortie', 'famille']).agg(
        n_decl=('decl', 'nunique'), n=('n', 'sum'), win=('win', 'mean'), win_plac=('win_plac', 'mean'),
        ecart_win=('ecart_win', 'mean'), r=('r', 'mean'), r_plac=('r_plac', 'mean'), ecart_r=('ecart_r', 'mean'),
        decl_win_p05=('p_win', lambda x: int((x <= 0.05).sum())), decl_r_pos=('r', lambda x: int((x > 0).sum()))
    ).reset_index().sort_values('win', ascending=False)
    G.to_csv(os.path.join(OUT, 'frontiere_panel.csv'), index=False)
    # 2. frontière par famille : par tranche de taux de gagnants, meilleur R (réel) et R placebo
    reels = reels.copy()
    reels['tranche'] = pd.cut(reels['win'], [0, .4, .5, .6, .65, .7, .75, .8, .9, 1.0])
    F = reels.groupby(['famille', 'tranche'], observed=True).agg(
        cas=('n', 'size'), win=('win', 'mean'), win_plac=('win_plac', 'mean'), r=('r', 'mean'),
        r_plac=('r_plac', 'mean'), part_r_pos=('r', lambda x: float((x > 0).mean())),
        part_win_sig=('p_win', lambda x: float((x <= 0.05).mean()))).reset_index()
    F.to_csv(os.path.join(OUT, 'frontiere_familles.csv'), index=False)
    # 3. combinaisons qui remplissent les critères 1-3 (en échantillon, avant WF)
    C = B[(B['win'] >= BANDE[0]) & (B['win'] <= BANDE[1]) & (B['r'] > 0) & (B['pf_r'] > 1)]
    C = C.sort_values('p_win')
    C.to_csv(os.path.join(OUT, 'candidats_bande.csv'), index=False)
    print('panel : %d gestions ; combinaisons dans la bande 60-75 %% avec R > 0 : %d / %d (dont p_win <= 0,05 : %d)'
          % (len(G), len(C), len(B), int((C['p_win'] <= 0.05).sum())))
    print(F.to_string())
    return G, F, C


# ═══════════════════════════════════════ walk-forward ═══════════════════════════════════════
def _stats_groupe(t):
    r = t['r'].to_numpy(); p = t['pnl'].to_numpy()
    g, l = r[r > 0].sum(), -r[r < 0].sum()
    return pd.Series(dict(n=len(r), win=(p > 0).mean() if len(r) else np.nan, r=r.mean() if len(r) else np.nan,
                          pf_r=g / l if l > 0 else np.nan))


def selection_wf(T, decl, regle='r', n_min=8):
    """5 plis : apprentissage = blocs [p, p+3), test = bloc p+3 (par série). Sur l'apprentissage, parmi les
    gestions au taux 60-75 % (n >= n_min), on prend le meilleur R (regle='r') ou le meilleur écart de taux contre
    le hasard... (regle='r' seulement : l'écart demande le placebo par pli, fait à l'étape final)."""
    t = T[T['decl'] == decl]
    choix, oos = [], []
    for p in range(5):
        app = t[(t['blk'] >= p) & (t['blk'] < p + 3)]
        tst = t[t['blk'] == p + 3]
        s = app.groupby(['stop', 'sortie']).apply(_stats_groupe, include_groups=False)
        s = s[(s['n'] >= n_min) & (s['win'] >= BANDE[0]) & (s['win'] <= BANDE[1])]
        if not len(s):
            choix.append(dict(decl=decl, pli=p, stop=np.nan, sortie=None)); continue
        b = s.sort_values(regle, ascending=False).iloc[0]
        k, so = b.name
        o = tst[(tst['stop'] == k) & (tst['sortie'] == so)]
        oos.append(o.assign(pli=p))
        choix.append(dict(decl=decl, pli=p, stop=k, sortie=so, n_app=int(b['n']), win_app=b['win'], r_app=b['r'],
                          n_test=len(o), win_test=(o['pnl'] > 0).mean() if len(o) else np.nan,
                          r_test=o['r'].mean() if len(o) else np.nan))
    return pd.DataFrame(choix), (pd.concat(oos, ignore_index=True) if oos else pd.DataFrame())


def choix_panel(T, n_min=5):
    """Une SEULE gestion pour tous les déclencheurs réels (SOR : « une seule règle pour tout »), choisie à chaque pli
    sur l'apprentissage : taux moyen du panel dans la bande 60-75 %, meilleur R moyen du panel."""
    t = T[T['decl'] != 'hasard']
    out = {}
    for p in range(5):
        app = t[(t['blk'] >= p) & (t['blk'] < p + 3)]
        s = app.groupby(['decl', 'stop', 'sortie']).apply(_stats_groupe, include_groups=False).reset_index()
        s = s[s['n'] >= n_min]
        g = s.groupby(['stop', 'sortie']).agg(win=('win', 'mean'), r=('r', 'mean'), nd=('decl', 'nunique'))
        g = g[(g['nd'] >= 8) & (g['win'] >= BANDE[0]) & (g['win'] <= BANDE[1])]
        out[p] = g.sort_values('r', ascending=False).index[0] if len(g) else (np.nan, None)
    return out


def selection_panel(T, decl, cp):
    t = T[T['decl'] == decl]
    choix, oos = [], []
    for p, (k, so) in cp.items():
        o = t[(t['blk'] == p + 3) & (t['stop'] == k) & (t['sortie'] == so)]
        oos.append(o.assign(pli=p))
        choix.append(dict(decl=decl, pli=p, stop=k, sortie=so, n_test=len(o),
                          win_test=(o['pnl'] > 0).mean() if len(o) else np.nan, r_test=o['r'].mean() if len(o) else np.nan))
    return pd.DataFrame(choix), pd.concat(oos, ignore_index=True)


def etape_wf():
    T = pd.read_pickle(os.path.join(OUT, 'trades_balayage.pkl'))
    cp = choix_panel(T)
    print('choix panel par pli :', cp)
    chp, resp = [], []
    for d in DECLS:
        c, o = selection_panel(T, d, cp)
        chp.append(c)
        if len(o):
            resp.append(dict(decl=d, **_stats_groupe(o).to_dict()))
    pd.concat(chp, ignore_index=True).to_csv(os.path.join(OUT, 'wf_panel_choix.csv'), index=False)
    RP = pd.DataFrame(resp).sort_values('r', ascending=False)
    RP.to_csv(os.path.join(OUT, 'wf_panel_resultats.csv'), index=False)
    print(RP.round(3).to_string())
    ch, res, allo = [], [], []
    for d in DECLS:
        c, o = selection_wf(T, d)
        ch.append(c)
        if len(o):
            allo.append(o)
            st = _stats_groupe(o)
            res.append(dict(decl=d, **st.to_dict(), n_gestions=o[['stop', 'sortie']].drop_duplicates().shape[0],
                            gestions=' | '.join('%g ATR + %s' % x for x in o[['stop', 'sortie']].drop_duplicates()
                                                .itertuples(index=False, name=None))))
    CH = pd.concat(ch, ignore_index=True); R = pd.DataFrame(res).sort_values('r', ascending=False)
    CH.to_csv(os.path.join(OUT, 'wf_choix.csv'), index=False)
    R.to_csv(os.path.join(OUT, 'wf_resultats.csv'), index=False)
    pd.concat(allo, ignore_index=True).to_pickle(os.path.join(OUT, 'wf_trades_oos.pkl'))
    # gestions FIXES (sans sélection) : chaque gestion appliquée telle quelle, résultat sur les 5 blocs de test
    fx = T[T['blk'] >= 3].groupby(['decl', 'stop', 'sortie']).apply(_stats_groupe, include_groups=False).reset_index()
    fx.to_csv(os.path.join(OUT, 'wf_fixes_blocs_test.csv'), index=False)
    print(R.to_string())
    return CH, R


# ═══════════════════════════════════════ final ═══════════════════════════════════════
def regles():
    return SIM.charge_regles()[VARIANTE]


def trades_complets(decl, choix):
    """Trades complets (colonnes du moteur) des plis de test, avec la gestion choisie à chaque pli."""
    ut, pk = DECLS[decl]
    out = []
    for P in DW.charger(ut):
        if decl not in P['decl']:
            continue
        bl = blocs(P)
        L, S = P['decl'][decl]
        for _, c in choix.iterrows():
            if c['sortie'] is None or (isinstance(c['sortie'], float) and np.isnan(c['sortie'])):
                continue
            g = gestion(P, float(c['stop']), c['sortie'], PLAGES[pk])
            m = bl == c['pli'] + 3
            T = M.backtest(P['df'], L & m, S & m, g, details=True)
            if len(T):
                T['serie'] = P['nom']; T['instrument'] = P['instrument']; T['pli'] = c['pli']
                T['gestion'] = '%g ATR + %s' % (c['stop'], c['sortie'])
                out.append(T)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def placebo_moteur(decl, choix, n=500, graine=11):
    """Référence des CONSIGNES : moteur.reference_hasard (même gestion, mêmes heures, même sens, même nombre de
    signaux), sur chaque série et chaque pli de test, tirages regroupés. Renvoie (tableau par tirage, trades)."""
    ut, pk = DECLS[decl]
    par_tirage = [[] for _ in range(n)]
    for P in DW.charger(ut):
        if decl not in P['decl']:
            continue
        bl = blocs(P)
        L, S = P['decl'][decl]
        for _, c in choix.iterrows():
            if c['sortie'] is None or (isinstance(c['sortie'], float) and np.isnan(c['sortie'])):
                continue
            m = bl == c['pli'] + 3
            if not (L & m).any() and not (S & m).any():
                continue
            # référence au hasard limitée aux barres du pli de test (même période que les trades réels)
            sub = P['df'][m]
            Pm = dict(P, c=P['c'][m], a=P['a'][m], lv={f: v[m] for f, v in P['lv'].items()})
            g2 = gestion(Pm, float(c['stop']), c['sortie'], PLAGES[pk])
            _, trs = M.reference_hasard(sub, n, g2, graine=graine + 7 * int(c['pli']), long=L[m], short=S[m],
                                        garder_trades=True)
            for q, t in enumerate(trs):
                if len(t):
                    par_tirage[q].append(t.assign(serie=P['nom']))
    tir = [pd.concat(t, ignore_index=True) if t else pd.DataFrame() for t in par_tirage]
    rows = []
    for t in tir:
        if not len(t):
            continue
        r = t['r'].to_numpy(); p = t['pnl_usd'].to_numpy()
        g_, l_ = r[r > 0].sum(), -r[r < 0].sum()
        rows.append(dict(n=len(t), win=(p > 0).mean(), r=r.mean(), pf_r=g_ / l_ if l_ > 0 else np.nan))
    return pd.DataFrame(rows), tir


def propfirm(T, tirages_ref, n_sim=1000):
    """Tradeify Select Flex : (a) taille en micros fixe via optimise_taille (critère valeur espérée),
    (b) risque fixe en $ ; même chose sur 20 tirages au hasard (même gestion) à la même taille."""
    R = regles()
    tab, best = SIM.optimise_taille(T, R, tailles=range(1, 21), n_sim=n_sim, graine=1)
    c = int(best['contrats'])
    ref = SIM.analyse_reference([t for t in tirages_ref[:20] if len(t)], R, contrats=c, n_sim=20 * 300)
    rq = []
    for risque in (100, 150, 200, 250, 300, 400):
        if (np.floor(risque / T['risque_usd'].astype(float)) > 0).sum() < 5:
            continue
        x = SIM.monte_carlo(T, R, risque_usd=risque, n_sim=n_sim, graine=2)
        rq.append(dict(risque=risque, p=x['p_reussite'], p1=x['p_1er_payout'], ve=x['valeur_esperee_usd'],
                       n=x['n_trades']))
    rq = pd.DataFrame(rq)
    bq = rq.sort_values('ve', ascending=False).iloc[0].to_dict() if len(rq) else {}
    refq = {}
    if bq:
        xs = [SIM.monte_carlo(t, R, risque_usd=bq['risque'], n_sim=300, graine=q) for q, t in
              enumerate(tirages_ref[:20]) if len(t) and (np.floor(bq['risque'] / t['risque_usd']) > 0).sum() >= 5]
        refq = dict(p=float(np.nanmean([x['p_reussite'] for x in xs])),
                    ve=float(np.nanmean([x['valeur_esperee_usd'] for x in xs])))
    return dict(contrats=c, p=best['p_reussite'], p1=best['p_1er_payout'], ve=best['valeur_esperee_usd'],
                delai=best.get('delai_median_jours'), p_ref=ref.get('p_reussite'), ve_ref=ref.get('valeur_esperee_usd'),
                p1_ref=ref.get('p_1er_payout'), risque=bq.get('risque'), p_rq=bq.get('p'), p1_rq=bq.get('p1'),
                ve_rq=bq.get('ve'), p_rq_ref=refq.get('p'), ve_rq_ref=refq.get('ve'))


def white_rc(B, T, n_boot=2000, graine=0):
    """Bootstrap de White sur TOUTES les combinaisons (déclencheur réel x gestion) du balayage dont le taux est dans
    la bande : statistique = R moyen par trade ; rééchantillonnage par blocs de 3 journées (série, jour) ; nulle =
    R moyen recentré. p = P(max des R recentrés >= R max observé)."""
    keep = B[(B['win'] >= BANDE[0]) & (B['win'] <= BANDE[1]) & (B['decl'] != 'hasard')][['decl', 'stop', 'sortie']]
    t = T.merge(keep, on=['decl', 'stop', 'sortie'])
    t = t.assign(jour=t['serie'] + '|' + pd.to_datetime(t['entree_t']).dt.strftime('%Y-%m-%d'))
    t['combo'] = t['decl'] + '|' + t['stop'].astype(str) + '|' + t['sortie']
    jours = np.sort(t['jour'].unique()); pos = {j: q for q, j in enumerate(jours)}
    combos = t['combo'].unique(); cpos = {c: q for q, c in enumerate(combos)}
    S = np.zeros((len(combos), len(jours))); N = np.zeros_like(S)
    np.add.at(S, (t['combo'].map(cpos).to_numpy(), t['jour'].map(pos).to_numpy()), t['r'].to_numpy())
    np.add.at(N, (t['combo'].map(cpos).to_numpy(), t['jour'].map(pos).to_numpy()), 1)
    obs = S.sum(1) / np.maximum(N.sum(1), 1)
    ok = N.sum(1) >= 20
    rng = np.random.default_rng(graine)
    nj = len(jours); bl = 3; nb = int(np.ceil(nj / bl))
    mx = np.empty(n_boot)
    for b in range(n_boot):
        deb = rng.integers(0, max(nj - bl + 1, 1), nb)
        ix = (deb[:, None] + np.arange(bl)).ravel()[:nj]
        m = S[:, ix].sum(1) / np.maximum(N[:, ix].sum(1), 1)
        mx[b] = (m - obs)[ok].max()
    best = int(np.argmax(np.where(ok, obs, -9)))
    p = float((1 + (mx >= obs[best]).sum()) / (1 + n_boot))
    return dict(n_combos=int(ok.sum()), meilleur=combos[best], r_max=float(obs[best]), p_white=p,
                seuil95=float(np.percentile(mx, 95)))


def _tache_final(args):
    mode, d, ch, n_plac = args
    Tc = trades_complets(d, ch)
    if not len(Tc):
        return None
    m = M.metriques(Tc, n_boot=500)
    pl, tirs = placebo_moteur(d, ch, n=n_plac)
    row = dict(mode=mode, decl=d, n=m['n'], win=m['pct_gagnants'], r=m['r_moyen'], r_ic_bas=m['r_ic95'][0],
               r_ic_haut=m['r_ic95'][1], pf_usd=m['pf'],
               pf_r=float(Tc['r'][Tc['r'] > 0].sum() / max(-Tc['r'][Tc['r'] < 0].sum(), 1e-9)),
               win_plac=float(pl['win'].mean()), r_plac=float(pl['r'].mean()),
               p_win=float((1 + (pl['win'] >= m['pct_gagnants'] - 1e-12).sum()) / (1 + len(pl))),
               p_r=float((1 + (pl['r'] >= m['r_moyen'] - 1e-12).sum()) / (1 + len(pl))), n_tirages=len(pl),
               gestions=' | '.join(sorted(Tc['gestion'].unique())))
    row['ecart_win_pts'] = 100 * (row['win'] - row['win_plac'])
    row['criteres_1_3'] = bool((row['n'] >= 60) and BANDE[0] <= row['win'] <= BANDE[1] and row['r'] > 0
                               and row['pf_r'] > 1 and row['p_win'] <= 0.05)
    if (row['win'] >= 0.55 and row['r'] > 0) or d in ('clx_buy', 'A_clx_trend', 'hei', 'ML-0001', 'hasard'):
        pf = propfirm(Tc, tirs)
        row.update({'pf_' + k: v for k, v in pf.items()})
    Tc.to_pickle(os.path.join(OUT, 'final_trades_%s_%s.pkl' % (mode, d)))
    return row


def etape_final(n_plac=500):
    t0 = time.time()
    B = pd.read_csv(os.path.join(OUT, 'balayage.csv'))
    T = pd.read_pickle(os.path.join(OUT, 'trades_balayage.pkl'))
    W = white_rc(B, T)
    pickle.dump(W, open(os.path.join(OUT, 'white.pkl'), 'wb'))
    print('White RC :', W, flush=True)
    taches = []
    for mode, f in (('declencheur', 'wf_choix.csv'), ('panel', 'wf_panel_choix.csv')):
        CH = pd.read_csv(os.path.join(OUT, f))
        for d in DECLS:
            ch = CH[(CH['decl'] == d) & CH['sortie'].notna()]
            if len(ch):
                taches.append((mode, d, ch, n_plac))
    rows = []
    with ProcessPoolExecutor(max_workers=9) as ex:
        for row in ex.map(_tache_final, taches):
            if row:
                rows.append(row)
                print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    F = pd.DataFrame(rows)
    F.to_csv(os.path.join(OUT, 'final.csv'), index=False)
    print('final : %.0f s' % (time.time() - t0))
    return F, W


if __name__ == '__main__':
    etapes = sys.argv[1:] or ['verif', 'balayage', 'synthese', 'wf', 'final']
    if 'verif' in etapes:
        etape_verif()
    if 'balayage' in etapes:
        etape_balayage()
    if 'synthese' in etapes:
        etape_synthese()
    if 'wf' in etapes:
        etape_wf()
    if 'final' in etapes:
        etape_final()
