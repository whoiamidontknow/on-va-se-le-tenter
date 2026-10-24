"""Tests du simulateur propfirm (cas construits à la main).

    ~/venv-quant/bin/python -m unittest test_simulateur -v     (depuis KAIROS/propfirm)
"""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simulateur as S  # noqa: E402


def trades(*jours):
    """jours = liste de journées ; chaque journée = liste de (pnl, mae, mfe) pour 1 contrat.
    Journée i = i-ème jour ouvré à partir du lundi 05/01/2026, trades à 15h30, 15h45... Paris."""
    dates = pd.bdate_range("2026-01-05", periods=len(jours))
    lignes = []
    for d, jour in zip(dates, jours):
        for k, (pnl, mae, mfe) in enumerate(jour):
            e = d + pd.Timedelta(hours=15, minutes=30 + 20 * k)
            lignes.append({"entree_t": e, "sortie_t": e + pd.Timedelta(minutes=15), "sens": "long",
                           "pnl_usd": pnl, "mae_usd": mae, "mfe_usd": mfe})
    return pd.DataFrame(lignes)


def regles(**kw):
    base = dict(nom="test", capital=50_000, objectif_eval_usd=3_000, drawdown_usd=2_500,
                drawdown_type="intraday_trailing", drawdown_plafond_usd=None,
                perte_journaliere_usd=0, perte_journaliere_type="none", jours_min_eval=1,
                consistance_eval_pct=0, consistance_funded_pct=0, jours_min_avant_payout=1,
                payout_min_usd=500, gain_min_jour_payout_usd=0, frais_eval_usd=100,
                frais_activation_usd=0, coussin_payout_usd=2_600, partage_pct=100)
    base.update(kw)
    return S.Regles(**base)


class TestDrawdown(unittest.TestCase):
    def test_echec_par_mae_trade_gagnant_intraday(self):
        # Le trade finit +1 000 $ mais touche −2 600 $ latents : seuil 47 500 franchi.
        r = S.simule_chemin(trades([(1000, -2600, 1200)]), regles(), ordre="optimiste")
        self.assertEqual(r["res_eval"], -1)

    def test_pic_latent_fait_monter_le_seuil_avant_le_creux(self):
        # MFE +1 200 puis MAE −2 400 : seuil monté à 48 700, creux à 47 600 -> échec en intraday...
        t = trades([(1000, -2400, 1200)])
        self.assertEqual(S.simule_chemin(t, regles(), ordre="prudent")["res_eval"], -1)
        # ... mais pas si le creux vient d'abord (47 600 > 47 500)
        self.assertEqual(S.simule_chemin(t, regles(), ordre="optimiste")["res_eval"], -3)
        # ... ni en EOD trailing (seuil fixe dans la journée = 47 500)
        r = S.simule_chemin(t, regles(drawdown_type="eod_trailing"), ordre="prudent")
        self.assertNotEqual(r["res_eval"], -1)
        self.assertAlmostEqual(r["solde_final"], 51_000)

    def test_eod_trailing_seuil_mis_a_jour_en_fin_de_journee(self):
        # J1 +2 000 (clôture 52 000 -> seuil 49 500) ; J2 creux à −2 600 -> 49 400 < 49 500 -> échec
        t = trades([(2000, -100, 2500)], [(500, -2600, 600)])
        r = S.simule_chemin(t, regles(drawdown_type="eod_trailing", objectif_eval_usd=10_000))
        self.assertEqual(r["res_eval"], -1)
        self.assertEqual(r["j_eval"], 2)
        # un pic latent de +2 500 sans clôture ne fait PAS monter le seuil EOD
        t2 = trades([(0, -100, 2500)], [(0, -2400, 0)])
        r2 = S.simule_chemin(t2, regles(drawdown_type="eod_trailing", objectif_eval_usd=10_000))
        self.assertEqual(r2["res_eval"], -3)        # toujours en vie (censuré en fin de données)

    def test_static(self):
        t = trades([(2000, 0, 2000)], [(0, -4400, 0)])
        r = S.simule_chemin(t, regles(drawdown_type="static", objectif_eval_usd=10_000))
        self.assertEqual(r["res_eval"], -3)         # 47 600 > 47 500
        t = trades([(2000, 0, 2000)], [(0, -4500, 0)])
        self.assertEqual(S.simule_chemin(t, regles(drawdown_type="static", objectif_eval_usd=10_000))["res_eval"], -1)

    def test_plafond_du_trailing(self):
        # 3 jours à +1 000 -> plus haut 53 000. Sans plafond : seuil 50 500 ; avec plafond 100 : 50 100.
        jours = [[(1000, 0, 1000)]] * 3 + [[(0, -2800, 0)]]       # creux à 50 200
        t = trades(*jours)
        sans = S.simule_chemin(t, regles(objectif_eval_usd=10_000, drawdown_plafond_usd=None))
        avec = S.simule_chemin(t, regles(objectif_eval_usd=10_000, drawdown_plafond_usd=100))
        self.assertEqual(sans["res_eval"], -1)
        self.assertEqual(avec["res_eval"], -3)
        # plafond donné en solde absolu (50 100) : même résultat
        r = S._normalise({"nom": "x", "capital": 50_000, "drawdown_usd": 2500,
                          "drawdown_plafond_usd": 50_100}, "x", "t")
        self.assertAlmostEqual(r.plafond(1), 100)
        self.assertAlmostEqual(r.plafond(0), 100)       # pas de plafond d'éval distinct -> le même
        r2 = S._normalise({"capital": 50_000, "drawdown_usd": 2000, "drawdown_plafond_usd": 50_100,
                           "drawdown_plafond_eval_usd": 0}, "x", "t")
        self.assertEqual(r2.plafond(0), np.inf)          # 0 = le trailing ne s'arrête pas en éval


