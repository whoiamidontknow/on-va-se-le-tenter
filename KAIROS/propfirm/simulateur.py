"""Simulateur propfirm (éval 50k + phase financée jusqu'aux payouts) — KAIROS.

Entrée : une liste de trades (DataFrame) avec au minimum
    entree_t, sortie_t   horodatages (tz Europe/Paris ; naïfs = lus comme Paris)
    sens                 "long"/"short" (informatif)
    pnl_usd              P&L NET (frais compris) pour 1 contrat
    mae_usd              pire P&L latent du trade (<= 0) pour 1 contrat
    mfe_usd              meilleur P&L latent du trade pour 1 contrat
    r, risque_usd        facultatifs (risque_usd = 1 R en $ pour 1 contrat, sert au risque fixe)
+ une variante de règles (regles.toml, à défaut regles_provisoires.toml) + une taille.

Modèle (voir RESULTATS_PREREGLAGE_A.md, § Limites) :
  - Chaque trade = un chemin latent 0 -> x1 -> x2 -> pnl, où (x1, x2) = (MFE, MAE) ou (MAE, MFE).
    ordre="prudent"     : MFE puis MAE (le pic fait monter le seuil trailing AVANT le creux) ;
    ordre="optimiste"   : MAE puis MFE ;
    ordre="heuristique" : trade fini au plus bas -> MFE puis MAE ; fini au plus haut -> MAE puis MFE ;
                          sinon gagnant -> MAE puis MFE, perdant -> MFE puis MAE.
  - Seuil de liquidation : intraday trailing = plus haut solde LATENT − DD ; EOD trailing = plus haut
    solde de clôture − DD (fixe dans la journée, franchissement testé sur le latent) ; static = capital − DD.
    Le trailing cesse de monter à capital + drawdown_plafond_usd.
  - Perte journalière testée sur le latent : soft = liquidation au niveau limite + arrêt du jour,
    hard = échec. Si le seuil trailing est plus haut que la limite du jour, c'est lui qui part d'abord.
  - Journée de trading = session CME (18:00 -> 17:00 heure de New York). Un trade est rattaché à
    sa journée d'ENTRÉE (P&L, MAE, MFE) ; les trades qui traversent la fermeture sont comptés
    (non conformes propfirm) et peuvent être exclus (nuit="exclure").
  - Éval réussie en fin de journée si solde >= capital + objectif, jours actifs >= minimum, et
    meilleure journée <= consistance % du gain total. Sinon on continue.
  - Financé : nouveau compte, mêmes règles (surcharges possibles via une sous-table `funded`).
    Payout en fin de journée si jours actifs / jours gagnants (>= gain_min_jour) depuis le dernier
    payout suffisent, constance financée respectée et solde − (capital + coussin) >= payout_min ;
    montant = min(retirable, payout_max) × partage.
  - Clés de regles.toml prises en compte : plancher d'éval distinct (drawdown_plafond_eval_usd),
    type de drawdown et perte journalière du financé (*_funded), paliers de contrats financés
    (contrats_funded_paliers, appliqués au profit de clôture de la veille), plafonds de payout par
    rang, part max du profit, solde minimal + tampon (= drawdown_declencheur_blocage_usd), objectifs
    de profit par cycle, constance financée progressive, gel du plancher à la demande de payout,
    durée max d'éval (jours calendaires -> ×5/7 en jours de session), payouts_max, financement
    direct (type_compte), frais −1 = introuvables (valeur espérée NaN, voir valeur_hors_frais_eval_usd).
  - Valeur espérée d'une tentative = E[payouts nets] − E[frais d'éval (mensuels si indiqué)]
    − P(réussite) × frais d'activation, sur l'horizon financé simulé.

API principale :
    charge_regles(chemin=None) -> dict[str, Regles]
    prepare_trades(trades, contrats=1, *, risque_usd=None, contrats_max=None, ordre="prudent", nuit="garder")
    grille_jours(tp, debut=None, fin=None) -> Jours
    monte_carlo(trades, regles, contrats=1, *, methode="bootstrap"|"chronologique", ...) -> dict
    simule_chemin(trades, regles, contrats=1, ...) -> dict   (rejeu unique depuis le 1er jour)
    optimise_taille(trades, regles, tailles=None, critere="valeur_esperee", ...) -> (DataFrame, dict)
    analyse_reference(trades_hasard, regles, contrats=1, ...) -> dict
    stats_trades(trades, contrats=1) -> dict
    rapport(resultats, chemin_md=None, titre="") -> dict
"""
from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

import numpy as np
import pandas as pd

ICI = Path(__file__).resolve().parent
FICHIER_REGLES = ICI / "regles.toml"
FICHIER_PROVISOIRE = ICI / "regles_provisoires.toml"

DD_TYPES = {"intraday_trailing": 0, "eod_trailing": 1, "static": 2}
DLL_TYPES = {"none": 0, "soft": 1, "hard": 2}
_SYN_DD = {"intraday": "intraday_trailing", "trailing": "intraday_trailing", "eod": "eod_trailing",
           "end_of_day": "eod_trailing", "statique": "static", "fixe": "static", "static": "static"}
_SYN_DLL = {"": "none", "aucune": "none", "aucun": "none", "non": "none", "false": "none",
            "souple": "soft", "dure": "hard"}
JOURS_PAR_MOIS = 21          # jours de session pour une facturation mensuelle
TZ_PARIS = "Europe/Paris"
TZ_NY = "America/New_York"


