"""Validation du simulateur sur les trades réels du préréglage A (testeur TradingView, 3 ans, 15m).

    ~/venv-quant/bin/python valide_prereglage_a.py [--registre]
      -> RESULTATS_PREREGLAGE_A.md, balayage_prereglage_a.csv (+ lignes PF-xxx dans le registre
         avec --registre : append uniquement, à ne lancer qu'une fois par jeu de règles)

Source : tools/strategie/testeur_1er_jet/cache_trades.pkl (écrit par etude.py) = préréglage A
NQ1! et ES1! (fichiers 2b13f et 2f924 ; B et C du 1er jet sont faux, non utilisés), P&L CORRIGÉ
de l'effet du bug de la bougie de remplissage (pnl_c, m_mae_c, m_mfe_c, R = 2 ATR estimé).
Conversion micro : NQ -> MNQ et ES -> MES = P&L brut en points × valeur du point micro
(2 $ / 5 $), soit ÷10, puis commission micro aller-retour COMM_MICRO.
"""
import csv
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import simulateur as S  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
CACHE = ICI.parents[1] / "tools/strategie/testeur_1er_jet/cache_trades.pkl"
REGISTRE = ICI.parent / "registre/registre_tests.csv"
SORTIE_MD = ICI / "RESULTATS_PREREGLAGE_A.md"
SORTIE_CSV = ICI / "balayage_prereglage_a.csv"
CACHE_SYNTH = ICI / "__pycache__" / "synth_prereglage_a.pkl"   # pour régénérer md/registre sans recalcul
COMM_MINI = 2.5        # aller-retour utilisé par le testeur
COMM_MICRO = 1.30      # aller-retour micro supposé (frais propfirm + bourse), hypothèse
VP_MINI = {"NQ": 20.0, "ES": 50.0}
VP_MICRO = {"NQ": 2.0, "ES": 5.0}
MICRO = {"NQ": "MNQ", "ES": "MES"}
N_SIM = 2000
KW = dict(max_jours_eval=250, max_jours_funded=250, max_payouts=5, bloc_jours=5)
PRIORITE = ["tradeify_50k_select_flex", "tradeify_50k_growth", "lucid_50k_flex_sans_dll", "lucid_50k_pro_sans_dll"]
TAILLES_TAB = [1, 2, 3, 5, 8, 10, 15, 20, 30, 40]
APEX_COMPARAISON = "apex_50k_eod"


def trades_micro(t: pd.DataFrame, sym: str) -> pd.DataFrame:
    vp, c = VP_MICRO[sym], COMM_MICRO
    pts = (t["pnl_c"] + COMM_MINI) / VP_MINI[sym]          # P&L brut en points (corrigé du bug)
    return pd.DataFrame({
        "entree_t": t["entree_dt"].values, "sortie_t": t["sortie_dt"].values, "sens": "long",
        "pnl_usd": pts.values * vp - c,
        "mae_usd": -(t["m_mae_c"] * t["Rf"]).values * vp - c,
        "mfe_usd": (t["m_mfe_c"] * t["Rf"]).values * vp - c,
        "r": t["r"].values, "risque_usd": t["Rf"].values * vp + c,
    })


def references(tm: pd.DataFrame, t: pd.DataFrame, sym: str) -> dict:
    """Proxys « hasard » faute de trades à entrées aléatoires sur 3 ans : mêmes trades (même
    distribution, mêmes excursions) décalés d'une constante pour que l'espérance par trade soit
      - 'derive' : celle de la dérive du marché sur la même durée de détention (colonne exces
                   d'etude.py : acheter au hasard et garder aussi longtemps), nette de frais ;
      - 'nulle'  : zéro brut (= −commission)."""
    # exces = (pts − dérive_pts) × vp − 2,5  =>  dérive brute en $ mini = pts × vp − 2,5 − exces
    derive_mini = t["pts"] * VP_MINI[sym] - COMM_MINI - t["exces"]
    cible = {"derive": derive_mini.mean() * VP_MICRO[sym] / VP_MINI[sym] - COMM_MICRO, "nulle": -COMM_MICRO}
    out = {}
    for k, c in cible.items():
        dec = tm["pnl_usd"].mean() - c
        out[k] = tm.assign(pnl_usd=tm["pnl_usd"] - dec, mae_usd=tm["mae_usd"] - dec, mfe_usd=tm["mfe_usd"] - dec)
    return out


