# Préréglage A au simulateur propfirm — résultats (16/10/2026)

Règles : `regles.toml` (relevé définitif de l'agent « Règles des propfirms », 17 variantes).
Relancer : `~/venv-quant/bin/python Strat-Botting/propfirm/valide_prereglage_a.py` (le registre n'est modifié qu'avec `--registre`).

**Trades** : préréglage A (climax BUY + TREND 1H, long seul, stop 2 ATR, sortie Heishinator), testeur TradingView 15m, NQ1! et ES1! (fichiers `2b13f` et `2f924` ; B et C du 1er jet sont faux), P&L **corrigé** de l'effet du bug de la bougie de remplissage (`cache_trades.pkl`). Converti en micro (points × 2 $ / 5 $, soit ÷10) avec 1.30 $ de commission aller-retour par micro (hypothèse).

| Marché | Période | Trades | % gagnants | R moyen | PF (1 µ) | Gain net 1 µ | DD max clôturé 1 µ | Trades traversant la fermeture |
|---|---|---|---|---|---|---|---|---|
| MNQ | 2023-10-24 → 2026-10-05 | 632 | 25.0 % | +0.160 | 1.16 | +7 377 $ | 3 893 $ | 28 % |
| MES | 2023-10-24 → 2026-10-14 | 661 | 25.7 % | +0.062 | 1.03 | +770 $ | 3 125 $ | 28 % |

**Méthode** : Monte-Carlo par blocs de 5 journées de session (2 000 parcours, journées vides incluses), éval puis financé (250 journées max chacun, 5 payouts max, ou `payouts_max`) ; ordre des excursions **heuristique** (valeur centrale) et **prudent** (pic latent avant le creux : borne basse) ; **rejeu chronologique** depuis chaque journée de départ (fenêtres réelles, très corrélées entre elles). Taille = nombre de micros qui maximise la valeur espérée d'une tentative = payouts nets − frais d'éval − frais d'activation (prix catalogue, sans code promo). ¹ = prix de l'éval introuvable (−1) : valeur **hors frais d'éval**. Comptes « financé direct » : P(réussite) = 1 par construction, lire P(1er payout). ² « Sans trades de nuit » = mêmes calculs sans les trades qui traversent la fermeture : voir § 7 (biais de survie, ce n'est pas une sortie forcée). En drawdown EOD, l'ordre MAE/MFE ne change rien (plancher fixe dans la journée) : prudent = heuristique, sauf DLL et intraday.

## 1. Variantes prioritaires (bots permis sous conditions)

| Marché | Variante | Taille (µ) | P(réussite) | P prudent | Rejeu chrono | Délai méd. (j) | P(1er payout) | P(1er payout \| réussite) | P(≥3 payouts) | Valeur espérée / tentative | VE prudent | Réf. dérive P | Réf. esp. nulle P | Sans trades de nuit P ² |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MNQ | tradeify_50k_select_flex | 1 | 27.8 % | 27.8 % | 25.3 % | 96 | 19.1 % | 68.5 % | 8.5 % | +221 $ | +221 $ | 24.9 % | 12.2 % | 0.0 % |
| MNQ | tradeify_50k_growth | 1 | 37.9 % | 37.9 % | 34.2 % | 76 | 9.3 % | 24.7 % | 0.3 % | +13 $ | +13 $ | 35.0 % | 20.9 % | 0.0 % |
| MNQ | lucid_50k_flex_sans_dll | 1 | 36.4 % | 36.4 % | 30.3 % | 90 | 22.1 % | 60.9 % | 8.4 % | +475 $ ¹ | +475 $ ¹ | 33.7 % | 18.1 % | 0.0 % |
| MNQ | lucid_50k_pro_sans_dll | 1 | 39.0 % | 39.0 % | 34.2 % | 79 | 11.8 % | 30.4 % | 0.7 % | +248 $ ¹ | +248 $ ¹ | 36.6 % | 21.9 % | 0.0 % |
| MES | tradeify_50k_select_flex | 2 | 23.8 % | 23.8 % | 1.2 % | 77 | 14.4 % | 60.4 % | 4.7 % | +72 $ | +72 $ | 33.7 % | 18.4 % | 0.0 % |
| MES | tradeify_50k_growth | 2 | 27.3 % | 27.3 % | 2.6 % | 72 | 5.8 % | 21.2 % | 0.1 % | -46 $ | -46 $ | 37.4 % | 22.1 % | 0.0 % |
| MES | lucid_50k_flex_sans_dll | 2 | 28.6 % | 28.6 % | 4.4 % | 73 | 15.7 % | 54.9 % | 4.2 % | +274 $ ¹ | +274 $ ¹ | 39.1 % | 23.2 % | 0.0 % |
| MES | lucid_50k_pro_sans_dll | 2 | 28.6 % | 28.6 % | 4.4 % | 73 | 7.1 % | 25.0 % | 0.3 % | +153 $ ¹ | +153 $ ¹ | 39.1 % | 23.2 % | 0.0 % |

## 2. Autres variantes Tradeify / Lucid

