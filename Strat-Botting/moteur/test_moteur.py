"""Tests unitaires du moteur sur barres construites à la main.   ~/venv-quant/bin/python test_moteur.py"""
import os
import sys
import tempfile
import time
import unittest
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moteur as M  # noqa: E402
import registre as RG  # noqa: E402


def barres_main(debut, ut, ohlc, atr=10.0):
    """ohlc : liste de (o, h, l, c) ; horodatage = ouverture, heure de Paris."""
    t = pd.date_range(pd.Timestamp(debut, tz='Europe/Paris'), periods=len(ohlc), freq='%dmin' % ut)
    o, h, l, c = map(list, zip(*ohlc))
    return pd.DataFrame(dict(open=o, high=h, low=l, close=c, atr=atr), index=t)


def sig(n, *ix):
    s = np.zeros(n, bool)
    s[list(ix)] = True
    return s


PLAT = (100, 101, 99, 100)
G0 = dict(instrument='MNQ', heure_sortie=None, arrondi_tick=False, stop={'mode': 'atr', 'k': 1.0})


class TestExecution(unittest.TestCase):
    def test_entree_ouverture_suivante_et_couts(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 101, 99, 100.5), PLAT, PLAT])
        T = M.backtest(df, long=sig(4, 0), gestion=dict(G0, sortie_barres=1))
        self.assertEqual(len(T), 1)
        t = T.iloc[0]
        self.assertEqual(t.entree_t, df.index[1])
        self.assertAlmostEqual(t.prix_entree, 100.25)          # ouverture + 1 tick
        self.assertAlmostEqual(t.prix_sortie, 99.75)           # ouverture barre 2 - 1 tick
        self.assertEqual(t.motif_sortie, 'temps')
        self.assertAlmostEqual(t.pnl_usd, -0.5 * 2 - 2 * 0.62)  # -0,5 pt x 2 $ - commissions
        self.assertAlmostEqual(t.risque_usd, 10 * 2)
        self.assertAlmostEqual(t.r, t.pnl_usd / 20)
        self.assertListEqual(list(T.columns), M.COLONNES_TRADES)
        # colonnes du dataset (o/h/l/c = vrais prix, ha_* ignorées)
        d2 = df.rename(columns={'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c'}).assign(ha_o=0.0, ha_c=0.0)
        pd.testing.assert_frame_equal(M.backtest(d2, long=sig(4, 0), gestion=dict(G0, sortie_barres=1)), T)

    def test_sl_et_tp_meme_barre_donne_sl(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 125, 85, 110), PLAT])
        T = M.backtest(df, long=sig(3, 0), gestion=dict(G0, objectif={'mode': 'R', 'k': 2.0}))
        t = T.iloc[0]
        self.assertEqual(t.motif_sortie, 'stop')
        self.assertAlmostEqual(t.stop_initial, 90.25)
        self.assertAlmostEqual(t.objectif, 120.25)
        self.assertAlmostEqual(t.prix_sortie, 90.0)
        self.assertAlmostEqual(t.mae_usd, (90.25 - 100.25) * 2)   # bornée au stop
        self.assertAlmostEqual(t.mfe_usd, (125 - 100.25) * 2)

    def test_objectif_exige_un_tick_de_depassement(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 120.25, 99, 110), (110, 120.5, 109, 115), PLAT])
        T = M.backtest(df, long=sig(4, 0), gestion=dict(G0, objectif={'mode': 'R', 'k': 2.0}))
        t = T.iloc[0]
        self.assertEqual(t.motif_sortie, 'objectif')
        self.assertEqual(t.sortie_t, df.index[2])
        self.assertAlmostEqual(t.prix_sortie, 120.25)

    def test_ecart_a_travers_le_stop(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 101, 99, 100), (80, 82, 78, 81), PLAT])
        t = M.backtest(df, long=sig(4, 0), gestion=G0).iloc[0]
        self.assertEqual(t.motif_sortie, 'stop')
        self.assertAlmostEqual(t.prix_sortie, 79.75)          # ouverture 80 - 1 tick, pas le stop 90.25
        self.assertEqual(t.sortie_t, df.index[2])

    def test_short_symetrique(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 101, 99, 100), (120, 121, 119, 120), PLAT])
        t = M.backtest(df, short=sig(4, 0), gestion=G0).iloc[0]
        self.assertEqual(t.sens, 'short')
        self.assertAlmostEqual(t.prix_entree, 99.75)
        self.assertAlmostEqual(t.stop_initial, 109.75)
        self.assertAlmostEqual(t.prix_sortie, 120.25)

    def test_break_even(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 111, 99.5, 108), (108, 109, 99, 100), PLAT])
        g = dict(G0, break_even={'R': 1.0, 'ticks': 1})
        t = M.backtest(df, long=sig(4, 0), gestion=g).iloc[0]
        self.assertEqual(t.motif_sortie, 'stop_be')
        self.assertAlmostEqual(t.prix_sortie, 100.25)          # BE 100.5 - 1 tick
        self.assertAlmostEqual(t.stop_initial, 90.25)
        # le BE ne s'applique pas sur la barre où il est déclenché (actif à la suivante)
        df2 = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 111, 95, 108), (108, 109, 107, 108), PLAT])
        t2 = M.backtest(df2, long=sig(4, 0), gestion=dict(g, sortie_barres=2)).iloc[0]
        self.assertEqual(t2.motif_sortie, 'temps')

    def test_suiveur_atr(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 130, 99, 128), (128, 129, 118, 120), PLAT])
        g = dict(G0, stop={'mode': 'atr', 'k': 2.0}, suiveur={'k': 1.0})
        t = M.backtest(df, long=sig(4, 0), gestion=g).iloc[0]
        self.assertEqual(t.motif_sortie, 'stop_suiveur')
        self.assertAlmostEqual(t.prix_sortie, 120 - 0.25)      # 130 - 1 ATR = 120

    def test_sortie_signal_et_partiel(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 111, 99, 105), (105, 106, 104, 105), (104, 105, 103, 104)])
        g = dict(G0, sortie_signal={'long': sig(4, 2)}, partiel={'R': 1.0, 'fraction': 0.5, 'be_apres': False})
        t = M.backtest(df, long=sig(4, 0), gestion=g).iloc[0]
        self.assertEqual(t.motif_sortie, 'partiel+signal')
        self.assertAlmostEqual(t.prix_sortie, 103.75)
        pts = 0.5 * (110.25 - 100.25) + 0.5 * (103.75 - 100.25)
        self.assertAlmostEqual(t.pnl_usd, pts * 2 - 1.24)

    def test_stop_niveau_et_repli(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, PLAT, PLAT, PLAT, PLAT, PLAT])
        niv = np.array([95.0, np.nan, 99.9, np.nan, np.nan, np.nan])
        g = dict(G0, sortie_barres=1, stop={'mode': 'niveau', 'long': {'pivot': niv}, 'marge_ticks': 2,
                                            'min_atr': 0.25, 'max_atr': 3.0, 'repli_k': 2.0})
        T = M.backtest(df, long=sig(6, 0, 2, 4), gestion=g)
        self.assertEqual(list(T.niveau_stop), ['niveau:pivot', 'repli_atr2', 'repli_atr2'])
        self.assertAlmostEqual(T.stop_initial.iloc[0], 94.5)
        T2 = M.backtest(df, long=sig(6, 0, 2, 4), gestion=dict(g, stop=dict(g['stop'], sauter=True)))
        self.assertEqual(len(T2), 1)

    def test_objectif_niveau(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 116, 99, 115), PLAT])
        lv = {'r1': np.full(3, 105.0), 'r2': np.full(3, 115.0)}
        g = dict(G0, objectif={'mode': 'niveau', 'long': lv, 'ratio_min': 1.0, 'si_absent': 'sauter'})
        t = M.backtest(df, long=sig(3, 0), gestion=g).iloc[0]
        self.assertEqual(t.niveau_objectif, 'niveau:r2')        # r1 < 1 R : écarté
        self.assertAlmostEqual(t.prix_sortie, 115.0)

    def test_entree_limite(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 101, 98.5, 99), (99, 99.5, 97.5, 98), PLAT, PLAT])
        lim = np.full(5, 98.0)
        g = dict(G0, entree={'mode': 'limite', 'long': lim, 'validite': 3}, sortie_barres=1)
        t = M.backtest(df, long=sig(5, 0), gestion=g).iloc[0]
        self.assertEqual(t.entree_t, df.index[2])                # barre 1 : 98.5 > 98 - 1 tick
        self.assertAlmostEqual(t.prix_entree, 98.0)
        g2 = dict(g, entree={'mode': 'limite', 'long': np.full(5, 90.0), 'validite': 3})
        self.assertEqual(len(M.backtest(df, long=sig(5, 0), gestion=g2)), 0)

    def test_une_position_et_max_par_jour(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT] * 12)
        g = dict(G0, sortie_barres=2)
        T = M.backtest(df, long=sig(12, 0, 1, 2, 3, 6), gestion=g)
        self.assertEqual(list(T.entree_t), [df.index[1], df.index[3], df.index[7]])
        T2 = M.backtest(df, long=sig(12, 0, 1, 2, 3, 6), gestion=dict(g, max_trades_jour=2))
        self.assertEqual(len(T2), 2)

    def test_trou_de_donnees_pas_d_entree(self):
        df = barres_main('2026-01-05 10:00', 15, [PLAT] * 4)
        df.index = df.index[:2].append(df.index[2:] + pd.Timedelta(hours=3))
        self.assertEqual(len(M.backtest(df, long=sig(4, 1), gestion=dict(G0, sortie_barres=1))), 0)
        self.assertEqual(len(M.backtest(df, long=sig(4, 0), gestion=dict(G0, sortie_barres=1))), 1)