def ordre_variantes(R):
    autres = [n for n in R if n not in PRIORITE and not n.startswith("apex")]
    apex = [n for n in R if n.startswith("apex")]
    return [n for n in PRIORITE if n in R] + autres + apex


def ve_col(df):
    return "valeur_esperee_usd" if df["valeur_esperee_usd"].notna().any() else "valeur_hors_frais_eval_usd"


def depuis_cache():
    c = pd.read_pickle(CACHE_SYNTH)
    ecrit_md(c["synth"], c["stats"], c["risque_rows"], c["source"])
    if "--registre" in sys.argv:
        ecrit_registre(c["synth"], c["stats"])


def main():
    D = pd.read_pickle(CACHE)
    R = S.charge_regles()
    source = next(iter(R.values())).fichier_regles
    noms = ordre_variantes(R)
    lignes_bal, synth, risque_rows = [], [], []
    stats = {}
    for sym in ("NQ", "ES"):
        t = D[sym]
        tm = trades_micro(t, sym)
        tp0 = S.prepare_trades(tm)
        nuit_tab = {k: {"n": int(len(g)), "total": float(g["pnl"].sum()), "moy": float(g["pnl"].mean()),
                        "gagn": float((g["pnl"] > 0).mean()), "r": float(g["r"].mean())}
                    for k, g in tp0.groupby("traverse_fermeture")}
        stats[sym] = {**S.stats_trades(tm), "debut": str(tm["entree_t"].min().date()),
                      "fin": str(tm["entree_t"].max().date()),
                      "traverse": float(tp0["traverse_fermeture"].mean()), "nuit_tab": nuit_tab}
        refs = references(tm, t, sym)
        for nom in noms:
            r = R[nom]
            tailles = list(range(1, min(r.contrats_max_micro, 40) + 1))
            h, _ = S.optimise_taille(tm, r, tailles, n_sim=N_SIM, ordre="heuristique", **KW)
            col = ve_col(h)
            c_ve = int(h.loc[h[col].idxmax(), "contrats"])
            tp_ = sorted(set([c for c in TAILLES_TAB if c in tailles] + [c_ve]))
            p, _ = S.optimise_taille(tm, r, tp_, n_sim=N_SIM, ordre="prudent", **KW)
            for df, o in ((h, "heuristique"), (p, "prudent")):
                lignes_bal.append(df.assign(marche=MICRO[sym], ordre=o))
            h, p = h.set_index("contrats"), p.set_index("contrats")
            c_pr = int(h["p_reussite"].idxmax())
            mk = lambda **k: S.monte_carlo(tm, r, c_ve, **{**KW, "ordre": "heuristique", **k})
            chrono = mk(methode="chronologique")
            chrono_p = mk(methode="chronologique", ordre="prudent")
            nuit = mk(n_sim=N_SIM, nuit="exclure")
            ref_d = S.analyse_reference(refs["derive"], r, c_ve, n_sim=N_SIM, ordre="heuristique", **KW)
            ref_n = S.analyse_reference(refs["nulle"], r, c_ve, n_sim=N_SIM, ordre="heuristique", **KW)
            if nom in PRIORITE:
                for rq in (100, 200, 300, 400, 600):
                    x = S.monte_carlo(tm, r, risque_usd=rq, n_sim=N_SIM, ordre="heuristique", **KW)
                    risque_rows.append({"marche": MICRO[sym], "variante": nom, "risque": rq,
                                        "p": x["p_reussite"], "pay": x["p_1er_payout"], "ve": x[col]})
            st = S.stats_trades(tm, c_ve)
            synth.append({
                "marche": MICRO[sym], "sym": sym, "variante": nom, "propfirm": r.propfirm,
                "direct": r.financement_direct(), "frais_inconnus": r.frais_inconnus, "col_ve": col,
                "bots": str(r.bots_autorises), "c_ve": c_ve, "c_pr": c_pr,
                "p_ve": h.loc[c_ve, "p_reussite"], "p_ve_prudent": p.loc[c_ve, "p_reussite"],
                "p_max": h.loc[c_pr, "p_reussite"], "ve": h.loc[c_ve, col], "ve_prudent": p.loc[c_ve, col],
                "delai": h.loc[c_ve, "delai_median_jours"], "pay1": h.loc[c_ve, "p_1er_payout"],
                "pay1_si": h.loc[c_ve, "p_1er_payout_si_reussite"], "pay3": h.loc[c_ve, "p_3_payouts"],
                "payouts": h.loc[c_ve, "payouts_moyens_usd"], "frais": h.loc[c_ve, "frais_moyens_usd"],
                "chrono": chrono["p_reussite"], "chrono_pay1": chrono["p_1er_payout"],
                "chrono_prudent": chrono_p["p_reussite"], "chrono_cens": chrono["p_censure"],
                "nuit": nuit["p_reussite"], "ref_derive": ref_d["p_reussite"], "ref_nulle": ref_n["p_reussite"],
                "ref_derive_pay1": ref_d["p_1er_payout"], "ref_derive_ve": ref_d[col],
                "n_tailles": len(tailles), **st,
                "p1": {c: h.loc[c, "p_reussite"] for c in TAILLES_TAB if c in h.index},
                "pp1": {c: p.loc[c, "p_reussite"] for c in TAILLES_TAB if c in p.index},
                "pay1_t": {c: h.loc[c, "p_1er_payout"] for c in TAILLES_TAB if c in h.index},
                "v1": {c: h.loc[c, col] for c in TAILLES_TAB if c in h.index},
                "p_by_size": h["p_reussite"].to_dict(),
            })
            print(f"{MICRO[sym]} {nom:34s} taille={c_ve:2d} P={h.loc[c_ve,'p_reussite']:.3f} "
                  f"pay1={h.loc[c_ve,'p_1er_payout']:.3f} VE={h.loc[c_ve,col]:+.0f} | Pmax={h.loc[c_pr,'p_reussite']:.3f}@{c_pr} "
                  f"| chrono {chrono['p_reussite']:.3f} | réf dérive {ref_d['p_reussite']:.3f}", flush=True)
    pd.concat(lignes_bal, ignore_index=True).to_csv(SORTIE_CSV, index=False)
    pd.to_pickle({"synth": synth, "stats": stats, "risque_rows": risque_rows, "source": source}, CACHE_SYNTH)
    ecrit_md(synth, stats, risque_rows, source)
    if "--registre" in sys.argv:
        ecrit_registre(synth, stats)
    else:
        print("registre non modifié (relancer avec --registre pour ajouter les lignes PF-xxx)")