| Marché | Variante | Taille (µ) | P(réussite) | P prudent | Rejeu chrono | Délai méd. (j) | P(1er payout) | P(1er payout \| réussite) | P(≥3 payouts) | Valeur espérée / tentative | VE prudent | Réf. dérive P | Réf. esp. nulle P | Sans trades de nuit P ² |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MNQ | tradeify_50k_select_daily | 1 | 27.8 % | 27.8 % | 25.3 % | 96 | 13.0 % | 46.8 % | 9.5 % | +91 $ | +91 $ | 24.9 % | 12.2 % | 0.0 % |
| MNQ | tradeify_50k_lightning | 1 | 100.0 % | 100.0 % | 100.0 % | 0 | 5.8 % | 5.8 % | 0.0 % | -385 $ | -385 $ | 100.0 % | 100.0 % | 100.0 % |
| MNQ | lucid_50k_flex_dll | 1 | 36.4 % | 36.4 % | 30.3 % | 90 | 22.1 % | 60.9 % | 8.4 % | +329 $ | +329 $ | 33.7 % | 18.1 % | 0.0 % |
| MNQ | lucid_50k_pro_dll | 1 | 39.0 % | 39.0 % | 34.2 % | 79 | 11.8 % | 30.4 % | 0.7 % | +56 $ | +56 $ | 36.6 % | 21.9 % | 0.0 % |
| MNQ | lucid_50k_daily_eod_dll | 1 | 36.4 % | 36.4 % | 30.3 % | 90 | 13.9 % | 38.1 % | 8.8 % | +355 $ ¹ | +283 $ ¹ | 33.7 % | 18.1 % | 0.0 % |
| MNQ | lucid_50k_daily_eod_sans_dll | 1 | 36.4 % | 36.4 % | 30.3 % | 90 | 13.9 % | 38.1 % | 8.8 % | +355 $ ¹ | +283 $ ¹ | 33.7 % | 18.1 % | 0.0 % |
| MNQ | lucid_50k_daily_intraday_dll | 1 | 32.8 % | 27.6 % | 30.3 % | 83 | 12.4 % | 38.0 % | 8.1 % | +167 $ | +59 $ | 29.9 % | 16.7 % | 0.0 % |
| MNQ | lucid_50k_daily_intraday_sans_dll | 1 | 32.8 % | 27.6 % | 30.3 % | 83 | 12.4 % | 38.0 % | 8.1 % | +323 $ ¹ | +215 $ ¹ | 29.9 % | 16.7 % | 0.0 % |
| MNQ | lucid_50k_direct | 1 | 100.0 % | 100.0 % | 100.0 % | 0 | 5.8 % | 5.8 % | 0.0 % | -411 $ | -411 $ | 100.0 % | 100.0 % | 100.0 % |
| MES | tradeify_50k_select_daily | 2 | 23.8 % | 23.8 % | 1.2 % | 77 | 7.8 % | 32.7 % | 5.1 % | -24 $ | -24 $ | 33.7 % | 18.4 % | 0.0 % |
| MES | tradeify_50k_lightning | 1 | 100.0 % | 100.0 % | 100.0 % | 0 | 8.0 % | 8.0 % | 0.0 % | -345 $ | -345 $ | 100.0 % | 100.0 % | 100.0 % |
| MES | lucid_50k_flex_dll | 2 | 28.6 % | 28.6 % | 4.4 % | 73 | 15.7 % | 54.9 % | 4.2 % | +128 $ | +128 $ | 39.1 % | 23.2 % | 0.0 % |
| MES | lucid_50k_pro_dll | 2 | 28.6 % | 28.6 % | 4.4 % | 73 | 7.1 % | 25.0 % | 0.3 % | -39 $ | -39 $ | 39.1 % | 23.2 % | 0.0 % |
| MES | lucid_50k_daily_eod_dll | 3 | 25.2 % | 25.2 % | 11.8 % | 52 | 7.5 % | 30.0 % | 3.1 % | +179 $ ¹ | +88 $ ¹ | 31.9 % | 20.3 % | 0.0 % |
| MES | lucid_50k_daily_eod_sans_dll | 3 | 25.2 % | 25.2 % | 11.8 % | 52 | 7.5 % | 30.0 % | 3.1 % | +179 $ ¹ | +88 $ ¹ | 31.9 % | 20.3 % | 0.0 % |
| MES | lucid_50k_daily_intraday_dll | 3 | 21.6 % | 11.6 % | 9.9 % | 48 | 6.6 % | 30.4 % | 2.6 % | -0 $ | -113 $ | 27.5 % | 17.3 % | 0.0 % |
| MES | lucid_50k_daily_intraday_sans_dll | 3 | 21.6 % | 11.6 % | 9.9 % | 48 | 6.6 % | 30.4 % | 2.6 % | +156 $ ¹ | +43 $ ¹ | 27.5 % | 17.3 % | 0.0 % |
| MES | lucid_50k_direct | 1 | 100.0 % | 100.0 % | 100.0 % | 0 | 8.0 % | 8.0 % | 0.0 % | -371 $ | -371 $ | 100.0 % | 100.0 % | 100.0 % |