# ═════════════════════════════════════ règles ═════════════════════════════════════
@dataclass
class Regles:
    nom: str                                     # identifiant (clé de table du TOML)
    capital: float = 50_000.0
    objectif_eval_usd: float = 3_000.0
    drawdown_usd: float = 2_500.0
    drawdown_type: str = "intraday_trailing"
    drawdown_plafond_usd: float | None = 100.0   # plancher max (FINANCÉ), au-dessus du capital ; None = aucun
    perte_journaliere_usd: float = 0.0
    perte_journaliere_type: str = "none"
    contrats_max_mini: int = 10
    contrats_max_micro: int = 100
    jours_min_eval: int = 1
    consistance_eval_pct: float = 0.0
    consistance_funded_pct: float = 0.0
    jours_min_avant_payout: int = 5
    payout_min_usd: float = 500.0
    gain_min_jour_payout_usd: float = 0.0
    fermeture_obligatoire_ct: object = None
    news_interdites: object = None
    bots_autorises: object = None
    frais_eval_usd: float = 0.0
    frais_activation_usd: float = 0.0
    # ── clés ajoutées par regles.toml (agent « Règles des propfirms ») ──
    libelle: str = ""
    drawdown_plafond_eval_usd: float | None = None   # plancher max en ÉVAL (offset) ; voir plafond_eval_defini
    plafond_eval_defini: bool = False
    drawdown_declencheur_blocage_usd: float | None = None
    drawdown_bloque_a_la_demande_payout: bool = False
    duree_max_eval_jours: int = 0                    # jours CALENDAIRES, 0 = illimité
    contrats_funded_paliers: list = field(default_factory=list)   # [[profit_min_usd, minis], ...]
    payout_solde_min_usd: float | None = None
    payout_profit_cycle_min_usd: float = 0.0
    payout_objectifs_profit_cycle_usd: list = field(default_factory=list)
    payout_plafonds_usd: list = field(default_factory=list)       # par payout n°1, 2, ... ; 0 = sans plafond
    payout_pct_profit_max: float = 0.0
    payouts_max: int = 0                                          # 0 = illimité
    consistance_funded_progression_pct: list = field(default_factory=list)
    type_compte: str = ""
    frais_inconnus: bool = False
    # ── facultatifs du fichier provisoire ──
    propfirm: str = ""
    jours_gagnants_min_payout: int | None = None   # défaut : jours_min_avant_payout si gain_min > 0
    coussin_payout_usd: float | None = None
    payout_max_usd: float | None = None
    partage_pct: float = 90.0
    frais_eval_mensuels: bool = False
    frais_activation_mensuels: bool = False
    funded: dict = field(default_factory=dict)     # surcharges de la phase financée
    fichier_regles: str = ""

    def financement_direct(self) -> bool:
        return self.type_compte == "financement_direct" or self.objectif_eval_usd <= 0

    def plafond(self, phase: int) -> float:
        """Plancher maximal du seuil, en $ au-dessus du capital (inf = le trailing ne s'arrête pas)."""
        if phase == 0 and self.plafond_eval_defini:
            return _plancher(self.drawdown_plafond_eval_usd, self.capital)
        if phase == 1 and "drawdown_plafond_usd" in self.funded:
            return _plancher(self.funded["drawdown_plafond_usd"], self.capital)
        return _plancher(self.drawdown_plafond_usd, self.capital)

    def tampon(self) -> float:
        """Solde sous lequel rien n'est retirable."""
        pl = self.plafond(1)
        pl = pl if np.isfinite(pl) else 0.0
        if self.coussin_payout_usd is not None:
            return self.capital + float(self.coussin_payout_usd)
        if self.payout_solde_min_usd is None:
            return self.capital + float(self.drawdown_usd) + pl
        if self.payout_solde_min_usd > 0:
            if self.drawdown_declencheur_blocage_usd:
                return float(self.drawdown_declencheur_blocage_usd)
            return self.capital + float(self.drawdown_usd) + pl
        return self.capital

    def solde_min_payout(self) -> float:
        return float(self.payout_solde_min_usd or 0.0)

    def plafonds_payout(self) -> list:
        if self.payout_plafonds_usd:
            return [float(x) for x in self.payout_plafonds_usd]
        return [float(self.payout_max_usd)] if self.payout_max_usd else [0.0]

    def objectifs_cycle(self) -> list:
        if self.payout_objectifs_profit_cycle_usd:
            return [float(x) for x in self.payout_objectifs_profit_cycle_usd]
        return [float(self.payout_profit_cycle_min_usd)]

    def constances_funded(self) -> list:
        if self.consistance_funded_progression_pct:
            return [_pct(x) for x in self.consistance_funded_progression_pct]
        return [float(self.consistance_funded_pct)]

    def contrats_max(self, instrument: str = "micro") -> int:
        return int(self.contrats_max_micro if instrument == "micro" else self.contrats_max_mini)


def _num(v, defaut=0.0):
    if v is None or (isinstance(v, str) and v.strip().lower() in ("", "none", "aucun", "aucune", "nan")):
        return defaut
    if isinstance(v, bool):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return defaut


def _pct(v):
    x = _num(v, 0.0)
    return x * 100 if 0 < x <= 1 else x


def _plancher(x, cap) -> float:
    """None / 0 / NaN -> pas de plafond (inf) ; > capital/2 -> solde absolu converti en écart."""
    x = _num(x, np.nan)
    if np.isnan(x) or x == 0:
        return np.inf
    return x - cap if x > cap / 2 else x


