"""Moteur de backtest UNIQUE de KAIROS (futures MNQ / MES / NQ / ES, propfirm).

Repris de tools/strategie/engine.py et tools/strategie/optim/moteur.py (conventions prudentes), réécrit
pour : vrais prix fournis, multi-unités (signal 15m, exécution 2m/5m), stops sur niveaux, objectifs sur
niveaux, sortie forcée à l'heure propfirm, coûts par instrument, MAE/MFE en $.

CONVENTIONS (toutes paramétrables via `gestion`, voir GESTION_DEFAUT)
- Horodatage d'une barre = son OUVERTURE (convention des exports TradingView) ; clôture = ouverture + UT.
- Signal booléen calculé à la CLÔTURE de la barre signal i -> ordre placé après cette clôture :
    * au marché : rempli à l'OUVERTURE de la 1re barre d'exécution qui ouvre à/après la clôture de i,
      + glissement (1 tick contre nous par défaut) ;
    * à cours limité (prix fourni par barre signal, valable N barres d'exécution) : rempli si le prix
      TRAVERSE le niveau d'au moins `traverse_ticks` tick(s), au niveau (ou à l'ouverture si elle est
      déjà au-delà) ; pas de glissement sur un ordre limite sauf `glissement_sur_limites=True`.
  Pas d'entrée si cette ouverture arrive plus de `retard_max_min` minutes après la clôture du signal
  (trou de données, week-end) ; défaut = 0,5 x UT d'exécution (= règle « coupure » de engine.py).
- Multi-UT : les tableaux « signal » (entrées, sorties sur signal, ATR, niveaux, prix limites) vivent sur
  les barres signal ; ils ne sont connus qu'à la clôture de leur barre (aucun regard vers le futur).
  Mono-UT : passer df_signal=None (signal et exécution sur les mêmes barres).
- Stop (ordre stop au marché) : rempli au stop - glissement ; si l'OUVERTURE a déjà sauté le stop
  (écart), rempli à l'ouverture - glissement.
- Objectif / sortie partielle (ordres limites) : remplis si le prix dépasse le niveau de `traverse_ticks`.
  Ouverture au-delà de l'objectif : remplis à l'ouverture (meilleur prix).
- Stop ET objectif touchés dans la même barre : STOP (prudent). Sur la barre de remplissage d'un ordre
  limite rempli en cours de barre : stop possible, objectif impossible (ordre des événements inconnu).
- Break-even, suiveur ATR : recalculés à la CLÔTURE de chaque barre, actifs à partir de la suivante.
- Sorties décidées à la clôture : heure propfirm (à la clôture de la dernière barre qui finit avant
  l'heure limite, - glissement), sortie sur signal et sortie temporelle (à l'OUVERTURE suivante,
  - glissement). Ordre de priorité : heure > signal > temps.
- Une position (ou un ordre en attente) à la fois. Option : max de trades par jour (journée CME,
  17:00 Chicago -> 17:00 Chicago).
- Coûts : glissement dans les prix de remplissage ; commission par côté et par contrat retirée du PnL.
  r = pnl_usd / risque_usd, risque_usd = |entrée - stop initial| x valeur du point (sans les coûts).
- mae_usd (<= 0) / mfe_usd (>= 0) : pire / meilleure plus-value LATENTE d'un contrat, mesurée depuis le
  prix d'entrée (glissement compris), hors commission ; sur la barre de sortie on ne compte que ce qui a
  pu arriver avant la sortie (ouverture pour une sortie à l'ouverture, prix du stop pour un stop, etc.,
  en gardant l'autre extrême de la barre : prudent pour un drawdown suiveur).
"""
from __future__ import annotations

import math
import os
import re
import weakref
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

PARIS = ZoneInfo('Europe/Paris')
CHICAGO = ZoneInfo('America/Chicago')
NS_MIN = 60_000_000_000
NS_JOUR = 1440 * NS_MIN

INSTRUMENTS = {
    'MNQ': dict(point=2.0, tick=0.25, commission_cote=0.62),
    'MES': dict(point=5.0, tick=0.25, commission_cote=0.62),
    'NQ': dict(point=20.0, tick=0.25, commission_cote=2.25),
    'ES': dict(point=50.0, tick=0.25, commission_cote=2.25),
}

COLONNES_TRADES = ['entree_t', 'sortie_t', 'sens', 'prix_entree', 'stop_initial', 'objectif', 'prix_sortie',
                   'motif_sortie', 'r', 'pnl_usd', 'risque_usd', 'mae_usd', 'mfe_usd', 'barres', 'niveau_stop',
                   'niveau_objectif']