## 3. Apex — comparaison seulement (automatisation interdite)

| Marché | Variante | Taille (µ) | P(réussite) | P prudent | Rejeu chrono | Délai méd. (j) | P(1er payout) | P(1er payout \| réussite) | P(≥3 payouts) | Valeur espérée / tentative | VE prudent | Réf. dérive P | Réf. esp. nulle P | Sans trades de nuit P ² |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MNQ | apex_50k_eod | 3 | 21.1 % | 21.1 % | 19.1 % | 9 | 4.8 % | 22.8 % | 0.6 % | -412 $ | -412 $ | 20.3 % | 16.1 % | 0.0 % |
| MNQ | apex_50k_eod_sans_activation | 3 | 21.1 % | 21.1 % | 19.1 % | 9 | 4.8 % | 22.8 % | 0.6 % | -1 083 $ | -1 083 $ | 20.3 % | 16.1 % | 0.0 % |
| MNQ | apex_50k_intraday | 2 | 14.1 % | 1.4 % | 10.3 % | 11 | 3.2 % | 22.8 % | 0.5 % | -164 $ | -246 $ | 13.6 % | 11.8 % | 0.0 % |
| MNQ | apex_50k_intraday_sans_activation | 2 | 14.1 % | 1.4 % | 10.3 % | 11 | 3.2 % | 22.8 % | 0.5 % | +93 $ ¹ | +4 $ ¹ | 13.6 % | 11.8 % | 0.0 % |
| MES | apex_50k_eod | 4 | 12.3 % | 12.3 % | 7.7 % | 11 | 3.3 % | 26.7 % | 0.4 % | -435 $ | -435 $ | 14.0 % | 11.6 % | 0.0 % |
| MES | apex_50k_eod_sans_activation | 6 | 19.1 % | 19.1 % | 14.8 % | 10 | 3.5 % | 18.6 % | 0.4 % | -1 110 $ | -1 110 $ | 21.6 % | 17.2 % | 0.0 % |
| MES | apex_50k_intraday | 5 | 13.9 % | 0.5 % | 11.1 % | 9 | 2.5 % | 18.0 % | 0.4 % | -197 $ | -249 $ | 15.7 % | 12.7 % | 0.0 % |
| MES | apex_50k_intraday_sans_activation | 5 | 13.9 % | 0.5 % | 11.1 % | 9 | 2.5 % | 18.0 % | 0.4 % | +60 $ ¹ | +1 $ ¹ | 15.7 % | 12.7 % | 0.0 % |

## 4. P(réussite de l'éval) par taille — heuristique / prudent (%)