class TestPerteJournaliere(unittest.TestCase):
    JOURS = ([(-600, -600, 0), (500, -700, 600), (900, 0, 900)],   # latent du jour −1 300 au 2e trade
             [(400, 0, 400)])

    def test_soft_arrete_la_journee(self):
        r = S.simule_chemin(trades(*self.JOURS), regles(perte_journaliere_usd=1000, perte_journaliere_type="soft",
                                                        objectif_eval_usd=10_000))
        self.assertEqual(r["res_eval"], -3)                     # compte vivant
        self.assertAlmostEqual(r["solde_final"], 50_000 - 1000 + 400)   # liquidé à −1 000, 3e trade sauté

    def test_hard_fait_echouer(self):
        r = S.simule_chemin(trades(*self.JOURS), regles(perte_journaliere_usd=1000, perte_journaliere_type="hard",
                                                        objectif_eval_usd=10_000))
        self.assertEqual(r["res_eval"], -1)
        self.assertEqual(r["j_eval"], 1)

    def test_soft_mais_trailing_plus_haut_part_dabord(self):
        # DD 800 < perte journalière 1 000 : c'est le seuil trailing qui est touché d'abord -> échec
        r = S.simule_chemin(trades(*self.JOURS), regles(drawdown_usd=800, perte_journaliere_usd=1000,
                                                        perte_journaliere_type="soft", objectif_eval_usd=10_000))
        self.assertEqual(r["res_eval"], -1)