GESTION_DEFAUT = dict(
    instrument='MNQ',            # clé de INSTRUMENTS, ou dict(point=, tick=, commission_cote=)
    commission_cote=None,        # $ par contrat et par côté ; None = défaut de l'instrument
    glissement_ticks=1,          # par côté, sur les ordres au marché et stop
    glissement_sur_limites=False,
    traverse_ticks=1,            # un ordre limite n'est rempli que si le prix dépasse le niveau de N ticks
    arrondi_tick=True,           # stops / objectifs arrondis au tick le plus proche
    sens='les_deux',             # 'les_deux' | 'long' | 'short'
    # --- entrée : {'mode': 'marche'} ou {'mode': 'limite', 'long': prix, 'short': prix, 'validite': 4}
    entree=None,
    # --- stop : {'mode': 'atr', 'k': 2.0} | {'mode': 'points', 'points': 20.0} | {'mode': 'aucun', 'k_ref': 1.0}
    #     | {'mode': 'niveau', 'long': tableau ou {nom: tableau}, 'short': idem, 'marge_ticks': 2, 'marge_atr': 0.0,
    #        'min_atr': 0.25, 'max_atr': 4.0, 'choix': 'ordre'|'proche'|'loin', 'repli_k': 2.0, 'sauter': False}
    stop=None,
    # --- objectif : {'mode': 'aucun'} | {'mode': 'R', 'k': 2.0} | {'mode': 'points', 'points': 40.0}
    #     | {'mode': 'niveau', 'long': ..., 'short': ..., 'ratio_min': 1.5, 'marge_ticks': 0,
    #        'si_absent': 'aucun'|'sauter'|('R', 2.0)}
    objectif=None,
    break_even=None,             # {'R': 1.0, 'ticks': 1} : stop à entrée + ticks dès que la MFE atteint R
    suiveur=None,                # {'k': 3.0, 'activation_R': 0.0, 'ref': 'extreme'|'cloture'} (ATR exécution)
    partiel=None,                # {'R': 1.0, 'fraction': 0.5, 'be_apres': True}
    sortie_signal=None,          # {'long': bool (sortir d'un long), 'short': bool} sur les barres signal
    sortie_barres=0,             # sortie temporelle après N barres d'exécution (0 = non)
    heure_sortie='15:59',        # à plat avant cette heure (fuseau_sortie) ; None = pas de sortie forcée
    fuseau_sortie='America/Chicago',
    heure_reprise='17:00',       # [heure_sortie, heure_reprise) : ni position ni entrée
    plages_interdites=(),        # [('HH:MM', 'HH:MM'), ...] : pas d'ENTRÉE (heure d'ouverture de la barre d'entrée)
    plages_autorisees=None,      # idem, liste blanche (None = tout)
    fuseau_plages='Europe/Paris',
    max_trades_jour=0,           # 0 = illimité (journée CME)
    retard_max_min=None,         # None = 0,5 x UT d'exécution
    fin_donnees='cloture',       # 'cloture' (sortie à la dernière clôture, motif fin_donnees) | 'abandon'
)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Barres
# ════════════════════════════════════════════════════════════════════════════════════════════════
def atr_wilder(h, l, c, periode=14):
    """ATR de Pine (ta.atr) : RMA du true range amorcée par une moyenne simple. NaN avant `periode` barres."""
    h = np.asarray(h, float); l = np.asarray(l, float); c = np.asarray(c, float)
    n = len(c)
    tr = np.empty(n)
    if n == 0:
        return tr
    tr[0] = h[0] - l[0]
    pc = c[:-1]
    tr[1:] = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - pc), np.abs(l[1:] - pc)))
    out = np.full(n, np.nan)
    if n < periode:
        return out
    a = tr[:periode].mean(); out[periode - 1] = a
    trl = tr.tolist(); al = out.tolist(); p = float(periode)
    for i in range(periode, n):
        a = (a * (p - 1) + trl[i]) / p
        al[i] = a
    return np.array(al)


def _temps(df, fuseau_naif):
    if isinstance(df.index, pd.DatetimeIndex):
        t = df.index
    else:
        col = None
        low = {str(k).lower(): k for k in df.columns}
        for k in ('time', 't', 'datetime', 'date', 'horodatage', 'timestamp'):
            if k in low:
                col = low[k]; break
        if col is None:
            raise ValueError("pas d'index temporel ni de colonne time/t/datetime/date/horodatage")
        s = df[col]
        if np.issubdtype(s.dtype, np.number):
            unit = 'ms' if s.iloc[0] > 1e11 else 's'
            t = pd.DatetimeIndex(pd.to_datetime(s.to_numpy(), unit=unit, utc=True))
        else:
            txt = str(s.iloc[0])
            avec_decalage = bool(re.search(r'(Z|[+-]\d\d:?\d\d)$', txt))
            t = pd.DatetimeIndex(pd.to_datetime(s, utc=avec_decalage))
    if t.tz is None:
        t = t.tz_localize(fuseau_naif, ambiguous='NaT', nonexistent='shift_forward')
    return t.tz_convert('UTC')