| Marché | Variante | 1 µ | 2 µ | 3 µ | 5 µ | 8 µ | 10 µ | 15 µ | 20 µ | 30 µ | 40 µ | Max (taille) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MNQ | tradeify_50k_select_flex | 28 / 28 | 15 / 15 | 9 / 9 | 4 / 4 | 1 / 1 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 27.8 % (1) |
| MNQ | tradeify_50k_growth | 38 / 38 | 31 / 31 | 28 / 28 | 24 / 24 | 23 / 23 | 23 / 23 | 20 / 20 | 18 / 18 | 15 / 15 | 11 / 11 | 37.9 % (1) |
| MNQ | lucid_50k_flex_sans_dll | 36 / 36 | 26 / 26 | 21 / 21 | 14 / 14 | 10 / 10 | 9 / 9 | 6 / 6 | 5 / 5 | 4 / 4 | 3 / 3 | 36.4 % (1) |
| MNQ | lucid_50k_pro_sans_dll | 39 / 39 | 32 / 32 | 29 / 29 | 26 / 26 | 25 / 25 | 25 / 25 | 21 / 21 | 18 / 18 | 15 / 15 | 12 / 12 | 39.0 % (1) |
| MNQ | tradeify_50k_select_daily | 28 / 28 | 15 / 15 | 9 / 9 | 4 / 4 | 1 / 1 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 27.8 % (1) |
| MNQ | tradeify_50k_lightning | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100.0 % (1) |
| MNQ | lucid_50k_flex_dll | 36 / 36 | 26 / 26 | 21 / 21 | 14 / 14 | 10 / 10 | 8 / 8 | 6 / 6 | 3 / 3 | 3 / 3 | 2 / 2 | 36.4 % (1) |
| MNQ | lucid_50k_pro_dll | 39 / 39 | 32 / 32 | 29 / 29 | 25 / 25 | 26 / 26 | 24 / 24 | 21 / 21 | 17 / 17 | 15 / 15 | 11 / 11 | 39.0 % (1) |
| MNQ | lucid_50k_daily_eod_dll | 36 / 36 | 26 / 26 | 21 / 21 | 14 / 14 | 10 / 10 | 8 / 8 | 6 / 6 | 3 / 3 | 3 / 3 | 2 / 2 | 36.4 % (1) |
| MNQ | lucid_50k_daily_eod_sans_dll | 36 / 36 | 26 / 26 | 21 / 21 | 14 / 14 | 10 / 10 | 9 / 9 | 6 / 6 | 5 / 5 | 4 / 4 | 3 / 3 | 36.4 % (1) |
| MNQ | lucid_50k_daily_intraday_dll | 33 / 28 | 22 / 13 | 16 / 6 | 9 / 0 | 8 / 0 | 6 / 0 | 4 / 0 | 2 / 0 | 2 / 0 | 1 / 0 | 32.8 % (1) |
| MNQ | lucid_50k_daily_intraday_sans_dll | 33 / 28 | 22 / 13 | 16 / 6 | 9 / 0 | 7 / 0 | 6 / 0 | 5 / 0 | 4 / 0 | 4 / 0 | 3 / 0 | 32.8 % (1) |
| MNQ | lucid_50k_direct | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100.0 % (1) |
| MNQ | apex_50k_eod | 2 / 2 | 15 / 15 | 21 / 21 | 24 / 24 | 24 / 24 | 23 / 23 | 22 / 22 | 18 / 18 | 15 / 15 | 10 / 10 | 25.4 % (9) |
| MNQ | apex_50k_eod_sans_activation | 2 / 2 | 15 / 15 | 21 / 21 | 24 / 24 | 24 / 24 | 23 / 23 | 22 / 22 | 18 / 18 | 15 / 15 | 10 / 10 | 25.4 % (9) |
| MNQ | apex_50k_intraday | 2 / 1 | 14 / 1 | 16 / 1 | 14 / 0 | 14 / 0 | 14 / 0 | 15 / 0 | 14 / 0 | 13 / 0 | 11 / 0 | 16.8 % (14) |
| MNQ | apex_50k_intraday_sans_activation | 2 / 1 | 14 / 1 | 16 / 1 | 14 / 0 | 14 / 0 | 14 / 0 | 15 / 0 | 14 / 0 | 13 / 0 | 11 / 0 | 16.8 % (14) |
| MES | tradeify_50k_select_flex | 12 / 12 | 24 / 24 | 17 / 17 | 8 / 8 | 3 / 3 | 2 / 2 | 1 / 1 | 1 / 1 | 0 / 0 | 0 / 0 | 23.8 % (2) |
| MES | tradeify_50k_growth | 12 / 12 | 27 / 27 | 28 / 28 | 26 / 26 | 24 / 24 | 23 / 23 | 20 / 20 | 19 / 19 | 17 / 17 | 16 / 16 | 28.3 % (3) |
| MES | lucid_50k_flex_sans_dll | 12 / 12 | 29 / 29 | 25 / 25 | 19 / 19 | 14 / 14 | 12 / 12 | 9 / 9 | 8 / 8 | 5 / 5 | 4 / 4 | 28.6 % (2) |
| MES | lucid_50k_pro_sans_dll | 12 / 12 | 29 / 29 | 30 / 30 | 28 / 28 | 25 / 25 | 24 / 24 | 22 / 22 | 21 / 21 | 17 / 17 | 16 / 16 | 29.6 % (3) |
| MES | tradeify_50k_select_daily | 12 / 12 | 24 / 24 | 17 / 17 | 8 / 8 | 3 / 3 | 2 / 2 | 1 / 1 | 1 / 1 | 0 / 0 | 0 / 0 | 23.8 % (2) |
| MES | tradeify_50k_lightning | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100.0 % (1) |
| MES | lucid_50k_flex_dll | 12 / 12 | 29 / 29 | 25 / 25 | 19 / 19 | 13 / 13 | 11 / 11 | 7 / 7 | 6 / 6 | 4 / 4 | 2 / 2 | 28.6 % (2) |
| MES | lucid_50k_pro_dll | 12 / 12 | 29 / 29 | 30 / 30 | 28 / 28 | 24 / 24 | 24 / 24 | 21 / 21 | 19 / 19 | 18 / 18 | 16 / 16 | 29.6 % (3) |
| MES | lucid_50k_daily_eod_dll | 12 / 12 | 29 / 29 | 25 / 25 | 19 / 19 | 13 / 13 | 11 / 11 | 7 / 7 | 6 / 6 | 4 / 4 | 2 / 2 | 28.6 % (2) |
| MES | lucid_50k_daily_eod_sans_dll | 12 / 12 | 29 / 29 | 25 / 25 | 19 / 19 | 14 / 14 | 12 / 12 | 9 / 9 | 8 / 8 | 5 / 5 | 4 / 4 | 28.6 % (2) |
| MES | lucid_50k_daily_intraday_dll | 12 / 12 | 26 / 20 | 22 / 12 | 15 / 5 | 9 / 2 | 8 / 1 | 5 / 0 | 4 / 0 | 3 / 0 | 2 / 0 | 25.6 % (2) |
| MES | lucid_50k_daily_intraday_sans_dll | 12 / 12 | 26 / 20 | 22 / 12 | 15 / 5 | 10 / 2 | 8 / 1 | 6 / 0 | 5 / 0 | 4 / 0 | 3 / 0 | 25.6 % (2) |
| MES | lucid_50k_direct | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100.0 % (1) |
| MES | apex_50k_eod | 0 / 0 | 2 / 2 | 7 / 7 | 16 / 16 | 22 / 22 | 23 / 23 | 20 / 20 | 18 / 18 | 16 / 16 | 15 / 15 | 23.2 % (9) |
| MES | apex_50k_eod_sans_activation | 0 / 0 | 2 / 2 | 7 / 7 | 16 / 16 | 22 / 22 | 23 / 23 | 20 / 20 | 18 / 18 | 16 / 16 | 15 / 15 | 23.2 % (9) |
| MES | apex_50k_intraday | 0 / 0 | 2 / 1 | 7 / 0 | 14 / 1 | 13 / 1 | 13 / 0 | 13 / 0 | 13 / 0 | 12 / 0 | 11 / 0 | 13.9 % (5) |
| MES | apex_50k_intraday_sans_activation | 0 / 0 | 2 / 1 | 7 / 0 | 14 / 1 | 13 / 1 | 13 / 0 | 13 / 0 | 13 / 0 | 12 / 0 | 11 / 0 | 13.9 % (5) |