class TestEvalEtPayout(unittest.TestCase):
    def test_prudent_pic_puis_retour(self):
        # pnl +2 500, MAE 0, MFE +2 500 : en « prudent » 0 -> +2 500 -> 0 -> +2 500 ; le retour à 0
        # est une chute de 2 500 = DD depuis le pic latent -> échec. En heuristique : pas d'échec.
        t = trades([(2500, 0, 2500)])
        self.assertEqual(S.simule_chemin(t, regles(), ordre="prudent")["res_eval"], -1)
        self.assertNotEqual(S.simule_chemin(t, regles(), ordre="heuristique")["res_eval"], -1)

    def test_reussite_simple_et_jours_min(self):
        t = trades(*[[(1000, -100, 1000)]] * 5)
        self.assertEqual(S.simule_chemin(t, regles())["j_eval"], 3)
        self.assertEqual(S.simule_chemin(t, regles(jours_min_eval=5))["j_eval"], 5)

    def test_constance_eval(self):
        # J1 +2 500 puis +500/jour. Objectif 3 000 atteint en J2, mais 2 500 > 50 % de 3 000 :
        # il faut un gain total >= 5 000 -> J6.
        t = trades([(2500, 0, 2500)], *[[(500, 0, 500)]] * 8)
        # ordre heuristique : trade fini à son plus haut -> creux puis pic (en « prudent », le retour
        # de +2 500 à 0 avant la sortie toucherait le seuil : voir test_prudent_pic_puis_retour)
        sans = S.simule_chemin(t, regles(), ordre="heuristique")
        avec = S.simule_chemin(t, regles(consistance_eval_pct=50), ordre="heuristique")
        self.assertEqual(sans["j_eval"], 2)
        self.assertEqual(avec["res_eval"], 1)
        self.assertEqual(avec["j_eval"], 6)

    def test_constance_financee_et_payout(self):
        # Financé direct : coussin 2 600, payout min 500 -> retirable dès solde >= 53 100.
        t = trades([(3100, 0, 3100)], *[[(400, 0, 400)]] * 10)
        sans = S.simule_chemin(t, regles(), demarrer_finance=True, ordre="heuristique")
        self.assertGreaterEqual(sans["n_pay"], 1)      # puis d'autres (1 jour min entre payouts)
        self.assertEqual(sans["j_pay1"], 1)
        # constance 30 % : il faut 3 100 <= 0,3 × gain -> gain >= 10 334 -> pas atteint en 11 jours
        avec = S.simule_chemin(t, regles(consistance_funded_pct=30), demarrer_finance=True, ordre="heuristique")
        self.assertEqual(avec["n_pay"], 0)

    def test_valeur_esperee_frais(self):
        # Trades toujours perdants -> échec ; valeur espérée = −frais d'éval
        t = trades(*[[(-600, -600, 0)]] * 10)
        res = S.monte_carlo(t, regles(), 1, n_sim=50, max_jours_eval=50, max_jours_funded=50)
        self.assertEqual(res["p_reussite"], 0.0)
        self.assertAlmostEqual(res["valeur_esperee_usd"], -100)


class TestDivers(unittest.TestCase):
    def test_journee_de_session_cme(self):
        # 23h30 Paris un mardi (17h30 NY) -> fermeture ; 00h30 mercredi Paris = 18h30 NY mardi -> mercredi
        s = pd.Series(pd.to_datetime(["2026-01-06 15:30", "2026-01-07 00:30"])).dt.tz_localize("Europe/Paris")
        j = S.jour_session(s)
        self.assertEqual(list(j.dt.day), [6, 7])

    def test_taille_et_risque_fixe(self):
        t = trades([(100, -50, 120)])
        t["risque_usd"] = 80.0
        tp = S.prepare_trades(t, risque_usd=250)
        self.assertEqual(int(tp["n"].iloc[0]), 3)
        self.assertAlmostEqual(tp["pnl"].iloc[0], 300)
        res = S.monte_carlo(t, regles(contrats_max_micro=5), 6)
        self.assertFalse(res["taille_autorisee"])

    def test_chargement_regles(self):
        R = S.charge_regles()
        self.assertGreaterEqual(len(R), 3)
        for r in R.values():
            self.assertIn(r.drawdown_type, S.DD_TYPES)
            self.assertGreater(r.capital, 0)

    def test_bootstrap_et_chrono_tournent(self):
        rng = np.random.default_rng(1)
        jours = [[(float(p), float(min(p, 0) - 50), float(max(p, 0) + 50))] for p in rng.normal(60, 300, 120)]
        t = trades(*jours)
        r = regles(drawdown_type="eod_trailing", drawdown_usd=2000)
        a = S.monte_carlo(t, r, 1, n_sim=300)
        b = S.monte_carlo(t, r, 1, methode="chronologique")
        for x in (a, b):
            self.assertAlmostEqual(x["p_reussite"] + x["p_echec"] + x["p_hors_delai"] + x["p_censure"], 1.0)
        self.assertEqual(b["n_parcours"], 120)        # un départ par journée de la grille