class Barres:
    """Barres prêtes pour le moteur : temps en ns UTC (ouverture / clôture), o/h/l/c/atr en float64.

    colonnes : correspondance optionnelle {'open': 'nom', 'high': ..., 'low': ..., 'close': ..., 'atr': ...}.
    Sinon, recherche insensible à la casse, dans cet ordre : o/h/l/c (VRAIS prix de dataset/charger.py),
    open/high/low/close, ro/rh/rl/rc ; les colonnes ha_* (Heiken Ashi) ne sont JAMAIS prises.
    ATR : colonne atr (ou ratr), sinon ATR14 de Wilder calculé sur ces prix."""

    def __init__(self, df, colonnes=None, ut_min=None, horodatage='ouverture', fuseau_naif='Europe/Paris',
                 atr_periode=14):
        self.df = df
        colonnes = colonnes or {}
        low = {str(k).lower(): k for k in df.columns}

        noms = {'open': ('o', 'open', 'ro'), 'high': ('h', 'high', 'rh'), 'low': ('l', 'low', 'rl'),
                'close': ('c', 'close', 'rc'), 'atr': ('atr', 'ratr')}

        def col(nom, obligatoire=True):
            k = colonnes.get(nom)
            if k is None:
                k = next((low[x] for x in noms[nom] if x in low), None)
            if k is None:
                if obligatoire:
                    raise ValueError('colonne %s introuvable' % nom)
                return None
            return df[k].to_numpy(dtype=float)
        self.o, self.h, self.l, self.c = col('open'), col('high'), col('low'), col('close')
        t = _temps(df, fuseau_naif).as_unit('ns').asi8.astype(np.int64)
        self.n = len(t)
        if ut_min is None:
            ut_min = float(np.median(np.diff(t))) / NS_MIN if self.n > 1 else 1.0
        self.ut = float(ut_min)
        dt = int(round(self.ut * NS_MIN))
        if horodatage == 'cloture':
            t = t - dt
        self.t_ouv = t
        self.t_clo = t + dt
        a = col('atr', False)
        self.atr = a if a is not None else atr_wilder(self.h, self.l, self.c, atr_periode)
        self._cache = {}

    def tableau(self, x, dtype=float):
        """Résout un tableau : nom de colonne (str), Series, liste ou ndarray -> ndarray de longueur n."""
        if x is None:
            return None
        if isinstance(x, str):
            x = self.df[x]
        a = np.asarray(x.to_numpy() if hasattr(x, 'to_numpy') else x)
        if len(a) != self.n:
            raise ValueError('tableau de longueur %d pour %d barres' % (len(a), self.n))
        if dtype is bool:
            if a.dtype != bool:
                a = np.nan_to_num(a.astype(float), nan=0.0) != 0
            return a
        return a.astype(float)

    # ---- temps locaux (mis en cache)
    def _local(self, fuseau):
        k = ('loc', fuseau)
        if k not in self._cache:
            idx = _dti(self.t_ouv).tz_convert(ZoneInfo(fuseau))
            naif = idx.tz_localize(None).as_unit('ns').asi8
            self._cache[k] = (idx, naif, ((naif % NS_JOUR) // NS_MIN).astype(np.int64))
        return self._cache[k]

    def minutes_locales(self, fuseau):
        return self._local(fuseau)[2]

    def jour_cme(self):
        """Clé de journée CME (17:00 Chicago -> 17:00 Chicago) de chaque barre (ouverture)."""
        k = 'jour'
        if k not in self._cache:
            naif = self._local('America/Chicago')[1]
            self._cache[k] = (naif + 7 * 60 * NS_MIN) // NS_JOUR
        return self._cache[k]

    def drapeaux_heure(self, heure, reprise, fuseau):
        """(fin, interdite) : fin[k] = dernière barre qui CLÔTURE avant l'heure limite ;
        interdite[k] = la barre OUVRE dans [heure, reprise)."""
        k = ('heure', heure, reprise, fuseau)
        if k in self._cache:
            return self._cache[k]
        idx, naif, mins = self._local(fuseau)
        H = _hm(heure); Rp = _hm(reprise) if reprise else H
        jour = naif - naif % NS_JOUR
        cible = jour + H * NS_MIN + np.where(mins > H, NS_JOUR, 0)
        D = pd.DatetimeIndex(pd.to_datetime(cible, unit='ns')).tz_localize(ZoneInfo(fuseau), ambiguous='NaT',
                                                nonexistent='shift_forward').tz_convert('UTC').as_unit('ns').asi8
        dt = self.t_clo - self.t_ouv
        # trou de données : si la barre suivante OUVRE après l'heure limite, cette barre est la dernière
        # avant la limite (sinon une position traverserait le trou, et la nuit, sans être fermée)
        ouv_suiv = np.append(self.t_ouv[1:], np.iinfo(np.int64).max)
        fin = (self.t_clo <= D) & ((self.t_clo + dt > D) | (ouv_suiv > D))
        interdite = _dans_plage(mins, H, Rp)
        self._cache[k] = (fin, interdite)
        return fin, interdite


def _dti(ns):
    """entiers ns UTC -> DatetimeIndex UTC."""
    return pd.DatetimeIndex(pd.to_datetime(np.asarray(ns, np.int64), unit='ns', utc=True))


def _hm(s):
    if isinstance(s, (int, np.integer)):
        return int(s)
    hh, mm = str(s).split(':')
    return int(hh) * 60 + int(mm)


def _dans_plage(mins, a, b):
    if a == b:
        return np.zeros(len(mins), bool)
    return (mins >= a) & (mins < b) if a < b else (mins >= a) | (mins < b)


_CACHE = {}


def barres(df, **kw):
    """Barres (mises en cache par objet DataFrame : réutilisées tant que le DataFrame existe)."""
    if isinstance(df, Barres):
        return df
    key = (id(df), tuple(sorted((k, repr(v)) for k, v in kw.items())))
    hit = _CACHE.get(key)
    if hit is not None and hit[0]() is df and hit[1].n == len(df):
        return hit[1]
    b = Barres(df, **kw)
    if len(_CACHE) > 64:
        _CACHE.clear()
    _CACHE[key] = (weakref.ref(df), b)
    return b


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Projection barres signal -> barres d'exécution (aucun regard vers le futur)
# ════════════════════════════════════════════════════════════════════════════════════════════════
def projection(ex: Barres, sg: Barres | None):
    """idx[k] = dernière barre signal dont la CLÔTURE est <= l'ouverture de la barre d'exécution k+1,
    c.-à-d. l'information disponible quand on décide, à la clôture de k, d'un ordre pour k+1."""
    if sg is None or sg is ex:
        return np.arange(ex.n)
    nxt = np.empty(ex.n, np.int64)
    nxt[:-1] = ex.t_ouv[1:]
    nxt[-1] = ex.t_clo[-1]
    return np.searchsorted(sg.t_clo, nxt, side='right') - 1


def _evenement(sig, idx):
    """Pour chaque décision k : indice de la dernière barre signal VRAIE arrivée depuis la décision
    précédente (sinon -1)."""
    n = len(sig)
    pos = np.where(sig, np.arange(n), -1)
    last = np.maximum.accumulate(pos) if n else pos
    li = np.where(idx >= 0, last[np.clip(idx, 0, max(n - 1, 0))], -1)
    prev = np.r_[-1, idx[:-1]]
    return np.where((li > prev) & (li >= 0), li, -1)


def _evenement_any(sig, idx):
    cs = np.r_[0, np.cumsum(sig.astype(np.int64))]
    prev = np.r_[-1, idx[:-1]]
    return (cs[idx + 1] - cs[prev + 1]) > 0


def _niveaux(sg, x):
    """tableau ou {nom: tableau} -> liste [(nom, ndarray)]."""
    if x is None:
        return []
    if isinstance(x, dict):
        return [(str(k), sg.tableau(v)) for k, v in x.items()]
    return [(x if isinstance(x, str) else 'niveau', sg.tableau(x))]


def _gestion(g):
    out = dict(GESTION_DEFAUT)
    if g:
        inconnues = set(g) - set(GESTION_DEFAUT)
        if inconnues:
            raise KeyError('clés de gestion inconnues : %s' % sorted(inconnues))
        out.update(g)
    out['entree'] = out['entree'] or {'mode': 'marche'}
    out['stop'] = out['stop'] or {'mode': 'atr', 'k': 2.0}
    out['objectif'] = out['objectif'] or {'mode': 'aucun'}
    return out


def instrument(nom_ou_dict, commission=None):
    spec = dict(INSTRUMENTS[nom_ou_dict.upper()]) if isinstance(nom_ou_dict, str) else dict(nom_ou_dict)
    if commission is not None:
        spec['commission_cote'] = float(commission)
    return spec


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Backtest
# ════════════════════════════════════════════════════════════════════════════════════════════════
def backtest(df, long=None, short=None, gestion=None, df_signal=None, details=False):
    """Backtest une position à la fois.

    df        : barres d'EXÉCUTION (DataFrame ou Barres), vrais prix open/high/low/close (+ atr optionnel).
    long/short: signaux booléens (tableau, Series ou nom de colonne) sur les barres SIGNAL.
    df_signal : barres signal (multi-UT) ; None = mêmes barres que df (mono-UT).
    gestion   : dict, voir GESTION_DEFAUT.
    Renvoie un DataFrame de trades (COLONNES_TRADES). details=True ajoute les indices de barres
    (i_signal, k_entree, k_sortie) en colonnes supplémentaires."""
    G = _gestion(gestion)
    ex = barres(df)
    sg = ex if df_signal is None else barres(df_signal)
    spec = instrument(G['instrument'], G['commission_cote'])
    pv, tick, comm = spec['point'], spec['tick'], spec['commission_cote']
    slip = G['glissement_ticks'] * tick
    trav = G['traverse_ticks'] * tick
    slip_lim = slip if G['glissement_sur_limites'] else 0.0
    n = ex.n
    idx = projection(ex, sg)

    # ---- événements d'entrée
    zero = np.zeros(sg.n, bool)
    L = sg.tableau(long, bool) if long is not None else zero
    S = sg.tableau(short, bool) if short is not None else zero
    if G['sens'] == 'long':
        S = zero
    elif G['sens'] == 'short':
        L = zero
    eL, eS = _evenement(L, idx), _evenement(S, idx)
    isig = np.where(eL > eS, eL, eS)
    sens = np.where(eL > eS, 1, -1)
    cand = isig >= 0
    cand &= eL != eS                      # long et short sur la même barre : ambigu -> rien
    cand[-1] = False
    k_all = np.arange(n)
    e = np.minimum(k_all + 1, n - 1)
    retard = G['retard_max_min']
    retard = 0.5 * ex.ut if retard is None else retard
    tc = np.where(isig >= 0, sg.t_clo[np.clip(isig, 0, sg.n - 1)], 0)
    cand &= (ex.t_ouv[e] - tc) <= retard * NS_MIN
    if G['heure_sortie']:
        fin, interdite = ex.drapeaux_heure(G['heure_sortie'], G['heure_reprise'], G['fuseau_sortie'])
    else:
        fin = interdite = np.zeros(n, bool)
    cand &= ~fin[e] & ~interdite[e]
    if G['plages_interdites'] or G['plages_autorisees'] is not None:
        mins = ex.minutes_locales(G['fuseau_plages'])
        ok = np.ones(n, bool)
        for a, b in (G['plages_interdites'] or ()):
            ok &= ~_dans_plage(mins, _hm(a), _hm(b))
        if G['plages_autorisees'] is not None:
            aut = np.zeros(n, bool)
            for a, b in G['plages_autorisees']:
                aut |= _dans_plage(mins, _hm(a), _hm(b))
            ok &= aut
        cand &= ok[e]
    ks = np.flatnonzero(cand)

    # ---- sorties sur signal
    so = G['sortie_signal'] or {}
    xL = _evenement_any(sg.tableau(so['long'], bool), idx) if so.get('long') is not None else np.zeros(n, bool)
    xS = _evenement_any(sg.tableau(so['short'], bool), idx) if so.get('short') is not None else np.zeros(n, bool)

    # ---- paramètres
    atr_s = sg.atr
    atr_x = ex.atr if df_signal is None else np.where(np.isfinite(ex.atr), ex.atr, atr_s[np.clip(idx, 0, sg.n - 1)])
    st_cfg, ob_cfg, en_cfg = G['stop'], G['objectif'], G['entree']
    smode, omode, emode = st_cfg['mode'], ob_cfg['mode'], en_cfg['mode']
    if smode == 'niveau':
        nivS = {1: _niveaux(sg, st_cfg.get('long')), -1: _niveaux(sg, st_cfg.get('short'))}
    if omode == 'niveau':
        nivO = {1: _niveaux(sg, ob_cfg.get('long')), -1: _niveaux(sg, ob_cfg.get('short'))}
    if emode == 'limite':
        lim = {1: sg.tableau(en_cfg.get('long')) if en_cfg.get('long') is not None else None,
               -1: sg.tableau(en_cfg.get('short')) if en_cfg.get('short') is not None else None}
        valid = int(en_cfg.get('validite', 4))
    arr = G['arrondi_tick']

    def rnd(x):
        return round(x / tick) * tick if arr else x

    be = G['break_even']; tr = G['suiveur']; pa = G['partiel']
    nmax = int(G['sortie_barres'] or 0)
    maxj = int(G['max_trades_jour'] or 0)
    jours = ex.jour_cme().tolist() if maxj else None
    abandon = G['fin_donnees'] == 'abandon'

    def calc_stop(px, d, a, i):
        """-> (stop, risque, nom) ou None (sauter)."""
        if smode == 'atr':
            if not (a > 0):
                return None
            k = float(st_cfg.get('k', 2.0))
            s = rnd(px - d * k * a)
            return s, d * (px - s), 'atr%g' % k
        if smode == 'points':
            p = float(st_cfg['points'])
            s = rnd(px - d * p)
            return s, d * (px - s), 'pts%g' % p
        if smode == 'aucun':
            if not (a > 0):
                return None
            return None, float(st_cfg.get('k_ref', 1.0)) * a, 'aucun'
        if smode == 'niveau':
            marge = st_cfg.get('marge_ticks', 0) * tick + st_cfg.get('marge_atr', 0.0) * (a if a > 0 else 0.0)
            lo_, hi_ = st_cfg.get('min_atr'), st_cfg.get('max_atr')
            ok = []
            for nom, t in nivS[d]:
                v = t[i]
                if not math.isfinite(v):
                    continue
                s = rnd(v - d * marge)
                r = d * (px - s)
                if r <= 0:
                    continue
                if a > 0 and ((lo_ is not None and r < lo_ * a) or (hi_ is not None and r > hi_ * a)):
                    continue
                ok.append((s, r, 'niveau:' + nom))
            if ok:
                ch = st_cfg.get('choix', 'ordre')
                if ch == 'proche':
                    return min(ok, key=lambda x: x[1])
                if ch == 'loin':
                    return max(ok, key=lambda x: x[1])
                return ok[0]
            if st_cfg.get('sauter', False) or not (a > 0):
                return None
            k = float(st_cfg.get('repli_k', 2.0))
            s = rnd(px - d * k * a)
            return s, d * (px - s), 'repli_atr%g' % k
        raise ValueError('mode de stop inconnu : %s' % smode)

    def calc_obj(px, d, risk, i):
        """-> (objectif ou None, nom) ou False (sauter)."""
        if omode == 'aucun':
            return None, 'aucun'
        if omode == 'R':
            k = float(ob_cfg['k'])
            return rnd(px + d * k * risk), 'R%g' % k
        if omode == 'points':
            p = float(ob_cfg['points'])
            return rnd(px + d * p), 'pts%g' % p
        if omode == 'niveau':
            rmin = float(ob_cfg.get('ratio_min', 0.0))
            marge = ob_cfg.get('marge_ticks', 0) * tick
            best = None
            for nom, t in nivO[d]:
                v = t[i]
                if not math.isfinite(v):
                    continue
                o_ = rnd(v - d * marge)
                dist = d * (o_ - px)
                if dist <= 0 or dist < rmin * risk:
                    continue
                if best is None or dist < best[0]:
                    best = (dist, o_, 'niveau:' + nom)
            if best:
                return best[1], best[2]
            sa = ob_cfg.get('si_absent', 'aucun')
            if sa == 'sauter':
                return False
            if isinstance(sa, (tuple, list)) and sa[0] == 'R':
                return rnd(px + d * float(sa[1]) * risk), 'repli_R%g' % float(sa[1])
            return None, 'aucun'
        raise ValueError("mode d'objectif inconnu : %s" % omode)

    o, h, l, c = ex.o.tolist(), ex.h.tolist(), ex.l.tolist(), ex.c.tolist()
    finl, intl = fin.tolist(), interdite.tolist()
    xLl, xSl = xL.tolist(), xS.tolist()
    atrxl = atr_x.tolist()
    rows = []
    k_libre = 0
    compte = {}
    for kd in ks.tolist():
        if kd < k_libre:
            continue
        i = int(isig[kd]); d = int(sens[kd]); e0 = kd + 1
        if maxj and compte.get(jours[e0], 0) >= maxj:
            continue
        a = float(atr_s[i])
        # ---------------- entrée
        if emode == 'marche':
            f = e0; px = o[e0] + d * slip; ouv = True
            cs = calc_stop(px, d, a, i)
            if cs is None:
                continue
        else:
            lv = lim[d][i] if lim[d] is not None else float('nan')
            if not math.isfinite(lv):
                continue
            if calc_stop(lv, d, a, i) is None:
                continue
            f = -1; jlast = e0
            for j in range(e0, min(e0 + valid, n)):
                jlast = j
                if intl[j] or finl[j]:       # pas de remplissage dans la zone de sortie forcée
                    break
                if d * (o[j] - lv) <= 0:
                    f = j; px = o[j] + d * slip_lim; ouv = True; break
                if (l[j] <= lv - trav) if d == 1 else (h[j] >= lv + trav):
                    f = j; px = lv + d * slip_lim; ouv = False; break
            if f < 0:
                k_libre = jlast
                continue
            cs = calc_stop(px, d, a, i)
            if cs is None:
                k_libre = f
                continue
        st, risk, nom_s = cs
        if risk is None or not (risk > 0):
            continue
        co = calc_obj(px, d, risk, i)
        if co is False:
            if emode != 'marche':
                k_libre = f
            continue
        tg, nom_o = co
        if maxj:
            compte[jours[f]] = compte.get(jours[f], 0) + 1
        st0, tg0 = st, tg
        # ---------------- vie de la position
        best = px; worst = px
        be_ok = False; be_pend = False; nb = 0
        typ = 'stop'
        pp = rnd(px + d * float(pa['R']) * risk) if pa else None
        frac = float(pa['fraction']) if pa else 0.0
        part = 0.0; rest = 1.0; part_ok = False
        xp = None; motif = None; x = f; kind = 'intra'
        j = f
        while True:
            oj, hj, lj, cj = o[j], h[j], l[j], c[j]
            if j > f:
                if intl[j]:
                    xp = oj - d * slip; motif = 'heure'; x = j; kind = 'ouv'
                    best = max(best, oj) if d == 1 else min(best, oj)
                    worst = min(worst, oj) if d == 1 else max(worst, oj)
                    break
                if st is not None and d * (oj - st) <= 0:
                    xp = oj - d * slip; motif = typ; x = j; kind = 'ouv'
                    worst = min(worst, oj) if d == 1 else max(worst, oj)
                    break
                if pp is not None and not part_ok and d * (oj - pp) >= 0 and (tg is None or d * (pp - tg) < 0):
                    part = frac * d * (oj + 0 - px); rest = 1.0 - frac; part_ok = True
                    if pa.get('be_apres', True):
                        be_pend = True
                if tg is not None and d * (oj - tg) >= 0:
                    xp = oj; motif = 'objectif'; x = j; kind = 'ouv'
                    best = max(best, oj) if d == 1 else min(best, oj)
                    break
            adv = lj if d == 1 else hj
            fav = hj if d == 1 else lj
            tg_ok = ouv or j > f
            if st is not None and d * (adv - st) <= 0:
                xp = st - d * slip; motif = typ; x = j
                best = max(best, fav) if d == 1 else min(best, fav)
                worst = min(worst, st) if d == 1 else max(worst, st)
                break
            if tg_ok and pp is not None and not part_ok and d * (fav - pp) >= trav and (tg is None or d * (pp - tg) < 0):
                part = frac * d * (pp - d * slip_lim - px); rest = 1.0 - frac; part_ok = True
                if pa.get('be_apres', True):
                    be_pend = True
            if tg_ok and tg is not None and d * (fav - tg) >= trav:
                xp = tg - d * slip_lim; motif = 'objectif'; x = j
                best = max(best, tg) if d == 1 else min(best, tg)
                worst = min(worst, adv) if d == 1 else max(worst, adv)
                break
            best = max(best, fav) if d == 1 else min(best, fav)
            worst = min(worst, adv) if d == 1 else max(worst, adv)
            nb += 1
            if finl[j]:
                xp = cj - d * slip; motif = 'heure'; x = j; kind = 'clo'
                break
            if j + 1 >= n:
                if abandon:
                    xp = None
                else:
                    xp = cj - d * slip; motif = 'fin_donnees'; x = j; kind = 'clo'
                break
            if (xLl[j] if d == 1 else xSl[j]) or (nmax and nb >= nmax):
                motif = 'signal' if (xLl[j] if d == 1 else xSl[j]) else 'temps'
                x = j + 1; kind = 'ouv'; on = o[x]
                xp = on - d * slip
                best = max(best, on) if d == 1 else min(best, on)
                worst = min(worst, on) if d == 1 else max(worst, on)
                break
            # ---- mises à jour à la clôture (actives à la barre suivante)
            if (be and not be_ok and d * (best - px) >= float(be['R']) * risk) or (be_pend and not be_ok):
                ticks_be = float(be.get('ticks', 1)) if be else 1.0
                nv = px + d * ticks_be * tick
                if st is None or d * (nv - st) > 0:
                    st = nv; typ = 'stop_be'
                be_ok = True; be_pend = False
            if tr and d * (best - px) >= float(tr.get('activation_R', 0.0)) * risk:
                ax = atrxl[j]
                if ax == ax:
                    ref = best if tr.get('ref', 'extreme') == 'extreme' else cj
                    nv = rnd(ref - d * float(tr['k']) * ax)
                    if st is None or d * (nv - st) > 0:
                        st = nv; typ = 'stop_suiveur'
            j += 1
        if xp is None:          # abandon en fin de données
            k_libre = n
            break
        if part_ok:
            motif = 'partiel+' + motif
        pts = part + rest * d * (xp - px)
        pnl = pts * pv - 2 * comm
        risk_usd = risk * pv
        t_sortie = ex.t_ouv[x] if kind != 'clo' else ex.t_clo[x]
        rows.append((ex.t_ouv[f], t_sortie, d, px, st0 if st0 is not None else np.nan,
                     tg0 if tg0 is not None else np.nan, xp, motif, pnl / risk_usd, pnl, risk_usd,
                     min(0.0, d * (worst - px)) * pv, max(0.0, d * (best - px)) * pv,
                     x - f + (0 if kind == 'ouv' else 1), nom_s, nom_o, i, f, x))
        k_libre = x - 1 if kind == 'ouv' else x
    cols = COLONNES_TRADES + ['i_signal', 'k_entree', 'k_sortie']
    T = pd.DataFrame(rows, columns=cols)
    for k in ('entree_t', 'sortie_t'):
        T[k] = pd.to_datetime(T[k].astype(np.int64), unit='ns', utc=True).dt.tz_convert(PARIS)
    T['sens'] = np.where(T['sens'].to_numpy() == 1, 'long', 'short') if len(T) else T['sens'].astype(object)
    T['barres'] = T['barres'].astype(int)
    if not details:
        T = T[COLONNES_TRADES]
    T.attrs['instrument'] = G['instrument'] if isinstance(G['instrument'], str) else 'perso'
    return T


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Métriques
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _jour_cme_serie(t):
    t = pd.DatetimeIndex(t).tz_convert(CHICAGO).tz_localize(None)
    return (t + pd.Timedelta(hours=7)).normalize()


def metriques(trades, n_boot=2000, graine=0):
    """Résumé d'une liste de trades. IC95 du R moyen par bootstrap PAR JOUR (journée CME de sortie)."""
    T = trades
    n = len(T)
    if n == 0:
        return dict(n=0)
    T = T.sort_values('sortie_t')
    r = T['r'].to_numpy(float); p = T['pnl_usd'].to_numpy(float)
    jour = _jour_cme_serie(T['sortie_t'])
    g = pd.DataFrame({'j': jour, 'r': r, 'p': p}).groupby('j')
    sr, nr = g['r'].sum().to_numpy(), g['r'].count().to_numpy()
    rng = np.random.default_rng(graine)
    D = len(sr)
    ix = rng.integers(0, D, size=(n_boot, D))
    bm = sr[ix].sum(1) / nr[ix].sum(1)
    gains, pertes = p[p > 0].sum(), -p[p < 0].sum()
    eq = np.cumsum(p)
    pic = np.maximum.accumulate(np.r_[0.0, eq])[1:]
    sd = r.std(ddof=1) if n > 1 else np.nan
    pj = g['p'].sum()
    tous = pd.bdate_range(pj.index.min(), pj.index.max())
    pj = pj.reindex(tous.union(pj.index), fill_value=0.0)
    sh = pj.mean() / pj.std(ddof=1) * math.sqrt(252) if len(pj) > 1 and pj.std(ddof=1) > 0 else np.nan
    srt = T.sort_values('pnl_usd')
    cols = ['entree_t', 'sens', 'r', 'pnl_usd', 'motif_sortie']
    top10 = np.sort(p)[::-1][:10].sum()
    net = p.sum()
    return dict(
        n=n, pct_gagnants=float((p > 0).mean()), r_moyen=float(r.mean()),
        r_ic95=(float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))),
        pf=float(gains / pertes) if pertes > 0 else float('inf'), gain_net_usd=float(net),
        dd_max_usd=float((pic - eq).max()), t_stat=float(r.mean() / (sd / math.sqrt(n))) if sd and sd > 0 else np.nan,
        sharpe_jour=float(sh), n_jours=int(D),
        meilleurs=srt.tail(5)[cols].iloc[::-1].to_dict('records'), pires=srt.head(5)[cols].to_dict('records'),
        part_top10=float(top10 / net) if net > 0 else float('nan'),
    )