## 5. P(1er payout) et valeur espérée par taille (heuristique)

| Marché | Variante | 1 µ | 2 µ | 3 µ | 5 µ | 8 µ | 10 µ | 15 µ | 20 µ | 30 µ | 40 µ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MNQ | tradeify_50k_select_flex | 19 % / +221 $ | 7 % / +31 $ | 3 % / -60 $ | 1 % / -144 $ | 0 % / -162 $ | 0 % / -165 $ | 0 % / -165 $ | 0 % / -165 $ | 0 % / -165 $ | 0 % / -165 $ |
| MNQ | tradeify_50k_growth | 9 % / +13 $ | 6 % / -29 $ | 5 % / -55 $ | 2 % / -108 $ | 1 % / -128 $ | 1 % / -129 $ | 0 % / -138 $ | 0 % / -143 $ | 0 % / -144 $ | 0 % / -145 $ |
| MNQ | lucid_50k_flex_sans_dll | 22 % / +475 $ | 13 % / +312 $ | 7 % / +202 $ | 2 % / +86 $ | 1 % / +33 $ | 1 % / +29 $ | 0 % / +10 $ | 0 % / +8 $ | 0 % / +4 $ | 0 % / +4 $ |
| MNQ | lucid_50k_pro_sans_dll | 12 % / +248 $ | 8 % / +184 $ | 6 % / +147 $ | 3 % / +72 $ | 2 % / +56 $ | 2 % / +47 $ | 1 % / +15 $ | 1 % / +14 $ | 0 % / +7 $ | 0 % / +4 $ |
| MNQ | tradeify_50k_select_daily | 13 % / +91 $ | 6 % / -24 $ | 3 % / -82 $ | 1 % / -146 $ | 0 % / -161 $ | 0 % / -165 $ | 0 % / -165 $ | 0 % / -165 $ | 0 % / -165 $ | 0 % / -165 $ |
| MNQ | tradeify_50k_lightning | 6 % / -385 $ | 4 % / -422 $ | 3 % / -443 $ | 1 % / -471 $ | 0 % / -483 $ | 1 % / -480 $ | 0 % / -489 $ | 0 % / -492 $ | 0 % / -492 $ | 0 % / -491 $ |
| MNQ | lucid_50k_flex_dll | 22 % / +329 $ | 13 % / +169 $ | 7 % / +62 $ | 3 % / -65 $ | 1 % / -92 $ | 1 % / -114 $ | 1 % / -123 $ | 0 % / -143 $ | 0 % / -146 $ | 0 % / -146 $ |
| MNQ | lucid_50k_pro_dll | 12 % / +56 $ | 8 % / -7 $ | 6 % / -41 $ | 3 % / -129 $ | 2 % / -141 $ | 1 % / -154 $ | 1 % / -178 $ | 0 % / -188 $ | 0 % / -189 $ | 0 % / -192 $ |
| MNQ | lucid_50k_daily_eod_dll | 14 % / +355 $ | 8 % / +243 $ | 5 % / +155 $ | 3 % / +94 $ | 2 % / +76 $ | 1 % / +63 $ | 0 % / +41 $ | 0 % / +5 $ | 0 % / +5 $ | 0 % / +13 $ |
| MNQ | lucid_50k_daily_eod_sans_dll | 14 % / +355 $ | 8 % / +243 $ | 5 % / +159 $ | 2 % / +86 $ | 1 % / +41 $ | 1 % / +54 $ | 1 % / +54 $ | 1 % / +56 $ | 1 % / +57 $ | 0 % / +31 $ |
| MNQ | lucid_50k_daily_intraday_dll | 12 % / +167 $ | 7 % / +40 $ | 4 % / -32 $ | 2 % / -95 $ | 1 % / -110 $ | 0 % / -141 $ | 0 % / -144 $ | 0 % / -156 $ | 0 % / -151 $ | 0 % / -152 $ |
| MNQ | lucid_50k_daily_intraday_sans_dll | 12 % / +323 $ | 7 % / +196 $ | 4 % / +128 $ | 2 % / +56 $ | 1 % / +33 $ | 1 % / +39 $ | 1 % / +42 $ | 1 % / +44 $ | 1 % / +52 $ | 0 % / +31 $ |
| MNQ | lucid_50k_direct | 6 % / -411 $ | 4 % / -446 $ | 3 % / -466 $ | 1 % / -492 $ | 1 % / -500 $ | 1 % / -498 $ | 0 % / -510 $ | 0 % / -515 $ | 0 % / -515 $ | 0 % / -514 $ |
| MNQ | apex_50k_eod | 1 % / -482 $ | 4 % / -421 $ | 5 % / -412 $ | 3 % / -449 $ | 2 % / -467 $ | 2 % / -482 $ | 1 % / -501 $ | 0 % / -512 $ | 0 % / -507 $ | 0 % / -504 $ |
| MNQ | apex_50k_eod_sans_activation | 1 % / -1179 $ | 4 % / -1099 $ | 5 % / -1083 $ | 3 % / -1116 $ | 2 % / -1133 $ | 2 % / -1150 $ | 1 % / -1170 $ | 0 % / -1187 $ | 0 % / -1187 $ | 0 % / -1189 $ |
| MNQ | apex_50k_intraday | 1 % / -241 $ | 3 % / -164 $ | 3 % / -186 $ | 1 % / -217 $ | 1 % / -239 $ | 1 % / -243 $ | 0 % / -249 $ | 0 % / -255 $ | 0 % / -253 $ | 0 % / -255 $ |
| MNQ | apex_50k_intraday_sans_activation | 1 % / +9 $ | 3 % / +93 $ | 3 % / +72 $ | 1 % / +40 $ | 1 % / +18 $ | 1 % / +14 $ | 0 % / +8 $ | 0 % / +2 $ | 0 % / +4 $ | 0 % / +1 $ |
| MES | tradeify_50k_select_flex | 9 % / -72 $ | 14 % / +72 $ | 9 % / -1 $ | 4 % / -52 $ | 1 % / -124 $ | 0 % / -145 $ | 0 % / -152 $ | 0 % / -159 $ | 0 % / -164 $ | 0 % / -164 $ |
| MES | tradeify_50k_growth | 2 % / -126 $ | 6 % / -46 $ | 5 % / -56 $ | 4 % / -74 $ | 2 % / -107 $ | 2 % / -111 $ | 1 % / -133 $ | 0 % / -142 $ | 0 % / -144 $ | 0 % / -144 $ |
| MES | lucid_50k_flex_sans_dll | 7 % / +86 $ | 16 % / +274 $ | 12 % / +254 $ | 7 % / +198 $ | 3 % / +123 $ | 2 % / +100 $ | 1 % / +68 $ | 1 % / +45 $ | 1 % / +30 $ | 0 % / +16 $ |
| MES | lucid_50k_pro_sans_dll | 3 % / +27 $ | 7 % / +153 $ | 6 % / +145 $ | 5 % / +137 $ | 3 % / +71 $ | 2 % / +68 $ | 1 % / +36 $ | 1 % / +25 $ | 0 % / +7 $ | 0 % / +8 $ |
| MES | tradeify_50k_select_daily | 3 % / -135 $ | 8 % / -24 $ | 6 % / -55 $ | 3 % / -96 $ | 1 % / -137 $ | 1 % / -151 $ | 0 % / -156 $ | 0 % / -159 $ | 0 % / -163 $ | 0 % / -162 $ |
| MES | tradeify_50k_lightning | 8 % / -345 $ | 7 % / -362 $ | 6 % / -385 $ | 4 % / -408 $ | 2 % / -459 $ | 1 % / -465 $ | 1 % / -478 $ | 0 % / -486 $ | 0 % / -490 $ | 0 % / -492 $ |
| MES | lucid_50k_flex_dll | 7 % / -60 $ | 16 % / +128 $ | 12 % / +108 $ | 7 % / +48 $ | 3 % / -59 $ | 2 % / -65 $ | 1 % / -95 $ | 1 % / -118 $ | 0 % / -141 $ | 0 % / -143 $ |
| MES | lucid_50k_pro_dll | 3 % / -165 $ | 7 % / -39 $ | 6 % / -47 $ | 5 % / -56 $ | 2 % / -133 $ | 2 % / -127 $ | 1 % / -172 $ | 1 % / -181 $ | 0 % / -187 $ | 0 % / -192 $ |
| MES | lucid_50k_daily_eod_dll | 3 % / +31 $ | 8 % / +174 $ | 8 % / +179 $ | 5 % / +156 $ | 3 % / +104 $ | 2 % / +96 $ | 1 % / +34 $ | 1 % / +30 $ | 0 % / +14 $ | 0 % / +18 $ |
| MES | lucid_50k_daily_eod_sans_dll | 3 % / +31 $ | 8 % / +174 $ | 8 % / +179 $ | 5 % / +154 $ | 3 % / +129 $ | 2 % / +101 $ | 2 % / +82 $ | 1 % / +82 $ | 1 % / +59 $ | 0 % / +43 $ |
| MES | lucid_50k_daily_intraday_dll | 2 % / -125 $ | 7 % / -2 $ | 7 % / -0 $ | 4 % / -16 $ | 2 % / -79 $ | 2 % / -92 $ | 1 % / -142 $ | 1 % / -138 $ | 0 % / -149 $ | 0 % / -147 $ |
| MES | lucid_50k_daily_intraday_sans_dll | 2 % / +31 $ | 7 % / +154 $ | 7 % / +156 $ | 4 % / +138 $ | 2 % / +79 $ | 1 % / +56 $ | 1 % / +38 $ | 1 % / +42 $ | 1 % / +41 $ | 0 % / +36 $ |
| MES | lucid_50k_direct | 8 % / -371 $ | 7 % / -388 $ | 6 % / -412 $ | 4 % / -437 $ | 1 % / -490 $ | 2 % / -487 $ | 1 % / -504 $ | 0 % / -510 $ | 0 % / -514 $ | 0 % / -515 $ |
| MES | apex_50k_eod | 0 % / -490 $ | 0 % / -483 $ | 2 % / -462 $ | 4 % / -439 $ | 3 % / -450 $ | 3 % / -455 $ | 1 % / -496 $ | 1 % / -503 $ | 0 % / -507 $ | 0 % / -509 $ |
| MES | apex_50k_eod_sans_activation | 0 % / -1190 $ | 0 % / -1181 $ | 2 % / -1152 $ | 4 % / -1118 $ | 3 % / -1120 $ | 3 % / -1123 $ | 1 % / -1168 $ | 1 % / -1178 $ | 0 % / -1184 $ | 0 % / -1188 $ |
| MES | apex_50k_intraday | 0 % / -249 $ | 0 % / -238 $ | 1 % / -220 $ | 2 % / -197 $ | 1 % / -212 $ | 1 % / -227 $ | 1 % / -242 $ | 0 % / -247 $ | 0 % / -254 $ | 0 % / -254 $ |
| MES | apex_50k_intraday_sans_activation | 0 % / +0 $ | 0 % / +12 $ | 1 % / +33 $ | 2 % / +60 $ | 1 % / +44 $ | 1 % / +30 $ | 1 % / +15 $ | 0 % / +10 $ | 0 % / +2 $ | 0 % / +2 $ |