# ───────────────────────────────────── sorties ─────────────────────────────────────
def pct(x):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.1f} %"


def usd(x):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:+,.0f} $".replace(",", " ")


NUIT = "tout le gain vient des trades portés la nuit (interdits en propfirm)"


def verdict(s):
    return _verdict(s) + " ; ATTENTION : " + NUIT


def _verdict(s):
    v = s["ve"]
    if not v > 0:
        return "non viable : valeur espérée <= 0 à toutes les tailles"
    if s["direct"]:
        if s["pay1"] <= s["ref_derive_pay1"] + 0.05:
            return "financé direct : P(1er payout) non distinguable de la référence dérive"
        return "financé direct : à confirmer"
    if s["p_ve"] <= s["ref_derive"] + 0.05:
        return "non distinguable de la référence dérive (hasard)"
    return "à confirmer (scellé, sortie avant fermeture)"


ENTETE_SYNTH = ("| Marché | Variante | Taille (µ) | P(réussite) | P prudent | Rejeu chrono | Délai méd. (j) | "
                "P(1er payout) | P(1er payout \\| réussite) | P(≥3 payouts) | Valeur espérée / tentative | "
                "VE prudent | Réf. dérive P | Réf. esp. nulle P | Sans trades de nuit P ² |")


def ligne_synth(s):
    ve_note = " ¹" if s["col_ve"] != "valeur_esperee_usd" else ""
    return (f"| {s['marche']} | {s['variante']} | {s['c_ve']} | {pct(s['p_ve'])} | {pct(s['p_ve_prudent'])} | "
            f"{pct(s['chrono'])} | {s['delai']:.0f} | {pct(s['pay1'])} | {pct(s['pay1_si'])} | {pct(s['pay3'])} | "
            f"{usd(s['ve'])}{ve_note} | {usd(s['ve_prudent'])}{ve_note} | {pct(s['ref_derive'])} | "
            f"{pct(s['ref_nulle'])} | {pct(s['nuit'])} |")