def resume(m):
    """Une ligne lisible."""
    if not m.get('n'):
        return 'n=0'
    return ('n=%d  gagnants %.0f %%  R moyen %+.3f [%+.3f ; %+.3f]  PF %.2f  net %+.0f $  DD %.0f $  t %.2f  '
            'Sharpe %.2f  top10 %.0f %%' % (m['n'], 100 * m['pct_gagnants'], m['r_moyen'], *m['r_ic95'], m['pf'],
                                           m['gain_net_usd'], m['dd_max_usd'], m['t_stat'], m['sharpe_jour'],
                                           100 * m['part_top10'] if m['part_top10'] == m['part_top10'] else float('nan')))


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Référence « entrées au hasard, même gestion »
# ════════════════════════════════════════════════════════════════════════════════════════════════
def reference_hasard(df, n=200, gestion=None, graine=0, long=None, short=None, df_signal=None, n_signaux=None,
                     garder_trades=False):
    """n tirages d'entrées aléatoires avec la MÊME gestion. Chaque signal réel (long/short) est remplacé par une
    barre signal tirée au hasard ayant la même HEURE (Paris) et le même sens, parmi les barres où une entrée
    est possible (mêmes heures autorisées) -> même fréquence, même profil horaire.
    Sans long/short : n_signaux barres au hasard, sens 50/50.
    Renvoie un DataFrame (une ligne par tirage : n, r_moyen, pf, gain_net_usd, pct_gagnants, dd_max_usd) ;
    garder_trades=True -> (DataFrame, liste des trades)."""
    ex = barres(df)
    sg = ex if df_signal is None else barres(df_signal)
    G = _gestion(gestion)
    # barres signal où une entrée est possible : on lance le moteur avec « tout est signal »
    tout = np.ones(sg.n, bool)
    idx = projection(ex, sg)
    ev = _evenement(tout, idx)
    retard = G['retard_max_min']; retard = 0.5 * ex.ut if retard is None else retard
    e = np.minimum(np.arange(ex.n) + 1, ex.n - 1)
    ok_k = (ev >= 0) & ((ex.t_ouv[e] - sg.t_clo[np.clip(ev, 0, sg.n - 1)]) <= retard * NS_MIN)
    ok_k[-1] = False
    if G['heure_sortie']:
        fin, interdite = ex.drapeaux_heure(G['heure_sortie'], G['heure_reprise'], G['fuseau_sortie'])
        ok_k &= ~fin[e] & ~interdite[e]
    if G['plages_interdites'] or G['plages_autorisees'] is not None:
        mins = ex.minutes_locales(G['fuseau_plages'])
        ok = np.ones(ex.n, bool)
        for a, b in (G['plages_interdites'] or ()):
            ok &= ~_dans_plage(mins, _hm(a), _hm(b))
        if G['plages_autorisees'] is not None:
            aut = np.zeros(ex.n, bool)
            for a, b in G['plages_autorisees']:
                aut |= _dans_plage(mins, _hm(a), _hm(b))
            ok &= aut
        ok_k &= ok[e]
    elig = np.zeros(sg.n, bool)
    elig[ev[ok_k]] = True
    if G['stop']['mode'] in ('atr', 'aucun') or G['stop']['mode'] == 'niveau':
        elig &= np.isfinite(sg.atr) & (sg.atr > 0)
    heure = _dti(sg.t_clo).tz_convert(PARIS).hour.to_numpy()
    rng = np.random.default_rng(graine)
    if long is not None or short is not None:
        Ls = sg.tableau(long, bool) if long is not None else np.zeros(sg.n, bool)
        Ss = sg.tableau(short, bool) if short is not None else np.zeros(sg.n, bool)
        reels = [(hh, 1) for hh in heure[Ls & elig]] + [(hh, -1) for hh in heure[Ss & elig & ~Ls]]
    else:
        if not n_signaux:
            raise ValueError('donner long/short ou n_signaux')
        reels = [(None, int(rng.choice([1, -1]))) for _ in range(int(n_signaux))]
    pools = {hh: np.flatnonzero(elig & (heure == hh)) for hh in range(24)}
    tous = np.flatnonzero(elig)
    out, trs = [], []
    for _ in range(n):
        Lr = np.zeros(sg.n, bool); Sr = np.zeros(sg.n, bool)
        for hh, d in reels:
            pool = pools.get(hh) if hh is not None else tous
            if pool is None or len(pool) == 0:
                pool = tous
            b = pool[rng.integers(len(pool))]
            if d == 1 and not Sr[b]:
                Lr[b] = True
            elif d == -1 and not Lr[b]:
                Sr[b] = True
        T = backtest(ex, Lr, Sr, G, df_signal=None if df_signal is None else sg)
        m = metriques(T, n_boot=1) if len(T) else dict(n=0)
        out.append(dict(n=m['n'], r_moyen=m.get('r_moyen', np.nan), pf=m.get('pf', np.nan),
                        gain_net_usd=m.get('gain_net_usd', 0.0), pct_gagnants=m.get('pct_gagnants', np.nan),
                        dd_max_usd=m.get('dd_max_usd', 0.0)))
        if garder_trades:
            trs.append(T)
    R = pd.DataFrame(out)
    return (R, trs) if garder_trades else R