## 6. Risque fixe en $ par trade (variantes prioritaires ; contrats = ⌊risque / 1 R⌋, trade sauté si 0)

| Marché | Variante | 100 $ : P réussite / P payout / VE | 200 $ : P réussite / P payout / VE | 300 $ : P réussite / P payout / VE | 400 $ : P réussite / P payout / VE | 600 $ : P réussite / P payout / VE |
|---|---|---|---|---|---|---|
| MNQ | tradeify_50k_select_flex | 35 % / 29 % / +281 $ | 28 % / 17 % / +305 $ | 14 % / 6 % / +36 $ | 7 % / 2 % / -101 $ | 3 % / 0 % / -139 $ |
| MNQ | tradeify_50k_growth | 35 % / 12 % / +28 $ | 40 % / 13 % / +143 $ | 32 % / 8 % / +32 $ | 30 % / 6 % / -30 $ | 27 % / 4 % / -51 $ |
| MNQ | lucid_50k_flex_sans_dll | 35 % / 26 % / +433 $ | 40 % / 23 % / +626 $ | 28 % / 11 % / +350 $ | 22 % / 6 % / +247 $ | 15 % / 3 % / +129 $ |
| MNQ | lucid_50k_pro_sans_dll | 35 % / 14 % / +193 $ | 42 % / 16 % / +470 $ | 34 % / 9 % / +288 $ | 31 % / 6 % / +193 $ | 28 % / 5 % / +156 $ |
| MES | tradeify_50k_select_flex | 20 % / 13 % / +43 $ | 14 % / 7 % / -22 $ | 7 % / 3 % / -94 $ | 4 % / 2 % / -114 $ | 2 % / 0 % / -157 $ |
| MES | tradeify_50k_growth | 27 % / 5 % / -72 $ | 31 % / 5 % / -65 $ | 28 % / 3 % / -88 $ | 26 % / 3 % / -100 $ | 24 % / 2 % / -118 $ |
| MES | lucid_50k_flex_sans_dll | 25 % / 15 % / +278 $ | 26 % / 11 % / +270 $ | 19 % / 6 % / +200 $ | 14 % / 4 % / +158 $ | 11 % / 2 % / +100 $ |
| MES | lucid_50k_pro_sans_dll | 28 % / 7 % / +105 $ | 32 % / 6 % / +137 $ | 29 % / 4 % / +103 $ | 27 % / 3 % / +81 $ | 25 % / 2 % / +54 $ |