def ecrit_md(synth, stats, risque_rows, source):
    L = []
    a = L.append
    a("# Préréglage A au simulateur propfirm — résultats (16/10/2026)")
    a("")
    a(f"Règles : `{source}`" + (" — **PROVISOIRES**." if "provisoire" in source else
                                 " (relevé définitif de l'agent « Règles des propfirms », 17 variantes)."))
    a("Relancer : `~/venv-quant/bin/python Strat-Botting/propfirm/valide_prereglage_a.py` (le registre "
      "n'est modifié qu'avec `--registre`).")
    a("")
    a("**Trades** : préréglage A (climax BUY + TREND 1H, long seul, stop 2 ATR, sortie Heishinator), testeur "
      "TradingView 15m, NQ1! et ES1! (fichiers `2b13f` et `2f924` ; B et C du 1er jet sont faux), P&L "
      "**corrigé** de l'effet du bug de la bougie de remplissage (`cache_trades.pkl`). Converti en micro "
      f"(points × 2 $ / 5 $, soit ÷10) avec {COMM_MICRO:.2f} $ de commission aller-retour par micro (hypothèse).")
    a("")
    a("| Marché | Période | Trades | % gagnants | R moyen | PF (1 µ) | Gain net 1 µ | DD max clôturé 1 µ | Trades traversant la fermeture |")
    a("|---|---|---|---|---|---|---|---|---|")
    for sym, st in stats.items():
        a(f"| {MICRO[sym]} | {st['debut']} → {st['fin']} | {st['n_trades']} | {st['pct_gagnants']:.1f} % | "
          f"{st['r_moyen']:+.3f} | {st['pf']:.2f} | {usd(st['gain_net_usd'])} | {st['dd_max_usd']:,.0f} $ | "
          f"{100*st['traverse']:.0f} % |".replace(",", " "))
    a("")
    a("**Méthode** : Monte-Carlo par blocs de 5 journées de session (2 000 parcours, journées vides "
      "incluses), éval puis financé (250 journées max chacun, 5 payouts max, ou `payouts_max`) ; ordre des "
      "excursions **heuristique** (valeur centrale) et **prudent** (pic latent avant le creux : borne basse) ; "
      "**rejeu chronologique** depuis chaque journée de départ (fenêtres réelles, très corrélées entre "
      "elles). Taille = nombre de micros qui maximise la valeur espérée d'une tentative = payouts nets − "
      "frais d'éval − frais d'activation (prix catalogue, sans code promo). ¹ = prix de l'éval introuvable "
      "(−1) : valeur **hors frais d'éval**. Comptes « financé direct » : P(réussite) = 1 par construction, "
      "lire P(1er payout). ² « Sans trades de nuit » = mêmes calculs sans les trades qui traversent la "
      "fermeture : voir § 7 (biais de survie, ce n'est pas une sortie forcée). En drawdown EOD, l'ordre "
      "MAE/MFE ne change rien (plancher fixe dans la journée) : prudent = heuristique, sauf DLL et intraday.")
    a("")
    groupes = [("1. Variantes prioritaires (bots permis sous conditions)", lambda s: s["variante"] in PRIORITE),
               ("2. Autres variantes Tradeify / Lucid", lambda s: s["variante"] not in PRIORITE and s["propfirm"] != "apex"),
               ("3. Apex — comparaison seulement (automatisation interdite)", lambda s: s["propfirm"] == "apex")]
    for titre, f in groupes:
        a(f"## {titre}")
        a("")
        a(ENTETE_SYNTH)
        a("|" + "---|" * 15)
        for s in synth:
            if f(s):
                a(ligne_synth(s))
        a("")
    a("## 4. P(réussite de l'éval) par taille — heuristique / prudent (%)")
    a("")
    a("| Marché | Variante | " + " | ".join(f"{c} µ" for c in TAILLES_TAB) + " | Max (taille) |")
    a("|---|---|" + "---|" * (len(TAILLES_TAB) + 1))
    for s in synth:
        cel = [f"{100*s['p1'][c]:.0f} / {100*s['pp1'][c]:.0f}" if c in s["p1"] and c in s["pp1"] else "—"
               for c in TAILLES_TAB]
        a(f"| {s['marche']} | {s['variante']} | " + " | ".join(cel) + f" | {pct(s['p_max'])} ({s['c_pr']}) |")
    a("")
    a("## 5. P(1er payout) et valeur espérée par taille (heuristique)")
    a("")
    a("| Marché | Variante | " + " | ".join(f"{c} µ" for c in TAILLES_TAB) + " |")
    a("|---|---|" + "---|" * len(TAILLES_TAB))
    for s in synth:
        cel = [f"{100*s['pay1_t'][c]:.0f} % / {s['v1'][c]:+.0f} $" if c in s["v1"] else "—" for c in TAILLES_TAB]
        a(f"| {s['marche']} | {s['variante']} | " + " | ".join(cel) + " |")
    a("")
    if risque_rows:
        a("## 6. Risque fixe en $ par trade (variantes prioritaires ; contrats = ⌊risque / 1 R⌋, trade sauté si 0)")
        a("")
        rr = pd.DataFrame(risque_rows)
        risques = sorted(rr["risque"].unique())
        a("| Marché | Variante | " + " | ".join(f"{q} $ : P réussite / P payout / VE" for q in risques) + " |")
        a("|---|---|" + "---|" * len(risques))
        for (m, v), g in rr.groupby(["marche", "variante"], sort=False):
            g = g.set_index("risque")
            a(f"| {m} | {v} | " + " | ".join(
                f"{100*g.loc[q,'p']:.0f} % / {100*g.loc[q,'pay']:.0f} % / {g.loc[q,'ve']:+.0f} $" for q in risques) + " |")
        a("")
    a("## 7. Lecture")
    a("")
    a("**Point principal — dépendance au portage de nuit.** À 1 micro, sur 3 ans :")
    a("")
    a("| Marché | Trades | Intrajournée : n / total / moyenne / % gagnants / R moyen | Traversant la fermeture : n / total / moyenne / % gagnants / R moyen |")
    a("|---|---|---|---|")
    for sym, st in stats.items():
        nt = st["nuit_tab"]
        f_ = lambda d: f"{d['n']} / {usd(d['total'])} / {usd(d['moy'])} / {100*d['gagn']:.0f} % / {d['r']:+.2f}"
        a(f"| {MICRO[sym]} | {st['n_trades']} | {f_(nt[False])} | {f_(nt[True])} |")
    a("")
    a("Les trades fermés dans la journée sont presque tous des stops (5-6 % de gagnants) ; les gagnants sont "
      "les trades longs portés au-delà de 17 h New York. C'est en partie un biais de survie (un trade qui "
      "passe la nuit n'a pas été stoppé avant), donc retirer ces trades (P = 0 %) n'est PAS le bon "
      "contrefactuel — mais cela veut dire que **toutes les probabilités ci-dessus supposent un portage de "
      "nuit interdit par les trois propfirms**. Avec une sortie forcée à 15:40 CT, le P&L de ces trades est "
      "inconnu ici : il faut rejouer le préréglage A au testeur avec fermeture forcée avant de conclure.")
    a("")
    prio = [s for s in synth if s["variante"] in PRIORITE]
    best = max(prio, key=lambda s: s["ve"] if s["ve"] == s["ve"] else -1e9)
    a(f"- Meilleure variante prioritaire : **{best['marche']} {best['variante']}, {best['c_ve']} micros** — "
      f"P(réussite) {pct(best['p_ve'])} (prudent {pct(best['p_ve_prudent'])}, rejeu chrono {pct(best['chrono'])}), "
      f"P(1er payout) {pct(best['pay1'])}, valeur espérée {usd(best['ve'])} par tentative ; référence "
      f"« dérive » à la même taille : P(réussite) {pct(best['ref_derive'])}, valeur {usd(best['ref_derive_ve'])}.")
    for m in ("MNQ", "MES"):
        sm = [s for s in synth if s["marche"] == m and s["propfirm"] != "apex"]
        npos = sum(s["ve"] > 0 for s in sm)
        npp = sum(s["ve_prudent"] > 0 for s in sm)
        ec = np.mean([s["p_ve"] - s["ref_derive"] for s in sm if not s["direct"]])
        a(f"- {m} : valeur espérée > 0 pour {npos} variantes Tradeify/Lucid sur {len(sm)} (heuristique), "
          f"{npp} en ordre prudent ; écart moyen P(réussite) stratégie − référence dérive : {100*ec:+.1f} points.")
    a("- La référence garde la même distribution de trades et ne change que l'espérance (ramenée à la dérive "
      "du marché sur la même durée) : un écart faible veut dire que la réussite vient surtout de la variance "
      "(queue de gros gagnants), pas d'un avantage propre de l'entrée.")
    a("- Le rejeu chronologique est nettement plus dur que le bootstrap là où la stratégie saigne longtemps "
      "(oct. 2025 → mars 2026 ; ES quasi toute 2025) : les départs de ces périodes échouent presque tous. "
      "Il n'y a que quelques fenêtres indépendantes en 3 ans : c'est l'estimation la plus réaliste mais la "
      "plus bruitée.")
    a("- Les petites tailles maximisent souvent P(réussite) (la variance d'un trade reste loin du drawdown) "
      "mais l'éval dure alors des mois ; les règles à constance (Select Flex 40 % en éval, Lucid Flex 50 %) "
      "pénalisent une stratégie de queue dont la meilleure journée pèse lourd.")
    a("- Le balayage de taille est une sélection (jusqu'à 40 tailles) : la taille « optimale » est optimiste ; "
      "regarder la zone stable des § 4-5 plutôt que le maximum.")
    a("")
    a("## 8. Limites")
    a("")
    a(f"- **{100*np.mean([st['traverse'] for st in stats.values()]):.0f} % des trades traversent la fermeture** "
      "de 17 h New York (sortie Heishinator). Interdit en propfirm (Tradeify/Lucid ferment d'office à "
      "15:45 CT, Apex échoue le compte). Ils sont rattachés à leur journée d'entrée avec leur P&L final ; la "
      "colonne « sans trades de nuit » les retire (biais dans l'autre sens : beaucoup de gros gagnants sont "
      "des trades longs). **Une version avec sortie forcée à 15:40 CT est nécessaire pour conclure.**")
    a("- Ordre MAE/MFE inconnu dans l'export : borne prudente et valeur heuristique ; un seul creux et un "
      "seul pic par trade.")
    a("- Trades en 1 contrat mini convertis ÷10 : glissement micro réel non modélisé ; R estimé (±25 %) "
      "pour les trades non stoppés ; correctif du bug estimé.")
    a("- Règles non modélisées : DLL financée évolutive (Tradeify Growth 2 000 $ à 53 000 ; LucidScale), "
      "fenêtres de news (LucidDaily), microscalping, inactivité, option constance 50 % payante, "
      "réinitialisations payantes ; `drawdown_bloque_a_la_demande_payout` = plancher figé à son niveau du "
      "moment ; tampon de payout = `drawdown_declencheur_blocage_usd` quand `payout_solde_min_usd` > 0, "
      "aucun sinon ; durée max d'éval convertie en jours de session (30 j calendaires = 21 j).")
    a("- Frais au prix catalogue (les codes promo de 80-90 % changent fortement la valeur espérée, surtout "
      "Apex) ; prix introuvables (−1) traités hors frais d'éval.")
    a("- Référence « hasard » = proxy (mêmes trades, espérance ramenée à la dérive), faute de trades à "
      "entrées aléatoires sur 3 ans ; à remplacer par la vraie référence du moteur commun.")
    a("- 3 ans de données = un régime long haussier ; le bootstrap par blocs ne crée pas de régime absent.")
    a("")
    a("Détail complet (toutes tailles, deux ordres) : `balayage_prereglage_a.csv`.")
    SORTIE_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


