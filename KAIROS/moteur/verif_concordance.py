"""Concordance trade par trade du moteur neuf avec tools/strategie/engine.py (moteur de référence du projet,
lui-même concordant avec optim/moteur.py) sur les exports « Jeu 15:10 » (NQ + MES, 15 min, vrais prix
reconstitués depuis le HA) et sur toutes les séries de tools/strategie/cache_series.pkl, préréglages A
(et C en bonus).

    ~/venv-quant/bin/python verif_concordance.py

Réglages du moteur neuf pour reproduire les conventions de engine.py :
commission 1,25 $/côté, NQ à 20 $/pt (engine.py traite NQ comme le mini), pas de sortie forcée à l'heure,
pas d'arrondi au tick (engine.py n'arrondit pas), trade ouvert en fin de série abandonné, et pour C :
glissement aussi sur l'ordre objectif (engine.py remplit l'objectif à objectif - 1 tick).
Les caches de séries de tools/strategie/optim/cache sont COPIÉS dans un dossier temporaire (lecture seule).
"""
import glob
import os
import shutil
import sys
import tempfile
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(HERE, '..', '..'))
STRAT = os.path.join(RACINE, 'tools', 'strategie')
sys.path[:0] = [HERE, STRAT, os.path.join(STRAT, 'optim')]
import moteur as M          # noqa: E402
import engine as EN         # noqa: E402
import strat as ST          # noqa: E402
import donnees              # noqa: E402

ENGSYM = {'MES': 'MES', 'NQ': 'NQZ'}
POINT = {'MES': 5.0, 'NQ': 20.0}


def charger():
    """Les 32 séries de tools/strategie/cache_series.pkl (tous les exports HA, 1 min -> 1D, MES/MES1/NQZ) +
    les 2 séries 15 min de « Jeu 15:10 » (cache de l'optimiseur)."""
    import pickle
    S = [s for s in pickle.load(open(os.path.join(STRAT, 'cache_series.pkl'), 'rb')) if s['tfm'] in ST.HTF]
    for s in S:
        s['racine'] = {'NQZ': 'NQ', 'MES1': 'MES'}.get(s['sym'], s['sym'])
    tmp = tempfile.mkdtemp()
    for f in glob.glob(os.path.join(STRAT, 'optim', 'cache', '*.pkl')):
        shutil.copy(f, tmp)
    S2, _ = donnees.charger(['/Users/jeremk/Jeu 15:10'], '15', None, {}, cache_dir=tmp, log=lambda *a: None)
    return S + S2


def vers_df(S):
    atr = np.array([np.nan if x is None else x for x in S['ratr']], float)
    return pd.DataFrame(dict(open=S['ro'], high=S['rh'], low=S['rl'], close=S['rc'], atr=atr), index=pd.DatetimeIndex(S['T']))


def comparer(nom, S_list, f_ent, kw_engine, f_gestion, verbeux=False):
    tot = ok = 0
    lignes = []
    temps = 0.0
    for sid, S in enumerate(S_list):
        Sx = dict(S); Sx['sym'] = ENGSYM.get(S['racine'], 'MES') if S['sym'] not in EN.SPEC else S['sym']
        ST.ensure_htf(Sx)
        ref = EN.run(Sx, f_ent(Sx), **kw_engine)
        eng = {(Sx['T'][Sx['T'].index(t['t']) + 1]): t for t in ref}
        df = vers_df(Sx)
        L, Sh, g = f_gestion(Sx)
        g = dict(g, instrument=dict(point=POINT[S['racine']], tick=0.25, commission_cote=1.25), heure_sortie=None,
                 arrondi_tick=False, fin_donnees='abandon')
        M.backtest(df, L, Sh, g)
        t0 = time.perf_counter()
        T = M.backtest(df, L, Sh, g)
        temps += time.perf_counter() - t0
        neuf = {row.entree_t: row for row in T.itertuples()}
        cles = sorted(set(eng) | set(neuf))
        for k in cles:
            a, b = eng.get(k), neuf.get(k)
            tot += 1
            if a is not None and b is not None and abs(a['R'] - b.r) < 1e-9 and abs(a['usd'] - b.pnl_usd) < 1e-6:
                ok += 1
            else:
                lignes.append((S['racine'], k, None if a is None else (round(a['R'], 4), a['why']),
                               None if b is None else (round(b.r, 4), b.motif_sortie)))
        if verbeux:
            print('  %s série %d (%s %s, %d barres) : engine.py %d trades, moteur %d trades'
                  % (nom, sid, S['sym'], S['tf'], S['n'], len(eng), len(neuf)))
    print('%s : %d / %d trades identiques (même barre d\'entrée, même sens, même R, même $) — moteur %.3f s'
          % (nom, ok, tot, temps))
    for x in lignes[:10]:
        print('   écart', x)
    return ok, tot


def main():
    S_list = charger()
    print('%d séries chargées' % len(S_list))

    # ---- préréglage A : climax BUY + TREND 1H, long seul, stop 2 ATR, sortie Heishinator (couleur opposée)
    def gA(S):
        n = S['n']
        L = np.array([i > 100 and S['clx'][i] == 1 and ST.f_trend(S, i, 1) for i in range(n)])
        sortie = ~np.asarray(S['bull'], bool)
        return L, None, dict(stop={'mode': 'atr', 'k': 2.0}, sortie_signal={'long': sortie})
    kwA = dict(stop=('atr', 2.0), exit_on=ST.x_heishi, filt=ST.f_and(ST.f_trend, lambda S, i, d: d == 1))
    okA, totA = comparer('Préréglage A', S_list, ST.e_clx, kwA, gA)

    # ---- préréglage C : cassure de trendline hors Londres, stop 1,5 ATR, objectif 2 R
    def gC(S):
        n = S['n']
        hors = np.array([EN.sess_of(t) in ('ASIE', 'US', 'SOIR') for t in S['T']])
        L = np.zeros(n, bool); Sh = np.zeros(n, bool)
        for i, d in ST.e_tl(S):
            if hors[i]:
                (L if d == 1 else Sh)[i] = True
        return L, Sh, dict(stop={'mode': 'atr', 'k': 1.5}, objectif={'mode': 'R', 'k': 2.0},
                           glissement_sur_limites=True)
    kwC = dict(stop=('atr', 1.5), target=2, sessions=('ASIE', 'US', 'SOIR'))
    okC, totC = comparer('Préréglage C', S_list, ST.e_tl, kwC, gC)
    print('CONCORDANCE TOTALE : %d / %d' % (okA + okC, totA + totC))


if __name__ == '__main__':
    main()