def _normalise(d: dict, nom_defaut: str, fichier: str) -> Regles:
    noms = {f.name for f in fields(Regles)} - {"nom", "libelle", "fichier_regles", "funded"}
    kw = {k: v for k, v in d.items() if k in noms}
    kw["nom"] = nom_defaut
    kw["libelle"] = str(d.get("nom") or nom_defaut)
    kw["fichier_regles"] = fichier
    cap = _num(kw.get("capital"), 50_000.0)
    kw["capital"] = cap
    for k in ("frais_eval_usd", "frais_activation_usd"):
        if k in kw and _num(kw[k]) < 0:           # -1 = introuvable
            kw[k] = float("nan")
            kw["frais_inconnus"] = True
    for k in ("objectif_eval_usd", "drawdown_usd", "perte_journaliere_usd", "payout_min_usd",
              "gain_min_jour_payout_usd", "payout_profit_cycle_min_usd"):
        if k in kw:
            kw[k] = _num(kw[k])
    for k in ("frais_eval_usd", "frais_activation_usd"):
        if k in kw and not kw.get("frais_inconnus"):
            kw[k] = _num(kw[k])
    for k in ("consistance_eval_pct", "consistance_funded_pct", "partage_pct", "payout_pct_profit_max"):
        if k in kw:
            kw[k] = _pct(kw[k])
    if "partage_trader_pct" in d:
        kw["partage_pct"] = _pct(d["partage_trader_pct"])
    for k in ("contrats_max_mini", "contrats_max_micro", "jours_min_eval", "jours_min_avant_payout",
              "duree_max_eval_jours", "payouts_max"):
        if k in kw:
            kw[k] = int(_num(kw[k]))
    if kw.get("jours_gagnants_min_payout") is not None:
        kw["jours_gagnants_min_payout"] = int(_num(kw["jours_gagnants_min_payout"]))
    for k in ("coussin_payout_usd", "payout_max_usd", "drawdown_declencheur_blocage_usd"):
        if kw.get(k) is not None:
            x = _num(kw[k], np.nan)
            kw[k] = None if (np.isnan(x) or x <= 0) else x
    if "payout_solde_min_usd" in kw:
        kw["payout_solde_min_usd"] = _num(kw["payout_solde_min_usd"])
    kw["drawdown_plafond_usd"] = d.get("drawdown_plafond_usd", 100.0)
    if "drawdown_plafond_eval_usd" in d:
        kw["plafond_eval_defini"] = True
    t = str(kw.get("drawdown_type", "intraday_trailing")).strip().lower()
    kw["drawdown_type"] = t if t in DD_TYPES else _SYN_DD.get(t, "intraday_trailing")
    t = str(kw.get("perte_journaliere_type", "none")).strip().lower()
    t = t if t in DLL_TYPES else _SYN_DLL.get(t, "none")
    if kw.get("perte_journaliere_usd", 0) <= 0:
        t = "none"
    kw["perte_journaliere_type"] = t
    for k in ("frais_eval_mensuels", "frais_activation_mensuels", "drawdown_bloque_a_la_demande_payout"):
        if k in kw:
            kw[k] = bool(kw[k])
    if not kw.get("propfirm"):
        n = (nom_defaut + " " + kw["libelle"]).lower()
        kw["propfirm"] = next((p for p in ("apex", "tradeify", "lucid", "topstep", "mff") if p in n), "")
    # surcharges de la phase financée : sous-table funded/finance, clés *_funded, perte_journaliere_funded_*
    surch = dict(d.get("funded") or d.get("finance") or {})
    if "drawdown_type_funded" in d:
        surch["drawdown_type"] = d["drawdown_type_funded"]
    if "perte_journaliere_funded_usd" in d:
        dll_f = _num(d["perte_journaliere_funded_usd"])
        surch["perte_journaliere_usd"] = dll_f
        typ_f = d.get("perte_journaliere_funded_type")
        if typ_f is None:
            typ_f = kw["perte_journaliere_type"] if kw["perte_journaliere_type"] != "none" else "soft"
        surch["perte_journaliere_type"] = typ_f if dll_f > 0 else "none"
    for k, v in d.items():
        if k.endswith("_funded") and k not in ("consistance_funded_pct", "drawdown_type_funded"):
            surch[k[: -len("_funded")]] = v
    kw["funded"] = surch
    return Regles(**kw)