class TestHeure(unittest.TestCase):
    def test_sortie_forcee_hiver(self):
        # janvier : 15:59 Chicago = 22:59 Paris -> sortie à la clôture de la barre 22:30 (22:45)
        df = barres_main('2026-01-06 22:00', 15, [PLAT, PLAT, (100, 101, 99, 100.5), PLAT, PLAT, PLAT])
        T = M.backtest(df, long=sig(6, 0), gestion=dict(G0, heure_sortie='15:59'))
        t = T.iloc[0]
        self.assertEqual(t.motif_sortie, 'heure')
        self.assertEqual(t.sortie_t, pd.Timestamp('2026-01-06 22:45', tz='Europe/Paris'))
        self.assertAlmostEqual(t.prix_sortie, 100.25)
        # pas d'entrée sur la barre de sortie forcée ni dans [15:59, 17:00) Chicago
        self.assertEqual(len(M.backtest(df, long=sig(6, 1, 3), gestion=dict(G0, heure_sortie='15:59'))), 0)

    def test_sortie_forcee_semaine_decalee(self):
        # 10/03/2026 : heure d'été US (depuis le 08/03), pas encore en Europe -> 15:59 Chicago = 21:59 Paris
        df = barres_main('2026-03-10 21:00', 15, [PLAT] * 6)
        t = M.backtest(df, long=sig(6, 0), gestion=dict(G0, heure_sortie='15:59')).iloc[0]
        self.assertEqual(t.sortie_t, pd.Timestamp('2026-03-10 21:45', tz='Europe/Paris'))
        # été (juillet) : 22:59 Paris de nouveau
        df = barres_main('2026-07-07 22:00', 15, [PLAT] * 6)
        t = M.backtest(df, long=sig(6, 0), gestion=dict(G0, heure_sortie='15:59')).iloc[0]
        self.assertEqual(t.sortie_t, pd.Timestamp('2026-07-07 22:45', tz='Europe/Paris'))

    def test_plage_interdite(self):
        df = barres_main('2026-01-06 08:00', 15, [PLAT] * 8)
        g = dict(G0, sortie_barres=1, plages_interdites=[('08:00', '08:30')])
        T = M.backtest(df, long=sig(8, 0, 1, 2, 4), gestion=g)
        self.assertEqual(list(T.entree_t), [df.index[2], df.index[3], df.index[5]])  # 08:15 refusée