class TestReglesDefinitives(unittest.TestCase):
    """Clés ajoutées par regles.toml : paliers, payouts, gel, durée, financement direct."""

    def test_paliers_de_contrats_finance(self):
        # Financé direct, 30 micros demandés, palier [0 profit -> 2 minis = 20 micros] :
        # le trade de +300 $ (30 micros) ne rapporte que 20/30 -> +200 $.
        t = trades([(10, -1, 10)])
        r = regles(contrats_funded_paliers=[[0, 2], [5000, 4]], objectif_eval_usd=0)
        out = S.simule_chemin(t, r, 30, ordre="heuristique")
        self.assertAlmostEqual(out["solde_final"], 50_200)

    def test_payout_pct_profit_et_plafonds_par_rang(self):
        # Sans tampon (solde min 0), 50 % du profit, plafonds [600, 0] ; payout min 250, 1 jour min.
        t = trades([(2000, 0, 2000)], [(2000, 0, 2000)])
        r = regles(objectif_eval_usd=0, coussin_payout_usd=None, payout_solde_min_usd=0,
                   payout_pct_profit_max=50, payout_plafonds_usd=[600, 0], payout_min_usd=250, partage_pct=90)
        out = S.simule_chemin(t, r, ordre="heuristique")
        # J1 : profit 2 000 -> 50 % = 1 000, plafonné à 600 -> solde 51 400
        # J2 : solde 53 400, profit 3 400 -> 50 % = 1 700, sans plafond -> retire 1 700
        self.assertEqual(out["n_pay"], 2)
        self.assertAlmostEqual(out["sum_pay"], 0.9 * (600 + 1700))
        self.assertAlmostEqual(out["solde_final"], 51_700)

    def test_gel_du_plancher_a_la_demande(self):
        # EOD 2 000 sans plafond. J1 +1 500 (plancher 49 500) -> payout de 500 (tampon = capital) ;
        # avec gel, le plancher reste 49 500 ; J2 +3 000 (clôture 54 000) ; J3 creux de −4 000 :
        # 50 000 > 49 500 (gelé) -> vivant ; sans gel le plancher serait 52 000 -> échec.
        t = trades([(1500, 0, 1500)], [(3000, 0, 3000)], [(0, -4000, 0)])
        base = dict(objectif_eval_usd=0, drawdown_usd=2000, drawdown_type="eod_trailing", coussin_payout_usd=None,
                    payout_solde_min_usd=0, payout_plafonds_usd=[500, 1], payout_min_usd=500,
                    jours_min_avant_payout=1)
        gel = S.simule_chemin(t, regles(drawdown_bloque_a_la_demande_payout=True, **base), ordre="heuristique")
        sans = S.simule_chemin(t, regles(drawdown_bloque_a_la_demande_payout=False, **base), ordre="heuristique")
        self.assertNotEqual(gel["res_fin"], -1)
        self.assertEqual(sans["res_fin"], -1)

    def test_duree_max_eval(self):
        # 30 jours calendaires = 21 journées de session ; +100 $/jour n'atteint jamais 3 000 $ à temps
        t = trades(*[[(100, 0, 100)]] * 40)
        out = S.simule_chemin(t, regles(duree_max_eval_jours=30), ordre="heuristique")
        self.assertEqual(out["res_eval"], -2)
        self.assertEqual(out["j_eval"], 21)

    def test_regles_definitives_chargees(self):
        if not S.FICHIER_REGLES.exists():
            self.skipTest("regles.toml absent")
        R = S.charge_regles(S.FICHIER_REGLES)
        a = R["apex_50k_intraday"]
        self.assertEqual(a.propfirm, "apex")
        self.assertEqual(S._params_phase(a, 0)["dll_type"], 0)            # pas de DLL en éval
        self.assertEqual(S._params_phase(a, 1)["dll"], 1000)              # DLL en financé
        self.assertEqual(a.plafond(0), 3000)                              # 53 000 en éval
        self.assertEqual(a.plafond(1), 100)                               # 50 100 en financé
        self.assertAlmostEqual(a.tampon(), 52_100)
        ld = R["lucid_50k_daily_eod_dll"]
        self.assertEqual(S._params_phase(ld, 1)["type"], S.DD_TYPES["intraday_trailing"])
        self.assertTrue(R["lucid_50k_direct"].financement_direct())
        self.assertTrue(R["lucid_50k_flex_sans_dll"].frais_inconnus)
        self.assertAlmostEqual(R["tradeify_50k_select_flex"].tampon(), 50_000)   # pas de tampon