def _cherche_variantes(obj, chemin=()):
    if isinstance(obj, dict):
        if "drawdown_usd" in obj:
            depuis_liste = bool(chemin) and chemin[-1].isdigit()
            ident = (obj.get("nom") if depuis_liste else None) or "_".join(chemin) or "variante"
            yield str(ident), obj
            return
        for k, v in obj.items():
            yield from _cherche_variantes(v, chemin + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _cherche_variantes(v, chemin + (str(i),))


def charge_regles(chemin: str | Path | None = None) -> dict[str, Regles]:
    """Lit regles.toml (prioritaire) ou regles_provisoires.toml. Renvoie {identifiant: Regles}."""
    if chemin is None:
        chemin = FICHIER_REGLES if FICHIER_REGLES.exists() else FICHIER_PROVISOIRE
    chemin = Path(chemin)
    with open(chemin, "rb") as f:
        data = tomllib.load(f)
    out = {}
    for ident, d in _cherche_variantes(data):
        r = _normalise(d, ident, chemin.name)
        out[r.nom] = r
    if not out:
        raise ValueError(f"aucune variante trouvée dans {chemin}")
    return out


def _params_phase(r: Regles, phase: int) -> dict:
    s = r.funded if phase == 1 else {}
    g = lambda k, dft: s.get(k, dft)
    typ = str(g("drawdown_type", r.drawdown_type)).lower()
    typ = typ if typ in DD_TYPES else _SYN_DD.get(typ, r.drawdown_type)
    dll = _num(g("perte_journaliere_usd", r.perte_journaliere_usd))
    dlt = str(g("perte_journaliere_type", r.perte_journaliere_type)).lower()
    dlt = dlt if dlt in DLL_TYPES else _SYN_DLL.get(dlt, "none")
    if dll <= 0:
        dlt = "none"
    return {"dd": _num(g("drawdown_usd", r.drawdown_usd)), "type": DD_TYPES[typ], "plafond": r.plafond(phase),
            "dll": dll, "dll_type": DLL_TYPES[dlt]}


# ═════════════════════════════════════ trades ═════════════════════════════════════
def _paris(s: pd.Series) -> pd.Series:
    s = pd.to_datetime(s)
    if s.dt.tz is None:
        s = s.dt.tz_localize(TZ_PARIS, ambiguous=np.zeros(len(s), dtype=bool), nonexistent="shift_forward")
    return s.dt.tz_convert(TZ_PARIS)


def jour_session(t: pd.Series) -> pd.Series:
    """Journée de trading CME (18:00 -> 17:00 New York) d'un horodatage tz-aware."""
    ny = t.dt.tz_convert(TZ_NY)
    return (ny + pd.Timedelta(hours=6)).dt.tz_localize(None).dt.normalize()


def prepare_trades(trades: pd.DataFrame, contrats: int = 1, *, risque_usd: float | None = None,
                   contrats_max: int | None = None, ordre: str = "prudent",
                   nuit: str = "garder") -> pd.DataFrame:
    """Met les trades à l'échelle (contrats ou risque fixe), rattache chaque trade à sa journée
    de session et fixe l'ordre des excursions. Colonnes ajoutées : jour, n, pnl, mae, mfe, x1, x2,
    traverse_fermeture."""
    t = trades.copy().reset_index(drop=True)
    t["entree_t"] = _paris(t["entree_t"])
    t["sortie_t"] = _paris(t["sortie_t"]) if "sortie_t" in t else t["entree_t"]
    t = t.sort_values("entree_t").reset_index(drop=True)
    t["jour"] = jour_session(t["entree_t"])
    t["traverse_fermeture"] = jour_session(t["sortie_t"]) != t["jour"]
    if nuit == "exclure":
        t = t[~t["traverse_fermeture"]].reset_index(drop=True)
    if risque_usd is not None:
        if "risque_usd" not in t:
            raise ValueError("risque fixe demandé mais pas de colonne risque_usd")
        n = np.floor(risque_usd / t["risque_usd"].astype(float)).astype(int)
    else:
        n = pd.Series(int(contrats), index=t.index)
    if contrats_max is not None:
        n = n.clip(upper=int(contrats_max))
    t["n"] = n
    t = t[t["n"] > 0].reset_index(drop=True)
    p1 = t["pnl_usd"].astype(float)
    mae1 = np.minimum(t["mae_usd"].astype(float), np.minimum(p1, 0.0))
    mfe1 = np.maximum(t["mfe_usd"].astype(float), p1)
    t["pnl"], t["mae"], t["mfe"] = p1 * t["n"], mae1 * t["n"], mfe1 * t["n"]
    if ordre == "prudent":
        pic_dabord = np.ones(len(t), dtype=bool)
    elif ordre == "optimiste":
        pic_dabord = np.zeros(len(t), dtype=bool)
    elif ordre == "heuristique":
        tol = 0.01 * (t["mfe"] - t["mae"]) + 1e-9
        fini_bas = (t["pnl"] - t["mae"]) <= tol
        fini_haut = (t["mfe"] - t["pnl"]) <= tol
        pic_dabord = np.where(fini_bas, True, np.where(fini_haut, False, t["pnl"] <= 0))
    else:
        raise ValueError(f"ordre inconnu : {ordre}")
    t["x1"] = np.where(pic_dabord, t["mfe"], t["mae"])
    t["x2"] = np.where(pic_dabord, t["mae"], t["mfe"])
    return t


@dataclass
class Jours:
    dates: pd.DatetimeIndex          # journées de session (lun-ven), vides comprises
    X: np.ndarray                    # (n_jours, K, 3) : x1, x2, pnl par trade
    valide: np.ndarray               # (n_jours, K)
    n_trades: np.ndarray             # (n_jours,)
    C: np.ndarray | None = None      # (n_jours, K) : contrats du trade (paliers financés)

    @property
    def n(self) -> int:
        return len(self.dates)


def grille_jours(tp: pd.DataFrame, debut=None, fin=None) -> Jours:
    """Range les trades préparés par journée de session (journées vides incluses)."""
    debut = pd.Timestamp(debut).normalize() if debut is not None else tp["jour"].min()
    fin = pd.Timestamp(fin).normalize() if fin is not None else tp["jour"].max()
    dates = pd.bdate_range(debut, fin)
    tp = tp[(tp["jour"] >= debut) & (tp["jour"] <= fin)]
    pos = dates.get_indexer(tp["jour"])
    if (pos < 0).any():   # trade un samedi/dimanche (ne devrait pas arriver) -> lundi suivant
        pos = dates.get_indexer(tp["jour"] + pd.offsets.BDay(0))
    rang = pd.Series(pos).groupby(pos).cumcount().values
    nt = np.bincount(pos, minlength=len(dates))
    K = max(1, int(nt.max()) if len(nt) else 1)
    X = np.zeros((len(dates), K, 3))
    V = np.zeros((len(dates), K), dtype=bool)
    C = np.ones((len(dates), K))
    X[pos, rang, 0] = tp["x1"].values
    X[pos, rang, 1] = tp["x2"].values
    X[pos, rang, 2] = tp["pnl"].values
    V[pos, rang] = True
    C[pos, rang] = tp["n"].values
    return Jours(dates, X, V, nt, C)


# ═════════════════════════════════════ moteur ═════════════════════════════════════
def _par_rang(liste, k):
    """liste[min(k, len−1)] vectorisé (k = numéro du prochain payout, base 0)."""
    a = np.asarray(liste, float)
    return a[np.minimum(k, len(a) - 1)]


def _moteur(J: Jours, idx: np.ndarray, r: Regles, max_jours_eval: int, max_jours_funded: int,
            max_payouts: int, demarrer_finance: bool = False, mult_palier: int = 10) -> dict:
    """Simule N parcours en parallèle. idx[i, t] = indice de la journée jouée par le parcours i au
    pas t (−1 = plus de données : parcours censuré). mult_palier = 10 si les trades sont en micros
    (les paliers de contrats financés sont en minis), 1 s'ils sont en minis."""
    N, T = idx.shape
    cap = float(r.capital)
    P0, P1 = _params_phase(r, 0), _params_phase(r, 1)
    tgt = float(r.objectif_eval_usd)
    c_ev = r.consistance_eval_pct / 100.0
    c_fu_l = np.asarray(r.constances_funded(), float) / 100.0
    cyc_l = r.objectifs_cycle()
    plaf_pay_l = [np.inf if x <= 0 else x for x in r.plafonds_payout()]
    jmin_pay = int(r.jours_min_avant_payout)
    gmin = float(r.gain_min_jour_payout_usd)
    jwin = r.jours_gagnants_min_payout
    if jwin is None:
        jwin = jmin_pay if gmin > 0 else 0
    pmin = float(r.payout_min_usd)
    tampon, solde_min = r.tampon(), r.solde_min_payout()
    pct_max = r.payout_pct_profit_max / 100.0
    part = r.partage_pct / 100.0
    if r.payouts_max > 0:
        max_payouts = min(max_payouts, int(r.payouts_max))
    if r.duree_max_eval_jours > 0:
        max_jours_eval = min(max_jours_eval, int(r.duree_max_eval_jours * 5 // 7))
    paliers = sorted([(float(p), float(m)) for p, m in r.contrats_funded_paliers]) if r.contrats_funded_paliers else []
    pal_seuils = np.array([p for p, _ in paliers])
    pal_max = np.array([m * mult_palier for _, m in paliers])
    C = J.C if J.C is not None else np.ones(J.valide.shape)

    phase = np.full(N, 1 if demarrer_finance else 0)
    B = np.full(N, cap)
    Pk = np.full(N, cap)
    plaf = np.full(N, P1["plafond"] if demarrer_finance else P0["plafond"])
    tph = np.zeros(N, int)
    act = np.zeros(N, int)
    best = np.full(N, -np.inf)
    sp_base = np.full(N, cap)
    sp_best = np.full(N, -np.inf)
    sp_act = np.zeros(N, int)
    sp_win = np.zeros(N, int)
    res_eval = np.full(N, 1 if demarrer_finance else 0)
    j_eval = np.zeros(N, int)
    ja_eval = np.zeros(N, int)
    res_fin = np.zeros(N, int)
    j_fin = np.zeros(N, int)
    n_pay = np.zeros(N, int)
    sum_pay = np.zeros(N)
    j_pay1 = np.full(N, np.nan)
    pire_marge = np.full(N, np.inf)        # plus petite distance au seuil (diagnostic)
    K = J.X.shape[1]

    def sel(key, ph):
        return np.where(ph == 0, P0[key], P1[key])

    for t in range(T):
        vivant = phase < 2
        if not vivant.any():
            break
        d = idx[:, t]
        cens = vivant & (d < 0)
        if cens.any():
            c0, c1 = cens & (phase == 0), cens & (phase == 1)
            res_eval[c0] = -3
            j_eval[c0] = tph[c0]
            res_fin[c1] = -3
            j_fin[c1] = tph[c1]
            phase[cens] = 2
            vivant &= ~cens
        dd_i = np.where(vivant, d, 0)
        ph = phase.copy()
        ddv, typ = sel("dd", ph), sel("type", ph)
        dll, dlt = sel("dll", ph), sel("dll_type", ph)
        D0 = B.copy()
        niv_dll = np.where(dlt > 0, D0 - dll, -np.inf)
        # paliers de contrats en financé (profit de clôture de la veille)
        if len(paliers):
            k_pal = np.searchsorted(pal_seuils, B - cap, side="right") - 1
            cmax_j = np.where((ph == 1) & (k_pal >= 0), pal_max[np.maximum(k_pal, 0)], np.inf)
        else:
            cmax_j = np.full(N, np.inf)
        en_jeu = vivant.copy()
        trade_jour = np.zeros(N, bool)
        echec = np.zeros(N, bool)
        nt = J.n_trades[dd_i]
        for k in range(K):
            v = en_jeu & J.valide[dd_i, k]
            if not v.any():
                if not (en_jeu & (nt > k)).any():
                    break
                continue
            trade_jour |= v
            fact = np.minimum(1.0, cmax_j / C[dd_i, k])
            fini = np.zeros(N, bool)
            for j in range(3):
                x = J.X[dd_i, k, j] * fact
                m = v & ~fini
                eq = B + x
                Pk = np.where(m & (typ == 0), np.maximum(Pk, eq), Pk)
                seuil = np.where(typ == 2, cap - ddv, np.minimum(Pk - ddv, cap + plaf))
                pire_marge = np.where(m, np.minimum(pire_marge, eq - seuil), pire_marge)
                t_dd = m & (eq <= seuil)
                t_dll = m & (eq <= niv_dll)
                f = (t_dd & ((dlt != 1) | (seuil >= niv_dll))) | (t_dll & (dlt == 2))
                soft = t_dll & (dlt == 1) & ~f
                if f.any():
                    echec |= f
                    en_jeu &= ~f
                    fini |= f
                if soft.any():
                    B = np.where(soft, niv_dll, B)
                    en_jeu &= ~soft
                    fini |= soft
                if j == 2:
                    ok = m & ~f & ~soft
                    B = np.where(ok, B + x, B)
        # ── échecs du jour ──
        if echec.any():
            e0, e1 = echec & (ph == 0), echec & (ph == 1)
            res_eval[e0] = -1
            j_eval[e0] = tph[e0] + 1
            ja_eval[e0] = act[e0] + 1
            res_fin[e1] = -1
            j_fin[e1] = tph[e1] + 1
            phase[echec] = 2
        ok = vivant & ~echec
        tph[ok] += 1
        act[ok & trade_jour] += 1
        dp = B - D0
        Pk = np.where(ok & (typ == 1), np.maximum(Pk, B), Pk)
        # ── éval ──
        ev = ok & (ph == 0)
        best = np.where(ev & trade_jour, np.maximum(best, dp), best)
        gain = B - cap
        cons = (c_ev <= 0) | (best <= c_ev * gain + 1e-9)
        passe = ev & (B >= cap + tgt - 1e-9) & (act >= r.jours_min_eval) & cons
        if passe.any():
            res_eval[passe] = 1
            j_eval[passe] = tph[passe]
            ja_eval[passe] = act[passe]
            phase[passe] = 1
            B[passe] = cap
            Pk[passe] = cap
            plaf[passe] = P1["plafond"]
            tph[passe] = 0
            act[passe] = 0
            sp_base[passe] = cap
            sp_best[passe] = -np.inf
            sp_act[passe] = 0
            sp_win[passe] = 0
        hors_delai = ev & ~passe & (tph >= max_jours_eval)
        if hors_delai.any():
            res_eval[hors_delai] = -2
            j_eval[hors_delai] = tph[hors_delai]
            ja_eval[hors_delai] = act[hors_delai]
            phase[hors_delai] = 2
        # ── financé ──
        fu = ok & (ph == 1)
        if fu.any():
            sp_act[fu & trade_jour] += 1
            gagnant = trade_jour & ((dp >= gmin) if gmin > 0 else (dp > 0))
            sp_win[fu & gagnant] += 1
            sp_best = np.where(fu & trade_jour, np.maximum(sp_best, dp), sp_best)
            gsp = B - sp_base
            c_fu = _par_rang(c_fu_l, n_pay)
            cons_f = (c_fu <= 0) | (sp_best <= c_fu * gsp + 1e-9)
            cyc = _par_rang(cyc_l, n_pay)
            retirable = B - tampon
            if pct_max > 0:
                retirable = np.minimum(retirable, pct_max * (B - cap))
            montant = np.minimum(retirable, _par_rang(plaf_pay_l, n_pay))
            elig = (fu & (sp_act >= jmin_pay) & (sp_win >= jwin) & cons_f & (B >= solde_min - 1e-9)
                    & (gsp >= cyc - 1e-9) & ((cyc <= 0) | (gsp > 0)) & (montant >= pmin - 1e-9))
            if elig.any():
                if r.drawdown_bloque_a_la_demande_payout:
                    typ1 = P1["type"]
                    if typ1 != 2:
                        seuil_now = np.minimum(Pk - P1["dd"], cap + plaf)
                        plaf = np.where(elig, np.minimum(plaf, seuil_now - cap), plaf)
                B = np.where(elig, B - montant, B)
                sum_pay += np.where(elig, montant * part, 0.0)
                premier = elig & (n_pay == 0)
                j_pay1[premier] = tph[premier]
                n_pay[elig] += 1
                sp_base = np.where(elig, B, sp_base)
                sp_best[elig] = -np.inf
                sp_act[elig] = 0
                sp_win[elig] = 0
            fin = fu & ((n_pay >= max_payouts) | (tph >= max_jours_funded))
            if fin.any():
                res_fin[fin] = 1
                j_fin[fin] = tph[fin]
                phase[fin] = 2
    # parcours encore vivants à la fin de idx : censurés
    rest = phase < 2
    r0, r1 = rest & (phase == 0), rest & (phase == 1)
    res_eval[r0] = -3
    j_eval[r0] = tph[r0]
    res_fin[r1] = -3
    j_fin[r1] = tph[r1]
    return {"res_eval": res_eval, "j_eval": j_eval, "ja_eval": ja_eval, "res_fin": res_fin,
            "j_fin": j_fin, "n_pay": n_pay, "sum_pay": sum_pay, "j_pay1": j_pay1,
            "solde_final": B, "pire_marge": pire_marge}


def _frais(out: dict, r: Regles, direct: bool = False) -> np.ndarray:
    je = np.maximum(out["j_eval"], 1)
    fe = r.frais_eval_usd * (np.ceil(je / JOURS_PAR_MOIS) if (r.frais_eval_mensuels and not direct) else 1.0)
    reussi = out["res_eval"] == 1
    jf = np.maximum(out["j_fin"], 1)
    fa = r.frais_activation_usd * (np.ceil(jf / JOURS_PAR_MOIS) if r.frais_activation_mensuels else 1.0)
    return fe + np.where(reussi, fa, 0.0)


def _resume(out: dict, r: Regles, max_payouts: int, direct: bool = False) -> dict:
    re, rf = out["res_eval"], out["res_fin"]
    n = len(re)
    reussi = re == 1
    resolu = re != -3
    frais = _frais(out, r, direct)
    net = out["sum_pay"] - frais
    # hors frais d'éval (utile quand le prix est introuvable : -1 dans regles.toml)
    act = r.frais_activation_usd if np.isfinite(r.frais_activation_usd) else 0.0
    brut = out["sum_pay"] - np.where(reussi, act, 0.0)
    m = {
        "n_parcours": int(n),
        "p_reussite": float(reussi.mean()),
        "p_echec": float((re == -1).mean()),
        "p_hors_delai": float((re == -2).mean()),
        "p_censure": float((re == -3).mean()),
        "p_reussite_resolus": float(reussi[resolu].mean()) if resolu.any() else float("nan"),
        "delai_median_jours": float(np.median(out["j_eval"][reussi])) if reussi.any() else float("nan"),
        "delai_median_jours_actifs": float(np.median(out["ja_eval"][reussi])) if reussi.any() else float("nan"),
        "delai_p75_jours": float(np.percentile(out["j_eval"][reussi], 75)) if reussi.any() else float("nan"),
        "p_1er_payout": float((out["n_pay"] >= 1).mean()),
        "p_1er_payout_si_reussite": float((out["n_pay"][reussi] >= 1).mean()) if reussi.any() else float("nan"),
        "p_echec_finance_si_reussite": float((rf[reussi] == -1).mean()) if reussi.any() else float("nan"),
        "p_censure_finance_si_reussite": float((rf[reussi] == -3).mean()) if reussi.any() else float("nan"),
        "delai_median_1er_payout_jours": float(np.nanmedian(out["j_pay1"])) if (out["n_pay"] >= 1).any() else float("nan"),
        "payouts_moyens_usd": float(out["sum_pay"].mean()),
        "frais_moyens_usd": float(frais.mean()),
        "valeur_esperee_usd": float(net.mean()),
        "valeur_esperee_resolus_usd": float(net[resolu].mean()) if resolu.any() else float("nan"),
        "valeur_hors_frais_eval_usd": float(brut.mean()),
        "frais_eval_usd": float(r.frais_eval_usd),
        "financement_direct": bool(direct),
    }
    for k in range(1, max_payouts + 1):
        m[f"p_{k}_payouts"] = float((out["n_pay"] >= k).mean())
    return m


def _idx_bootstrap(nj: int, N: int, T: int, bloc: int, rng) -> np.ndarray:
    bloc = max(1, min(int(bloc), nj))
    nb = math.ceil(T / bloc)
    deb = rng.integers(0, nj - bloc + 1, size=(N, nb))
    return (deb[:, :, None] + np.arange(bloc)[None, None, :]).reshape(N, -1)[:, :T]


def _idx_chrono(nj: int, pas: int = 1, T: int | None = None) -> np.ndarray:
    starts = np.arange(0, nj, max(1, pas))
    T = nj if T is None else T
    idx = starts[:, None] + np.arange(T)[None, :]
    idx[idx >= nj] = -1
    return idx


def monte_carlo(trades: pd.DataFrame, regles: Regles, contrats: int = 1, *, instrument: str = "micro",
                risque_usd: float | None = None, methode: str = "bootstrap", n_sim: int = 2000,
                bloc_jours: int = 5, max_jours_eval: int = 250, max_jours_funded: int = 250,
                max_payouts: int = 5, ordre: str = "prudent", nuit: str = "garder", graine: int = 0,
                pas_chrono: int = 1, debut=None, fin=None, details: bool = False) -> dict:
    """P(réussite), délai, survie au payout, valeur espérée d'une tentative.

    methode="bootstrap"     : n_sim parcours de journées tirées par blocs de `bloc_jours` journées
                              consécutives (journées vides incluses : la fréquence des trades est gardée).
    methode="chronologique" : un parcours par journée de départ possible, rejoué dans l'ordre réel
                              (fenêtres glissantes ; les parcours qui sortent des données sont « censurés »).
    """
    cmax = regles.contrats_max(instrument)
    meta = {"variante": regles.nom, "propfirm": regles.propfirm, "contrats": contrats,
            "instrument": instrument, "risque_usd": risque_usd, "methode": methode, "ordre": ordre,
            "nuit": nuit, "regles_source": regles.fichier_regles}
    if risque_usd is None and contrats > cmax:
        return {**meta, "taille_autorisee": False}
    tp = prepare_trades(trades, contrats, risque_usd=risque_usd, contrats_max=cmax, ordre=ordre, nuit=nuit)
    J = grille_jours(tp, debut, fin)
    rng = np.random.default_rng(graine)
    if methode == "bootstrap":
        idx = _idx_bootstrap(J.n, n_sim, max_jours_eval + max_jours_funded, bloc_jours, rng)
    elif methode == "chronologique":
        idx = _idx_chrono(J.n, pas_chrono)
    else:
        raise ValueError(methode)
    direct = regles.financement_direct()
    out = _moteur(J, idx, regles, max_jours_eval, max_jours_funded, max_payouts, demarrer_finance=direct,
                  mult_palier=10 if instrument == "micro" else 1)
    res = {**meta, "taille_autorisee": True, "n_trades": int(len(tp)), "n_jours_donnees": int(J.n),
           "pct_traverse_fermeture": float(tp["traverse_fermeture"].mean()) if len(tp) else 0.0,
           **_resume(out, regles, max_payouts, direct)}
    if details:
        res["_parcours"] = out
    return res


def simule_chemin(trades: pd.DataFrame, regles: Regles, contrats: int = 1, *, ordre: str = "prudent",
                  demarrer_finance: bool = False, max_jours_eval: int = 10_000,
                  max_jours_funded: int = 10_000, max_payouts: int = 100, instrument: str = "micro",
                  nuit: str = "garder") -> dict:
    """Rejeu unique, dans l'ordre, depuis la première journée (sert aux tests et au contrôle)."""
    tp = prepare_trades(trades, contrats, contrats_max=None, ordre=ordre, nuit=nuit)
    J = grille_jours(tp)
    idx = _idx_chrono(J.n)[:1]
    out = _moteur(J, idx, regles, max_jours_eval, max_jours_funded, max_payouts,
                  demarrer_finance or regles.financement_direct(), mult_palier=10 if instrument == "micro" else 1)
    return {k: (v[0].item() if isinstance(v, np.ndarray) else v) for k, v in out.items()}


# ═════════════════════════════════ optimisation, référence ═════════════════════════════════
CRITERES = {"valeur_esperee": "valeur_esperee_usd", "p_reussite": "p_reussite",
            "p_1er_payout": "p_1er_payout"}


def optimise_taille(trades: pd.DataFrame, regles: Regles, tailles=None, critere: str = "valeur_esperee",
                    instrument: str = "micro", **kw) -> tuple[pd.DataFrame, dict]:
    """Balaye le nombre de contrats (1..max) ; renvoie (tableau, meilleure ligne selon `critere`)."""
    if tailles is None:
        tailles = range(1, min(regles.contrats_max(instrument), 40) + 1)
    lignes = []
    for c in tailles:
        res = monte_carlo(trades, regles, c, instrument=instrument, **kw)
        if res.get("taille_autorisee"):
            lignes.append(res)
    df = pd.DataFrame(lignes)
    col = CRITERES.get(critere, critere)
    if col == "valeur_esperee_usd" and len(df) and df[col].isna().all():
        col = "valeur_hors_frais_eval_usd"        # prix de l'éval introuvable
    meilleur = df.loc[df[col].idxmax()].to_dict() if len(df) else {}
    return df, meilleur


def analyse_reference(trades_hasard, regles: Regles, contrats: int = 1, **kw) -> dict:
    """Même analyse sur des trades « au hasard » fournis par l'appelant (un DataFrame ou une liste
    de tirages). Renvoie la moyenne des métriques sur les tirages + min/max de P(réussite)."""
    tirages = [trades_hasard] if isinstance(trades_hasard, pd.DataFrame) else list(trades_hasard)
    n_sim = kw.pop("n_sim", 2000)
    rs = [monte_carlo(t, regles, contrats, n_sim=max(200, n_sim // len(tirages)), graine=i, **kw)
          for i, t in enumerate(tirages)]
    rs = [r for r in rs if r.get("taille_autorisee")]
    if not rs:
        return {"taille_autorisee": False}
    num = {k: float(np.nanmean([r[k] for r in rs])) for k, v in rs[0].items()
           if isinstance(v, (int, float, np.floating)) and not isinstance(v, bool)}
    meta = {k: v for k, v in rs[0].items() if k not in num}
    ps = [r["p_reussite"] for r in rs]
    return {**meta, **num, "n_tirages": len(rs), "p_reussite_min": min(ps), "p_reussite_max": max(ps),
            "reference": True}


def stats_trades(trades: pd.DataFrame, contrats: int = 1) -> dict:
    """Statistiques classiques à la taille donnée (P&L net, PF, % gagnants, R moyen, DD max clôturé)."""
    p = trades["pnl_usd"].astype(float).values * contrats
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    eq = np.cumsum(p)
    dd = float((np.maximum.accumulate(np.concatenate([[0], eq])) - np.concatenate([[0], eq])).max())
    r = trades["r"].astype(float).mean() if "r" in trades else float("nan")
    return {"n_trades": int(len(p)), "pct_gagnants": float(100 * (p > 0).mean()),
            "r_moyen": float(r), "pf": float(g / l) if l > 0 else float("nan"),
            "gain_net_usd": float(p.sum()), "dd_max_usd": dd}


# ═════════════════════════════════════ rapport ═════════════════════════════════════
COLONNES_RAPPORT = [
    ("variante", "Variante"), ("contrats", "Taille"), ("methode", "Méthode"),
    ("p_reussite", "P(réussite)"), ("p_echec", "P(échec)"), ("delai_median_jours", "Délai méd. (j)"),
    ("p_1er_payout", "P(1er payout)"), ("p_3_payouts", "P(≥3 payouts)"),
    ("valeur_esperee_usd", "Valeur espérée $"),
]
METRIQUES_COMPACTES = ["variante", "propfirm", "regles_source", "financement_direct", "contrats", "instrument", "methode", "ordre", "n_trades",
                       "p_reussite", "p_echec", "p_hors_delai", "p_censure", "delai_median_jours",
                       "delai_median_jours_actifs", "p_1er_payout", "p_1er_payout_si_reussite",
                       "p_3_payouts", "payouts_moyens_usd", "frais_moyens_usd", "valeur_esperee_usd",
                       "valeur_hors_frais_eval_usd",
                       "pct_traverse_fermeture"]


def _fmt(v, k):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if k.startswith("p_") and isinstance(v, (float, np.floating)):
        return f"{100 * v:.1f} %"
    if isinstance(v, (float, np.floating)):
        return f"{v:,.0f}".replace(",", " ")
    return str(v)


def rapport(resultats, chemin_md: str | Path | None = None, titre: str = "Simulation propfirm") -> dict:
    """Renvoie un dict compact (ou une liste de dicts) et écrit un résumé Markdown si demandé."""
    seul = isinstance(resultats, dict)
    liste = [resultats] if seul else list(resultats)
    compact = [{k: r.get(k) for k in METRIQUES_COMPACTES if k in r} for r in liste]
    if chemin_md is not None:
        lignes = [f"# {titre}", "", "| " + " | ".join(h for _, h in COLONNES_RAPPORT) + " |",
                  "|" + "---|" * len(COLONNES_RAPPORT)]
        for r in liste:
            lignes.append("| " + " | ".join(_fmt(r.get(k), k) for k, _ in COLONNES_RAPPORT) + " |")
        Path(chemin_md).write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return compact[0] if seul else compact