def ecrit_registre(synth, stats):
    with open(REGISTRE, newline="", encoding="utf-8") as f:
        lec = list(csv.reader(f))
    entete = lec[0]
    ids = [row[0] for row in lec[1:] if row and row[0].startswith("PF-")]
    n0 = max([int(i.split("-")[1]) for i in ids], default=0)
    apex = {(s["marche"]): s["p_by_size"] for s in synth if s["variante"] == APEX_COMPARAISON}
    rows = []
    for s in [s for s in synth if s["propfirm"] != "apex"]:
        st = stats[s["sym"]]
        n0 += 1
        d = {k: "" for k in entete}
        p_app = s["pay1"] if s["direct"] else s["p_ve"]
        pa = apex.get(s["marche"], {}).get(s["c_ve"])
        d.update({
            "id": f"PF-{n0:03d}", "date": date.today().isoformat(), "agent": "simulateur-propfirm",
            "famille": "propfirm-validation",
            "recette": f"Préréglage A (climax BUY + TREND 1H, stop 2 ATR, sortie Heishinator, long) — "
                       f"{s['variante']}, {s['c_ve']} micros (taille max valeur espérée)",
            "marche": f"{s['marche']} ({s['sym']}1! ÷10)", "ut_signal": "15m", "ut_entree": "15m",
            "periode_debut": st["debut"], "periode_fin": st["fin"], "echantillon": "testeur_3ans",
            "n_variantes_testees": s["n_tailles"], "n_trades": s["n_trades"],
            "pct_gagnants": round(s["pct_gagnants"], 1), "r_moyen": round(st["r_moyen"], 3),
            "pf": round(s["pf"], 2), "gain_net_usd": round(s["gain_net_usd"]), "dd_max_usd": round(s["dd_max_usd"]),
            "p_apex": "" if pa is None else round(pa, 3),
            "p_ref_hasard": round(s["ref_derive_pay1"] if s["direct"] else s["ref_derive"], 3),
            "verdict": (f"{verdict(s)} ; VE {s['ve']:+.0f} $/tentative"
                        + (" (hors frais d'éval, prix introuvable)" if s["col_ve"] != "valeur_esperee_usd" else "")
                        + f" ; P prudent {s['p_ve_prudent']:.3f} ; chrono {s['chrono']:.3f} ; P(1er payout) {s['pay1']:.3f}"
                        + (" ; financé direct : p = P(1er payout)" if s["direct"] else "")
                        + f" ; {100*st['traverse']:.0f} % trades de nuit non conformes ; p_apex = {APEX_COMPARAISON} même taille"),
            "fichier": "Strat-Botting/propfirm/RESULTATS_PREREGLAGE_A.md",
        })
        col = {"tradeify": "p_tradeify", "lucid": "p_lucid"}.get(s["propfirm"])
        if col:
            d[col] = round(p_app, 3)
        rows.append([d[k] for k in entete])
    with open(REGISTRE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"{len(rows)} lignes ajoutées au registre (jusqu'à PF-{n0:03d})")


if __name__ == "__main__":
    depuis_cache() if "--depuis-cache" in sys.argv else main()