class TestMultiUT(unittest.TestCase):
    def setUp(self):
        n15 = 8
        self.s15 = barres_main('2026-01-06 10:00', 15, [PLAT] * n15, atr=np.arange(1, n15 + 1) * 1.0)
        self.e5 = barres_main('2026-01-06 10:00', 5, [(100 + k, 100.5 + k, 99.5 + k, 100 + k) for k in range(24)])
        self.e2 = barres_main('2026-01-06 10:00', 2, [PLAT] * 60)

    def test_entree_apres_cloture_15m(self):
        g = dict(G0, sortie_barres=1)
        t = M.backtest(self.e5, long=sig(8, 1), gestion=g, df_signal=self.s15).iloc[0]
        self.assertEqual(t.entree_t, pd.Timestamp('2026-01-06 10:30', tz='Europe/Paris'))  # clôture de 10:15
        self.assertAlmostEqual(t.prix_entree, 106 + 0.25)                             # ouverture 5m de 10:30
        self.assertAlmostEqual(t.risque_usd, 2.0 * 2)                                 # ATR de la barre signal 1
        t2 = M.backtest(self.e2, long=sig(8, 1), gestion=g, df_signal=self.s15).iloc[0]
        self.assertEqual(t2.entree_t, pd.Timestamp('2026-01-06 10:30', tz='Europe/Paris'))
        t3 = M.backtest(self.e2, long=sig(8, 0), gestion=g, df_signal=self.s15).iloc[0]
        self.assertEqual(t3.entree_t, pd.Timestamp('2026-01-06 10:16', tz='Europe/Paris'))  # 1re barre 2m >= 10:15

    def test_pas_de_fuite_du_futur(self):
        g = dict(G0, sortie_barres=3)
        L = sig(8, 2)
        ref = M.backtest(self.e5, long=L, gestion=g, df_signal=self.s15)
        fut = self.s15.copy()
        fut.iloc[3:, :] = fut.iloc[3:, :] * 3       # on change tout le futur de la barre signal
        L2 = L.copy(); L2[3:] = True
        alt = M.backtest(self.e5, long=L2, gestion=g, df_signal=fut)
        pd.testing.assert_series_equal(ref.iloc[0], alt.iloc[0], check_names=False)

    def test_sortie_signal_meme_barre_que_entree_ignoree(self):
        g = dict(G0, sortie_signal={'long': sig(8, 1, 3)})
        t = M.backtest(self.e5, long=sig(8, 1), gestion=g, df_signal=self.s15).iloc[0]
        self.assertEqual(t.motif_sortie, 'signal')
        self.assertEqual(t.sortie_t, pd.Timestamp('2026-01-06 11:00', tz='Europe/Paris'))  # clôture 15m de 10:45


