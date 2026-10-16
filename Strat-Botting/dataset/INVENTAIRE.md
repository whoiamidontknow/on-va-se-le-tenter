# Inventaire des confluences — DATASET.pine V1 (16/10/2026)

Source : `STRATEGIE_V1.pine` V6 (modules copiés de `CompletV3.pine`, Climax de `CLIMATOR.pine`).
Toutes les valeurs sont calculées **sur le graphique Heiken Ashi** (comme l'indicateur), sauf les
colonnes « vrais prix » (`RO`…`RATR`, `P*R_*`, `RND_DN`).

**Types** : É = événement ponctuel (vrai sur une bougie) · S = état (vrai sur une durée) ·
N = niveau de prix · V = valeur continue. **Dir.** : L/S = directionnel (long/short), — = non.
**UT** : « graph. » = unité du graphique ; sinon unité demandée par `request.security`.
**Colonne** : en-tête du CSV (`EVT.3` = bit 3 de la colonne `EVT`) → nom décodé par `charger.py`.

## 1. Prix et volatilité

| Confluence | Module | Type | Dir. | UT | Paramètres par défaut | Colonne CSV → charger.py |
|---|---|---|---|---|---|---|
| OHLC Heiken Ashi | graphique | N | — | graph. | — | `open high low close` → `ha_o ha_h ha_l ha_c` |
| OHLC vrais | vrais prix | N | — | graph. | `ticker.new(..., backadjustment.inherit)` | `RO RH RL RC` → `o h l c` |
| Volume réel | vrais prix | V | — | graph. | idem | `RV` → `v` |
| ATR des vrais prix | vrais prix | V | — | graph. | RMA du TR, 14 | `RATR` → `atr` |

## 2. Tendance / momentum

| Confluence | Module | Type | Dir. | UT | Paramètres par défaut | Colonne CSV → charger.py |
|---|---|---|---|---|---|---|
| Couleur Heishinator (bleu) | Heishinator | S | L/S | graph. | EMA(ohlc4,4) > EMA(ohlc4,32) | `ETAT.0` → `hei_bleu` |
| Changement de couleur haussier / baissier | Heishinator | É | L/S | graph. | idem | `EVT.4/5` → `hei_flip_haut/bas` |
| EMA50 / EMA60 | Moyenator | N | — | graph. | close, 50 / 60 | `EMA50 EMA60` → `ema50 ema60` |
| Clôture > EMA50 | Moyenator | S | L/S | graph. | — | `ETAT.13` → `au_dessus_ema50` |
| ADX, DI+, DI− | Signator | V | (DI) | graph. | DMI(14,14) | `ADX DIP DIM` → `adx dip dim` |
| RSI | SuperTrader | V | — | graph. | 14 | `RSI` → `rsi` |
| CCI | SuperTrader | V | — | graph. | 30 | `CCI` → `cci` |
| TREND (×6 unités) | Tableau TIMEFRAME | S | L/S | 3, 5, 15, 60, 240, 1D | dernière bougie CLÔTURÉE : close > EMA50 | `TF_TD.0-5` → `trend_3 … trend_1D` |
| STRENGTH (×6, 0-4) | Tableau TIMEFRAME | V | L | idem | close>open, MACD>signal, close>EMA50, RSI>50 | `TF_STR` (3 bits/unité, 7 = pas de donnée) → `str_3 … str_1D` |
| Dashator (×6) | Dashator | S | L/S | 1, 5, 15, 60, 240, 1D | bougie HA haussière (clôturée si unité > graph.) | `TF_TD.6-11` → `dash_1 … dash_1D` |
| Données multi-UT disponibles | ajout dataset | S | — | toutes | close de l'unité non na | `TF_OK` (17 bits) → `ok_trend_*`, `ok_dash_*`, `ok_pa_1/5/15`, `ok_macd10`, `ok_jour` |

## 3. Signaux d'entrée

| Confluence | Module | Type | Dir. | UT | Paramètres par défaut | Colonne CSV → charger.py |
|---|---|---|---|---|---|---|
| Flèche Long / Short **Fort** | Signator V9 | É | L/S | graph. | ADX ≥ 18, score ≥ 50, 2e bougie de couleur, conviction V9, blackout actif | `EVT.0/1` → `sig_long_fort`, `sig_short_fort` |
| Flèche Long / Short **Moyen** | Signator V9 | É | L/S | graph. | score entre 18 et 50 | `EVT.2/3` → `sig_long_moyen`, `sig_short_moyen` |
| Score Signator (0-100) | Signator | V | — | graph. | 4 termes pondérés | `SCORE` → `score` |
| Conviction / saturation / 2e bougie | Signator | S | — | graph. | bande 0,3 ATR ou volume ≥ SMA20 ; range ≥ 0,5 ATR ou cpos ≥ 0,67 | `ETAT.14/15/17` → `sig_conv`, `sig_satur`, `sig_run2` |
| Climax BUY / SELL | Climator | É | L/S | graph. | BUY : corps ≥ 0,55, vol ≥ 1,5×SMA20 ; SELL : corps ≥ 0,65, vol ≥ 2× | `EVT.6/7` → `clx_buy`, `clx_sell` |
| Divergence RSI haussière / baissière | SuperTrader | É | L/S | graph. | pivots RSI 5/5, écart 5-60 barres (confirmée 5 barres après) | `EVT.18/19` → `div_haus`, `div_bais` |

## 4. Feu de Confluence et colonne SIGNAL (29 voix, vote par le sens)

| Confluence | Module | Type | Dir. | UT | Paramètres par défaut | Colonne CSV → charger.py |
|---|---|---|---|---|---|---|
| Voix long / voix short (sur 29) | Feu | V | L/S | mixte | 6 Dashator + 10 SuperTrader + 7 SIGNAL + 6 TREND | `FEU_L FEU_S` → `feu_l feu_s` |
| Trend VIDYA | SuperTrader | S | L/S | graph. | VIDYA(10, CMO 20, SMA15) ± 2×ATR200 | `V_ST` voix 0 → `v_trend` (−1/0/+1) |
| Cross SMA50/200 journalier | SuperTrader | S | L/S | 1D | remis à « — » chaque semaine | `V_ST` voix 1 → `v_cross` ; `ST_ETAT` → `cross_etat` |
| CCI ≥ 0 | SuperTrader | S | L/S | graph. | 30 | `V_ST` voix 2 → `v_cci` |
| RSI ≥ 50 | SuperTrader | S | L/S | graph. | 14 | `V_ST` voix 3 → `v_rsi` |
| MACD 10 min | SuperTrader | S | L/S | 10 | 20/40/5 | `V_ST` voix 4 → `v_macd` ; `ST_ETAT` → `macd_etat` |
| Gap (Bull % ≥ Bear %) | SuperTrader | S | L/S | graph. + 1D | — | `V_ST` voix 5 → `v_gap` |
| TF1 / TF2 / TF3 PA | SuperTrader | S | L/S | 1, 5, 15 | SMA20 H/L + MACD 20/40/5 | `V_ST` voix 6-8 → `v_pa1/2/3` ; `ST_ETAT` → `pa1/2/3_etat` |
| Divergence affichée (10 barres) | SuperTrader | S | L/S | graph. | — | `V_ST` voix 9 → `v_div` ; `ST_ETAT` → `div_etat` |
| SuperTrend | SIGNAL | S | L/S | graph. | (3, 10) | `V_SIG` voix 0 → `s_supertrend` |
| MA (close > EMA50) | SIGNAL | S | L/S | graph. | 50 | `V_SIG` voix 1 → `s_ma` |
| VWAP | SIGNAL | S | L/S | graph. | hlc3 | `V_SIG` voix 2 → `s_vwap` |
| Lin Regress | SIGNAL | S | L/S | graph. | 100, prix au-dessus | `V_SIG` voix 3 → `s_linreg` |
| CPR (jour précédent) | SIGNAL | S | L/S/neutre | 1D | — | `V_SIG` voix 4 → `s_cpr` |
| ORB | SIGNAL | S | L/S/neutre | graph. | 09:30-09:45 NY, remis à zéro chaque jour | `V_SIG` voix 5 → `s_orb` |
| Jour précédent (PDH/PDL) | SIGNAL | S | L/S/neutre | 1D | — | `V_SIG` voix 6 → `s_pd` |

## 5. Niveaux (stop, objectif, cassures)

| Confluence | Module | Type | Dir. | UT | Paramètres par défaut | Colonne CSV → charger.py |
|---|---|---|---|---|---|---|
| Droite de résistance (prix courant) | Trendlines V2 | N | — | graph. | pivots 10/10, tampon 0,1 %, 3 touches, nouvelle ancre 100 barres | `TL_RES` → `tl_res` |
| Droite de support (prix courant) | Trendlines V2 | N | — | graph. | idem | `TL_SUP` → `tl_sup` |
| Droite active (non cassée) | Trendlines V2 | S | — | graph. | — | `ETAT.2/3` → `tl_res_active`, `tl_sup_active` |
| Nouvelle droite validée | Trendlines V2 | É | — | graph. | — | `EVT.10/11` → `tl_res_nouvelle`, `tl_sup_nouvelle` |
| Cassure haute / basse (Breakator) | Trendlines V2 | É | L/S | graph. | mèche + tampon | `EVT.8/9` → `tl_cassure_haut`, `tl_cassure_bas` |
| Zone haussière la plus proche au-dessus / au-dessous (haut, bas) | Detector | N | — | graph. | pivot volume 5, mitigation mèche, 3 zones / côté | `ZH_SUP_H ZH_SUP_B ZH_INF_H ZH_INF_B` → `zh_sup_h …` |
| Zone baissière la plus proche au-dessus / au-dessous | Detector | N | — | graph. | idem | `ZB_SUP_H ZB_SUP_B ZB_INF_H ZB_INF_B` → `zb_sup_h …` |
| Prix dans une zone haussière / baissière | Detector | S | — | graph. | — | `ETAT.4/5` → `dans_zh`, `dans_zb` |
| Nouvelle zone / zone mitigée | Detector | É | — | graph. | — | `EVT.12-15` → `zh_nouvelle`, `zb_nouvelle`, `zh_mitigee`, `zb_mitigee` |
| ORB haut / bas | ORB | N | — | graph. | 09:30 NY, 15 min | `ORB_H ORB_L` → `orb_h orb_l` (+ `orb_h_vrai orb_l_vrai`) |
| ORB en formation / formé | ORB | S | — | graph. | — | `ETAT.7/6` → `orb_en_cours`, `orb_forme` |
| Haut / bas session Asie, Londres, US | Sessions | N | — | graph. | Tokyo 09:00-15:30, Londres 08:00-16:30, NY 09:30-16:00 | `AS_H AS_L LD_H LD_L US_H US_L` (+ versions `_vrai`) |
| Session en cours | Sessions | S | — | graph. | idem | `ETAT.8/9/10` → `en_asie`, `en_londres`, `en_us` |
| Monday High / Low | Monday | N | — | graph. | lundi 00:00 → mardi 07:30 Paris | `MON_H MON_L` (+ `mon_h_vrai mon_l_vrai`) |
| Lundi en cours / niveaux prêts | Monday | S | — | graph. | — | `ETAT.11/12` → `lundi_en_cours`, `monday_pret` |
| Cassure Monday haute / basse (clôture) | Monday | É | L/S | graph. | 1 fois par côté et par semaine | `EVT.16/17` → `mon_cassure_haut`, `mon_cassure_bas` |
| Pivots weekly / mensuel / annuel (HA, comme l'indicateur) | Pivator | N | — | W, M, 12M | Traditionnel, période précédente | `PW_* PM_* PY_*` (H, L, C) → `pw_p, pw_r1…r5, pw_s1…s5`, idem `pm_`, `py_` |
| Pivots weekly / mensuel / annuel (vrais prix) | Pivator | N | — | W, M, 12M | idem | `PWR_* PMR_* PYR_*` → `pwr_p … pyr_s5` |
| Pivot le plus proche au-dessus / au-dessous du vrai close, par famille | dérivé | N | — | — | parmi P, R1-R5, S1-S5 | → `pw_dessus pw_dessous …`, `pwr_dessus …` |
| Niveaux ronds au-dessous / au-dessus | Rondator | N | — | graph. | intervalle 100, arrondi inférieur du vrai close | `RND_DN` → `rond_dessous`, `rond_dessus` |

## 6. Filtres de contexte

| Confluence | Module | Type | Dir. | UT | Paramètres par défaut | Colonne CSV → charger.py |
|---|---|---|---|---|---|---|
| Blackout d'annonces | Blackout | S | — | graph. | bougie qui OUVRE à 08:30 ou 10:00 NY ±3 min | `ETAT.1` → `blackout` |
| Graphique en Heiken Ashi | garde-fou | S | — | — | — | `ETAT.16` → `graphique_ha` (doit valoir 1 partout) |
| Heure de session | dérivé | V | — | — | — | colonne `time` → `heure_paris`, `heure_ny`, `minute_ny` (HHMM, fuseau NY) |

## Détail des colonnes empaquetées

Bit `k` vaut `2^k`. Voix sur 2 bits : 0 = neutre, 1 = long, 2 = short (décodées en −1/0/+1).

- **EVT** : 0 sig_long_fort · 1 sig_short_fort · 2 sig_long_moyen · 3 sig_short_moyen · 4 hei_flip_haut ·
  5 hei_flip_bas · 6 clx_buy · 7 clx_sell · 8 tl_cassure_haut · 9 tl_cassure_bas · 10 tl_res_nouvelle ·
  11 tl_sup_nouvelle · 12 zh_nouvelle · 13 zb_nouvelle · 14 zh_mitigee · 15 zb_mitigee ·
  16 mon_cassure_haut · 17 mon_cassure_bas · 18 div_haus · 19 div_bais
- **ETAT** : 0 hei_bleu · 1 blackout · 2 tl_res_active · 3 tl_sup_active · 4 dans_zh · 5 dans_zb ·
  6 orb_forme · 7 orb_en_cours · 8 en_asie · 9 en_londres · 10 en_us · 11 lundi_en_cours ·
  12 monday_pret · 13 au_dessus_ema50 · 14 sig_conv · 15 sig_satur · 16 graphique_ha · 17 sig_run2
- **TF_TD** : 0-5 TREND 3/5/15/60/240/1D · 6-11 Dashator 1/5/15/60/240/1D
- **TF_OK** : 0-5 TREND · 6-11 Dashator · 12-14 PA 1/5/15 min · 15 MACD 10 min · 16 journalier
- **TF_STR** : 6 × 3 bits (unité 1 = bits 0-2 … unité 6 = bits 15-17), valeur 0-4, 7 = pas de donnée
- **V_ST** : 10 voix × 2 bits : trend, cross, cci, rsi, macd, gap, pa1, pa2, pa3, div
- **V_SIG** : 7 voix × 2 bits : supertrend, ma, vwap, linreg, cpr, orb, pd
- **ST_ETAT** : bits 0-1 MACD (0 Bearish, 1 Bullish, 2 SUPERBULL, 3 Basing) · 2-4 / 5-7 / 8-10 PA1/2/3
  (0 neut, 1 super, 2 warn, 3 bull, 4 bear) · 11-12 divergence (0 neut, 1 bull, 2 bear) ·
  13-14 cross (0 aucun, 1 Golden, 2 Death)

## Ce qui N'EST PAS dans le dataset, et pourquoi

| Absent | Raison |
|---|---|
| VIX, volumes des tickers (bloc SuperTrader) | non demandés dans STRATEGIE_V1, ne votent pas au Feu |
| Rangeator | non répliqué (dernier chantier, cf. MEMOIRE §15) |
| Fibonator | module séparé (`FIBONACCI_AUTO.pine`), hors STRATEGIE_V1 |
| TBT, ALLUMAGE / CONTINUATION | non calables (MEMOIRE §15) |
| Flèches de l'original | indicateur fermé : uniquement dans les anciens exports (Jeu 15:10…) |
| Sessions / Monday / ORB sur vrais prix | recalculés par `charger.py` à partir de `RH`/`RL` et des drapeaux de session (exact, données intraday complètes) |
| Niveaux de session intacts des jours précédents | reconstructibles en Python à partir des colonnes `AS_H…` bougie par bougie |

## Budget Pine

63 plots sur 64 (1 libre) · 32 `request.security` sur 40 (vrais prix 1, pivots 6, journalier 3, MACD 10 min 1,
PA 9, TREND 6, Dashator 6).