## 7. Lecture

**Point principal — dépendance au portage de nuit.** À 1 micro, sur 3 ans :

| Marché | Trades | Intrajournée : n / total / moyenne / % gagnants / R moyen | Traversant la fermeture : n / total / moyenne / % gagnants / R moyen |
|---|---|---|---|
| MNQ | 632 | 457 / -40 594 $ / -89 $ / 5 % / -0.84 | 175 / +47 971 $ / +274 $ / 76 % / +2.78 |
| MES | 661 | 476 / -22 064 $ / -46 $ / 6 % / -0.89 | 185 / +22 834 $ / +123 $ / 76 % / +2.51 |

Les trades fermés dans la journée sont presque tous des stops (5-6 % de gagnants) ; les gagnants sont les trades longs portés au-delà de 17 h New York. C'est en partie un biais de survie (un trade qui passe la nuit n'a pas été stoppé avant), donc retirer ces trades (P = 0 %) n'est PAS le bon contrefactuel — mais cela veut dire que **toutes les probabilités ci-dessus supposent un portage de nuit interdit par les trois propfirms**. Avec une sortie forcée à 15:40 CT, le P&L de ces trades est inconnu ici : il faut rejouer le préréglage A au testeur avec fermeture forcée avant de conclure.

- Meilleure variante prioritaire : **MNQ lucid_50k_flex_sans_dll, 1 micros** — P(réussite) 36.4 % (prudent 36.4 %, rejeu chrono 30.3 %), P(1er payout) 22.1 %, valeur espérée +475 $ par tentative ; référence « dérive » à la même taille : P(réussite) 33.7 %, valeur +410 $.
- MNQ : valeur espérée > 0 pour 11 variantes Tradeify/Lucid sur 13 (heuristique), 11 en ordre prudent ; écart moyen P(réussite) stratégie − référence dérive : +2.7 points.
- MES : valeur espérée > 0 pour 7 variantes Tradeify/Lucid sur 13 (heuristique), 7 en ordre prudent ; écart moyen P(réussite) stratégie − référence dérive : -8.8 points.
- La référence garde la même distribution de trades et ne change que l'espérance (ramenée à la dérive du marché sur la même durée) : un écart faible veut dire que la réussite vient surtout de la variance (queue de gros gagnants), pas d'un avantage propre de l'entrée.
- Le rejeu chronologique est nettement plus dur que le bootstrap là où la stratégie saigne longtemps (oct. 2025 → mars 2026 ; ES quasi toute 2025) : les départs de ces périodes échouent presque tous. Il n'y a que quelques fenêtres indépendantes en 3 ans : c'est l'estimation la plus réaliste mais la plus bruitée.
- Les petites tailles maximisent souvent P(réussite) (la variance d'un trade reste loin du drawdown) mais l'éval dure alors des mois ; les règles à constance (Select Flex 40 % en éval, Lucid Flex 50 %) pénalisent une stratégie de queue dont la meilleure journée pèse lourd.
- Le balayage de taille est une sélection (jusqu'à 40 tailles) : la taille « optimale » est optimiste ; regarder la zone stable des § 4-5 plutôt que le maximum.

## 8. Limites

- **28 % des trades traversent la fermeture** de 17 h New York (sortie Heishinator). Interdit en propfirm (Tradeify/Lucid ferment d'office à 15:45 CT, Apex échoue le compte). Ils sont rattachés à leur journée d'entrée avec leur P&L final ; la colonne « sans trades de nuit » les retire (biais dans l'autre sens : beaucoup de gros gagnants sont des trades longs). **Une version avec sortie forcée à 15:40 CT est nécessaire pour conclure.**
- Ordre MAE/MFE inconnu dans l'export : borne prudente et valeur heuristique ; un seul creux et un seul pic par trade.
- Trades en 1 contrat mini convertis ÷10 : glissement micro réel non modélisé ; R estimé (±25 %) pour les trades non stoppés ; correctif du bug estimé.
- Règles non modélisées : DLL financée évolutive (Tradeify Growth 2 000 $ à 53 000 ; LucidScale), fenêtres de news (LucidDaily), microscalping, inactivité, option constance 50 % payante, réinitialisations payantes ; `drawdown_bloque_a_la_demande_payout` = plancher figé à son niveau du moment ; tampon de payout = `drawdown_declencheur_blocage_usd` quand `payout_solde_min_usd` > 0, aucun sinon ; durée max d'éval convertie en jours de session (30 j calendaires = 21 j).
- Frais au prix catalogue (les codes promo de 80-90 % changent fortement la valeur espérée, surtout Apex) ; prix introuvables (−1) traités hors frais d'éval.
- Référence « hasard » = proxy (mêmes trades, espérance ramenée à la dérive), faute de trades à entrées aléatoires sur 3 ans ; à remplacer par la vraie référence du moteur commun.
- 3 ans de données = un régime long haussier ; le bootstrap par blocs ne crée pas de régime absent.

Détail complet (toutes tailles, deux ordres) : `balayage_prereglage_a.csv`.