class TestOutils(unittest.TestCase):
    def marche(self, n=40000, graine=1):
        rng = np.random.default_rng(graine)
        t = pd.date_range(pd.Timestamp('2024-01-02 00:00', tz='Europe/Paris'), periods=n, freq='15min')
        c = 15000 + np.cumsum(rng.normal(0, 8, n)).round(2)
        o = np.r_[c[0], c[:-1]]
        h = np.maximum(o, c) + rng.exponential(4, n); l = np.minimum(o, c) - rng.exponential(4, n)
        r = lambda x: np.round(x * 4) / 4
        return pd.DataFrame(dict(open=r(o), high=r(h), low=r(l), close=r(c)), index=t)

    def test_performance_40000_barres(self):
        df = self.marche()
        rng = np.random.default_rng(2)
        L = rng.random(len(df)) < 0.02; S = rng.random(len(df)) < 0.02
        X = rng.random(len(df)) < 0.1
        g = dict(instrument='MNQ', stop={'mode': 'atr', 'k': 2.0}, objectif={'mode': 'R', 'k': 3.0},
                 break_even={'R': 1.0}, suiveur={'k': 3.0, 'activation_R': 1.5},
                 sortie_signal={'long': X, 'short': X}, sortie_barres=40)
        M.backtest(df, L, S, g)          # préparation (ATR, fuseaux) mise en cache
        t0 = time.perf_counter()
        T = M.backtest(df, L, S, g)
        dt = time.perf_counter() - t0
        print('\n  40 000 barres, %d trades : %.3f s' % (len(T), dt))
        self.assertLess(dt, 1.0)
        m = M.metriques(T)
        self.assertEqual(m['n'], len(T))
        self.assertTrue(m['r_ic95'][0] <= m['r_moyen'] <= m['r_ic95'][1])

    def test_reference_hasard(self):
        df = self.marche(6000)
        L = np.zeros(len(df), bool); L[200::97] = True
        g = dict(instrument='MNQ', stop={'mode': 'atr', 'k': 2.0}, sortie_barres=8)
        R = M.reference_hasard(df, 20, g, graine=3, long=L)
        n_reel = len(M.backtest(df, L, None, g))
        self.assertEqual(len(R), 20)
        self.assertTrue(abs(R['n'].mean() - n_reel) / n_reel < 0.15)
        self.assertTrue(0 < M.p_hasard(R, 0.0) <= 1)

    def test_decoupage_et_walk_forward(self):
        df = self.marche(8000)
        dev, sce = M.decoupage(df)
        self.assertEqual(len(dev) + len(sce), len(df))
        self.assertLess(dev.index.max(), sce.index.min())
        self.assertTrue(0.72 < len(dev) / len(df) < 0.78)
        self.assertEqual(len(M.charger_recherche(df)), len(dev))
        wf = M.walk_forward(dev, k=4, ratio=3)
        self.assertEqual(len(wf), 4)
        for a, b in wf:
            self.assertLess(a.index.max(), b.index.min())