def p_hasard(ref, valeur, col='r_moyen'):
    """Part des tirages au hasard au moins aussi bons que la recette (p-valeur unilatérale, +1 lissage)."""
    v = ref[col].dropna().to_numpy()
    return float((1 + (v >= valeur).sum()) / (1 + len(v)))


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Découpage développement / scellé, walk-forward
# ════════════════════════════════════════════════════════════════════════════════════════════════
PART_DEV = 0.75
JOURNAL_SCELLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'registre', 'ouvertures_scelle.log')


def date_coupure(df, part_dev=PART_DEV):
    """Début (ns UTC) de la 1re journée CME du scellé : coupure à la frontière de journée qui suit 75 % des barres."""
    b = barres(df)
    j = b.jour_cme()
    k = int(math.floor(part_dev * b.n))
    k = min(max(k, 1), b.n - 1)
    jc = j[k]
    k0 = int(np.searchsorted(j, jc, side='left'))
    return int(b.t_ouv[k0])


def decoupage(df, part_dev=PART_DEV, coupure=None):
    """(developpement, scelle) coupés chronologiquement (75 % / 25 % des barres, à une frontière de journée CME).
    coupure : instant (ns UTC, Timestamp ou chaîne) à imposer (ex. coupure du cadre d'exécution en multi-UT)."""
    b = barres(df)
    if coupure is None:
        cut = date_coupure(df, part_dev)
    else:
        cut = pd.Timestamp(coupure)
        cut = (cut.tz_localize(PARIS) if cut.tz is None else cut).value if not isinstance(coupure, (int, np.integer)) else int(coupure)
    m = b.t_ouv < cut
    return df[m], df[~m]


