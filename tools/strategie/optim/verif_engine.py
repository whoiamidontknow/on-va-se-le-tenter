"""Concordance de l'optimiseur avec tools/strategie/engine.py sur les préréglages A, B, C de STRATEGIE_V1.

Mode « compatible engine.py » : chauffe 101 barres (entrées i > 100 comme strat.py), sortie Heishinator
« etat » (couleur opposée), pas de blackout général, pas de maximum par jour. On compare trade par trade
(même barre signal, même sens, même R).

  python tools/strategie/optim/verif_engine.py --data "/Users/jeremk/Jeu 15:10" --tf 15
"""
import os, sys, argparse, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import donnees, espace, univers, optimiseur
import engine as EN, strat as ST

PRESETS = {
    'A': (dict(declencheur='climax', e_sens_in='Long seulement', f_trTf='60', x_atrK_in=2.0, x_oppHei_in=True),
          'clx', dict(stop=('atr', 2.0), exit_on=ST.x_heishi, filt=ST.f_and(ST.f_trend, lambda S, i, d: d == 1))),
    'B': (dict(declencheur='fleche_fort', f_trTf='60', fenetre='hors_londres', x_atrK_in=1.0, x_oppHei_in=True),
          'sigF', dict(stop=('atr', 1.0), exit_on=ST.x_heishi, filt=ST.f_trend, sessions=('ASIE', 'US', 'SOIR'))),
    'C': (dict(declencheur='trendline', fenetre='hors_londres', x_atrK_in=1.5, x_tpR_in=2.0),
          'tl', dict(stop=('atr', 1.5), target=2, sessions=('ASIE', 'US', 'SOIR'))),
}
ENGSYM = {'MES': 'MES', 'NQ': 'NQZ', 'API': 'API'}


def neutre():
    return dict(declencheur='trendline', e_sens_in='Les deux', f_trTf='aucun', f_emaOn_in=False, fenetre='aucune',
                f_boOn=False, f_adxMin=0, atr_rel_min=0.0, f_maxJour=0, f_detK=0.0, f_clxOn_in=False, f_clxAge=0,
                f_feuSeuil=0, entree='marche', limite_validite=2, x_stopMode_in='ATR × k', x_atrK_in=1.5, x_swL=5,
                x_swR=2, x_swMarge=2, x_fixPts=0, x_tpR_in=0.0, x_trMode_in='Aucun', x_trK=2.0, x_trAct=0.0, x_beR=0.0,
                x_beTk=1, x_oppArr_in=False, x_oppHei_in=False, x_fin='aucune', temps_max_barres=0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', nargs='+', required=True)
    ap.add_argument('--tf', default='15')
    ap.add_argument('--symboles', default='')
    ap.add_argument('--api', action='store_true')
    a = ap.parse_args(argv)
    cfg = espace.lire_config(os.path.join(HERE, 'config.toml'))
    cfg = copy.deepcopy(cfg)
    cfg['execution']['heishi_sortie'] = 'etat'
    cfg['execution']['remplissage'] = 'prudent'
    syms = [s for s in a.symboles.split(',') if s] or None
    S, _ = donnees.charger(a.data, a.tf, syms, cfg['instruments'], cache_dir=os.path.join(HERE, 'cache'),
                           api=True if a.api else None)
    htf = ST.HTF[S[0]['tfm']]            # engine.py : TREND de l'unité « supérieure » (15 -> 60, 2 -> 10...)
    cfg['donnees']['unites_trend'] = sorted(set(cfg['donnees']['unites_trend']) | {htf})
    cfg['espace']['f_trTf'] = sorted(set(cfg['espace']['f_trTf']) | {str(htf)}, key=lambda v: (v != 'aucun', v))
    U = univers.Univers(S, cfg['instruments'], cfg['donnees']['unites_trend'], warmup=101)
    esp = espace.Espace(cfg, S[0]['tfm'])
    for k in PRESETS:
        if 'f_trTf' in PRESETS[k][0]:
            PRESETS[k][0]['f_trTf'] = str(htf)
    ev = optimiseur.Evaluateur(U, esp, cfg, log=lambda *x: None)
    tot_ok = tot = 0
    for name, (over, ent, kw) in PRESETS.items():
        c = dict(neutre(), **over)
        T = ev.trades(c)
        mine = {}
        for i in range(len(T['g'])):
            s = U.series[T['sid'][i]]
            mine[(int(T['sid'][i]), int(T['g'][i] - s['off']), int(T['d'][i]))] = float(T['R'][i])
        eng = {}
        for sid, Sx in enumerate(S):
            Sx = dict(Sx); Sx['sym'] = ENGSYM.get(Sx['racine'], 'MES')
            for t in EN.run(Sx, ST.ENTRIES[ent](Sx), **kw):
                i = Sx['T'].index(t['t'])
                eng[(sid, i, t['d'])] = t['R']
        com = set(mine) & set(eng)
        dif = [k for k in com if abs(mine[k] - eng[k]) > 1e-6]
        me = np.mean(list(mine.values())) if mine else np.nan
        ee = np.mean(list(eng.values())) if eng else np.nan
        print('Préréglage %s : engine.py n=%d moyR %+.4f | optimiseur n=%d moyR %+.4f | communs %d, R différents %d, '
              'seulement engine %d, seulement optimiseur %d' % (name, len(eng), ee, len(mine), me, len(com), len(dif),
                                                               len(set(eng) - set(mine)), len(set(mine) - set(eng))))
        for k in sorted(set(eng) ^ set(mine))[:5]:
            print('   écart', k, 'engine' if k in eng else 'optimiseur', eng.get(k, mine.get(k)))
        for k in dif[:5]:
            print('   R', k, eng[k], mine[k])
        tot += len(set(eng) | set(mine)); tot_ok += len(com) - len(dif)
    print('CONCORDANCE : %d / %d trades identiques' % (tot_ok, tot))
    return tot_ok, tot


if __name__ == '__main__':
    main()