def _ecrire(args):
    dossier, agent, k = args
    return RG.ajouter_test(dict(agent=agent, famille='test', recette='r%d' % k), dossier=dossier)


class TestRegistre(unittest.TestCase):
    def test_ecritures_concurrentes(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'registre_tests.csv'), 'w') as fh:
                fh.write(','.join(RG.CHAMPS) + '\n')
            with Pool(4) as p:
                ids = p.map(_ecrire, [(d, 'tendance' if k % 2 else 'Cassure', k) for k in range(20)])
            self.assertEqual(len(set(ids)), 20)
            R = pd.read_csv(os.path.join(d, 'registre_tests.csv'))
            self.assertEqual(len(R), 20)
            self.assertEqual(sorted(R.id)[:2], ['CAS-0001', 'CAS-0002'])
            df = barres_main('2026-01-05 10:00', 15, [PLAT, (100, 125, 85, 110), PLAT])
            T = M.backtest(df, long=sig(3, 0), gestion=G0)
            i = RG.ajouter_test(dict(agent='tendance', trades=T, verdict='test'), dossier=d)
            self.assertEqual(i, 'TEN-0011')
            self.assertTrue(os.path.exists(os.path.join(d, 'trades', 'TEN-0011.csv')))
            R = pd.read_csv(os.path.join(d, 'registre_tests.csv'))
            self.assertEqual(int(R.iloc[-1].n_trades), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