def charger_recherche(source, ouvrir_scelle=False, part_dev=PART_DEV, coupure=None, agent='?', **kw):
    """Chargement POUR LA RECHERCHE : ne renvoie que la partie développement.
    source : DataFrame, ou callable (ex. dataset.charger.charger) appelé avec **kw.
    ouvrir_scelle=True (réservé à l'avocat du diable, vague 2) -> (developpement, scelle), et l'ouverture est
    journalisée dans registre/ouvertures_scelle.log."""
    df = source(**kw) if callable(source) else source
    dev, sce = decoupage(df, part_dev, coupure)
    if not ouvrir_scelle:
        return dev
    try:
        with open(JOURNAL_SCELLE, 'a') as fh:
            fh.write('%s\t%s\t%d barres scellées\n' % (pd.Timestamp.now(tz=PARIS).isoformat(), agent, len(sce)))
    except OSError:
        pass
    return dev, sce


def walk_forward(df, k=5, ratio=3, ancre=False):
    """k plis glissants : le développement est coupé en (ratio + k) blocs de journées CME consécutives ;
    pli p : apprentissage = blocs [p, p + ratio) (ou [0, p + ratio) si ancre), test = bloc p + ratio.
    Renvoie [(df_apprentissage, df_test), ...]."""
    b = barres(df)
    j = b.jour_cme()
    uj = np.unique(j)
    nb = ratio + k
    bornes = np.linspace(0, len(uj), nb + 1).round().astype(int)
    blocs = [uj[bornes[q]:bornes[q + 1]] for q in range(nb)]
    out = []
    for p in range(k):
        a0 = 0 if ancre else p
        app = np.concatenate(blocs[a0:p + ratio])
        tst = blocs[p + ratio]
        out.append((df[np.isin(j, app)], df[np.isin(j, tst)]))
    return out
