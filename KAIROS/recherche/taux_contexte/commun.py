"""Briques communes de l'agent « Taux — contexte et horaires » (WRR).

- `charger_series(source)` : SEUL accès aux données (réutilise meta_ml/donnees.py : cache ou DATASET,
  développement seulement, scellé fermé). Passage au DATASET : `--source dataset`.
- `preparer(serie)` : signaux (union des déclencheurs de meta_ml/candidats.py), contextes à la clôture de la
  barre signal (briques de regimes/etats.py calculées sur les prix CAUSAUX + contextes ajoutés ici).
- `gestion`, `backtest_masque`, `placebo` : moteur commun ; placebo = entrées au hasard de même heure
  d'ouverture (Paris), même sens, DANS LE MÊME CONTEXTE, même gestion.
- `simuler` : simulateur Tradeify Select Flex (optimise_taille + analyse_reference).

Toutes les grandeurs de contexte sont connues à la clôture de la barre signal (aucune donnée future) :
prix causaux (colonnes *_causal du cache ; vrais prix du DATASET), multi-UT déjà clôturés, niveaux
(Monday, pivots weekly, jour précédent, session précédente) issus de périodes TERMINÉES.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
for p in (os.path.join(SB, 'moteur'), os.path.join(SB, 'propfirm'), os.path.join(SB, 'dataset'),
          os.path.join(SB, 'recherche', 'regimes'), os.path.join(SB, 'recherche', 'meta_ml')):
    if p not in sys.path:
        sys.path.insert(0, p)
import moteur as M  # noqa: E402

NS_MIN = 60_000_000_000
REGLE = 'tradeify_50k_select_flex'


# ════════════════════════════════════════════════════════════════════════════
# POINT D'ACCÈS UNIQUE AUX DONNÉES
# ════════════════════════════════════════════════════════════════════════════
def charger_series(source=None):
    """-> [dict(nom, instrument, df)] ; df = DÉVELOPPEMENT seulement (moteur.charger_recherche)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('donnees_meta_ml', os.path.join(SB, 'recherche', 'meta_ml', 'donnees.py'))
    DMM = importlib.util.module_from_spec(spec); spec.loader.exec_module(DMM)      # meta_ml/donnees.py
    return DMM.charger_series(source or os.environ.get('WRR_SOURCE', 'cache'))


# ════════════════════════════════════════════════════════════════════════════
# Contextes
# ════════════════════════════════════════════════════════════════════════════
def _causal(df):
    """Copie de df où o/h/l/c/atr sont les prix CAUSAUX (si présents) : sert aux contextes seulement."""
    d = df.copy()
    for k in ('o', 'h', 'l', 'c', 'atr'):
        if k + '_causal' in d.columns:
            d[k] = d[k + '_causal']
    for k in ('feu_l', 'feu_s'):
        if k not in d.columns:
            d[k] = np.nan
    for k in ('trend_60', 'trend_240', 'hei_60'):
        if 'ok_' + k not in d.columns:
            d['ok_' + k] = d[k].notna() if k in d.columns else False
        d[k] = d[k].fillna(0).astype(bool) if k in d.columns else False
    return d


def _jour_cme(idx):
    t = idx.tz_convert('America/Chicago').tz_localize(None)
    return (t + pd.Timedelta(hours=7)).normalize()


def _niveaux_periode(cle, h, l, c):
    """H/L/C de la période PRÉCÉDENTE (terminée) pour chaque barre, cle = identifiant de période croissant."""
    s = pd.DataFrame(dict(k=cle, h=h, l=l, c=c))
    g = s.groupby('k', sort=True).agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last'))
    prev = g.shift(1)
    return (prev['h'].reindex(cle).to_numpy(), prev['l'].reindex(cle).to_numpy(), prev['c'].reindex(cle).to_numpy())


def _session_precedente(heure, jour, h, l):
    """H/L de la dernière session TERMINÉE (nuit 0-8 h, Londres 8-14 h 30, US 14 h 30-24 h, heure de Paris)."""
    ses = np.where(heure < 8, 0, np.where(heure < 14.5, 1, 2))
    cle = np.zeros(len(h), np.int64)
    k = 0
    for i in range(1, len(h)):
        if ses[i] != ses[i - 1] or jour[i] != jour[i - 1]:
            k += 1
        cle[i] = k
    H, L, _ = _niveaux_periode(cle, h, l, l)
    return H, L


def contextes(df):
    """DataFrame (index = barres) des contextes NON orientés + niveaux, à la clôture de chaque barre."""
    import etats as ET          # regimes/etats.py
    d = ET.briques(_causal(df))
    par = df.index.tz_convert('Europe/Paris')
    heure = par.hour + par.minute / 60          # heure d'OUVERTURE de la barre signal (comme le filtre Pine)
    out = pd.DataFrame(index=df.index)
    out['heure'] = heure
    out['h_int'] = par.hour
    out['seance'] = np.where(heure < 8, 0, np.where(heure < 14.5, 1, 2))     # nuit / Londres / US
    out['tendance'] = d['tendance'].to_numpy()
    out['aligne'] = d['aligne'].to_numpy()
    out['vol'] = d['vol'].to_numpy()
    out['adx20'] = (d['adx'].to_numpy() >= 20).astype(int)
    out['jour'] = d['jour'].to_numpy()
    out['pos_orb'] = d['pos_orb'].to_numpy()
    c, h, l = d['c'].to_numpy(float), d['h'].to_numpy(float), d['l'].to_numpy(float)
    mh, ml = d['mon_h_r'].to_numpy(), d['mon_l_r'].to_numpy()
    out['pos_mon'] = np.where(np.isnan(mh), 9, d['pos_mon'].to_numpy())           # 9 = niveaux pas prêts
    jc = _jour_cme(df.index)
    jn = np.asarray((jc - pd.Timestamp('1970-01-01')).days, np.int64)
    # jour précédent (journée CME terminée)
    pdh, pdl, _ = _niveaux_periode(jn, h, l, c)
    out['pos_pdj'] = np.where(np.isnan(pdh), 9, np.where(c > pdh, 1, np.where(c < pdl, -1, 0)))
    # pivot weekly classique (semaine CME précédente)
    sem = pd.DatetimeIndex(jc).to_period('W-FRI').asi8
    wh, wl, wc = _niveaux_periode(sem, h, l, c)
    P = (wh + wl + wc) / 3
    out['pos_pivw'] = np.where(np.isnan(P), 9, np.where(c > P, 1, -1))
    # session précédente terminée
    sh, sl = _session_precedente(np.asarray(heure), jn, h, l)
    out['pos_ses'] = np.where(np.isnan(sh), 9, np.where(c > sh, 1, np.where(c < sl, -1, 0)))
    # dernier climax : sens et âge (barres)
    cb = df['clx_buy'].fillna(False).to_numpy(bool) if 'clx_buy' in df else np.zeros(len(df), bool)
    cs = df['clx_sell'].fillna(False).to_numpy(bool) if 'clx_sell' in df else np.zeros(len(df), bool)
    dern = np.zeros(len(df), int); age = np.full(len(df), 10 ** 6)
    cur, a = 0, 10 ** 6
    for i in range(len(df)):
        if cb[i] and not cs[i]:
            cur, a = 1, 0
        elif cs[i] and not cb[i]:
            cur, a = -1, 0
        else:
            a += 1
        dern[i], age[i] = cur, a
    out['clx_dern'] = dern
    out['clx_age'] = age
    out['mois'] = par.strftime('%Y-%m')
    out['jour_cme'] = jn
    return out


# Partitions : nom -> (fonction(ctx, sens) -> codes entiers, libellés). sens = +1 long / -1 short.
# Seuils FIXÉS À L'AVANCE (ceux de regimes/etats.py ; climax « récent » = 16 barres = 4 h en 15 min).
def _o(col):
    """Partition orientée : +1 « dans le sens du trade », -1 « contre », 0 neutre/dedans, 9 = inconnu."""
    return lambda X, s: np.where(X[col].to_numpy() == 9, 9, X[col].to_numpy() * s)


PARTITIONS = {
    'seance': (lambda X, s: X['seance'].to_numpy(), {0: 'nuit 0-8h', 1: 'Londres 8-14h30', 2: 'US 14h30-23h'}),
    'tendance': (_o('tendance'), {1: 'tendance dans le sens', 0: 'range (ADX<20 ou pente/EMA mixtes)',
                                  -1: 'tendance contre'}),
    'aligne': (_o('aligne'), {1: 'TREND 15/60/240 alignés dans le sens', 0: 'TREND non alignés',
                              -1: 'TREND alignés contre'}),
    'vol': (lambda X, s: X['vol'].to_numpy(), {0: 'volatilité basse', 1: 'volatilité moyenne', 2: 'volatilité haute'}),
    'adx': (lambda X, s: X['adx20'].to_numpy(), {1: 'ADX >= 20', 0: 'ADX < 20'}),
    'jour': (lambda X, s: X['jour'].to_numpy(), {0: 'lundi', 1: 'mardi', 2: 'mercredi', 3: 'jeudi', 4: 'vendredi'}),
    'monday': (_o('pos_mon'), {1: 'au-delà du Monday H/L dans le sens', 0: 'dans le Monday range',
                               -1: 'au-delà du Monday H/L contre'}),
    'pivot_w': (_o('pos_pivw'), {1: 'du bon côté du pivot weekly', -1: 'du mauvais côté du pivot weekly'}),
    'jour_prec': (_o('pos_pdj'), {1: 'au-delà du PDH/PDL dans le sens', 0: 'dans le range de la veille',
                                  -1: 'au-delà du PDH/PDL contre'}),
    'session_prec': (_o('pos_ses'), {1: 'au-delà de la session précédente dans le sens',
                                     0: 'dans la session précédente', -1: 'au-delà de la session précédente contre'}),
    'orb': (_o('pos_orb'), {1: 'au-delà de l\'ORB dans le sens', 0: 'dans l\'ORB / ORB pas formé',
                            -1: 'au-delà de l\'ORB contre'}),
    'climax': (lambda X, s: np.where(X['clx_dern'].to_numpy() == 0, 9,
                                     np.where(X['clx_dern'].to_numpy() == s,
                                              np.where(X['clx_age'].to_numpy() <= 16, 2, 1), -1)),
               {2: 'dernier climax dans le sens, <= 16 barres', 1: 'dernier climax dans le sens, > 16 barres',
                -1: 'dernier climax contre'}),
}


def masque(X, partition, etat, s):
    f, _ = PARTITIONS[partition]
    return np.asarray(f(X, s)) == etat


# ════════════════════════════════════════════════════════════════════════════
# Signaux, gestion, moteur
# ════════════════════════════════════════════════════════════════════════════
def preparer(serie):
    import candidats as CD      # meta_ml/candidats.py
    df = serie['df']
    D = CD.declencheurs(df)
    L = np.zeros(len(df), bool); S = np.zeros(len(df), bool)
    for a, b in D.values():
        L |= a; S |= b
    L[:150] = False; S[:150] = False
    X = contextes(df)
    px = df[['o', 'h', 'l', 'c', 'atr']]
    return dict(nom=serie['nom'], instrument=serie['instrument'], df=df, px=px, B=M.barres(px), L=L, S=S, X=X)


GEOMETRIES = {
    'A15R2': (1.5, 2.0), 'A15R1': (1.5, 1.0), 'A15R075': (1.5, 0.75), 'A15R05': (1.5, 0.5),
}


def gestion(geom, instrument):
    k, r = GEOMETRIES[geom]
    return dict(instrument=instrument, stop={'mode': 'atr', 'k': k}, objectif={'mode': 'R', 'k': r},
                heure_sortie='15:59')


def entrees_possibles(P, G):
    """Barres signal où le moteur peut entrer (même logique que moteur.reference_hasard)."""
    cle = ('poss', G['heure_sortie'])
    if cle in P:
        return P[cle]
    ex = P['B']
    G = M._gestion(G)
    e = np.minimum(np.arange(ex.n) + 1, ex.n - 1)
    ok = (ex.t_ouv[e] - ex.t_clo) <= 0.5 * ex.ut * NS_MIN
    ok[-1] = False
    fin, interdite = ex.drapeaux_heure(G['heure_sortie'], G['heure_reprise'], G['fuseau_sortie'])
    ok &= ~fin[e] & ~interdite[e]
    ok &= np.isfinite(ex.atr) & (ex.atr > 0)
    P[cle] = ok
    return ok


def backtest_masque(P, G, mL, mS):
    """Trades du moteur (une position à la fois) avec les signaux de P masqués par mL / mS."""
    T = M.backtest(P['B'], P['L'] & mL, P['S'] & mS, G)
    T['serie'] = P['nom']; T['instrument'] = P['instrument']
    return T


def placebo(P, G, mL, mS, n, graine):
    """n tirages : chaque signal réel (après masque) est remplacé par une barre au hasard de la MÊME heure
    d'ouverture (Paris), du MÊME sens, où le contexte est le même (mL / mS) et où une entrée est possible."""
    poss = entrees_possibles(P, G)
    h = P['X']['h_int'].to_numpy()
    rng = np.random.default_rng(graine)
    Lr, Sr = P['L'] & mL & poss, P['S'] & mS & poss
    reels = [(1, hh) for hh in h[Lr]] + [(-1, hh) for hh in h[Sr & ~Lr]]
    elig = {1: poss & mL, -1: poss & mS}
    pools = {}
    for d, hh in set(reels):
        p = np.flatnonzero(elig[d] & (h == hh))
        pools[(d, hh)] = p if len(p) else np.flatnonzero(elig[d])
    out = []
    nb = P['B'].n
    for _ in range(n):
        Lx = np.zeros(nb, bool); Sx = np.zeros(nb, bool)
        for d, hh in reels:
            pool = pools[(d, hh)]
            if not len(pool):
                continue
            b = pool[rng.integers(len(pool))]
            if d == 1 and not Sx[b]:
                Lx[b] = True
            elif d == -1 and not Lx[b]:
                Sx[b] = True
        T = M.backtest(P['B'], Lx, Sx, G)
        T['serie'] = P['nom']; T['instrument'] = P['instrument']
        out.append(T)
    return out


def jour_cme_trades(T):
    return np.asarray((_jour_cme(pd.DatetimeIndex(T['entree_t'])) - pd.Timestamp('1970-01-01')).days, np.int64) if len(T) else np.array([], int)


def compact(T, tirage=0):
    """Résumé léger d'une liste de trades : tirage, jour CME (entrée), mois, r, gagnant (pnl > 0)."""
    if not len(T):
        return pd.DataFrame(dict(tirage=[], jour=[], mois=[], r=[], g=[]))
    return pd.DataFrame(dict(tirage=np.full(len(T), tirage, np.int32), jour=jour_cme_trades(T).astype(np.int32),
                             mois=pd.DatetimeIndex(T['entree_t']).tz_convert('Europe/Paris').strftime('%Y%m').astype(np.int32),
                             r=T['r'].to_numpy(np.float32), g=(T['pnl_usd'].to_numpy() > 0)))


# ════════════════════════════════════════════════════════════════════════════
# Simulateur propfirm
# ════════════════════════════════════════════════════════════════════════════
def pour_simulateur(T):
    """Rapproche la période MES1 (avr.-juil.) de la période sept.-oct. par un décalage d'un nombre ENTIER de
    semaines (jours de semaine conservés) pour que le simulateur ne compte pas ~50 journées vides entre les
    deux périodes. Ne change ni l'ordre ni le contenu des trades."""
    T = T.copy()
    if not len(T) or 'serie' not in T:
        return T
    m1 = T['serie'].astype(str).str.startswith('MES1')
    if m1.any() and (~m1).any():
        fin1 = pd.Timestamp(T.loc[m1, 'sortie_t'].max())
        deb2 = pd.Timestamp(T.loc[~m1, 'entree_t'].min())
        sem = int((deb2 - fin1).days // 7)
        if sem > 0:
            dt = pd.Timedelta(weeks=sem)
            T.loc[m1, 'entree_t'] = pd.DatetimeIndex(T.loc[m1, 'entree_t']) + dt
            T.loc[m1, 'sortie_t'] = pd.DatetimeIndex(T.loc[m1, 'sortie_t']) + dt
    return T.sort_values('entree_t').reset_index(drop=True)


def simuler(trades, refs, n_sim=1000, tailles=(1, 2, 3, 5, 8, 12)):
    import simulateur as SIM
    regles = SIM.charge_regles()[REGLE]
    tr = pour_simulateur(trades)
    if not len(tr):
        return {}
    _, best = SIM.optimise_taille(tr, regles, list(tailles), n_sim=n_sim, ordre='prudent', bloc_jours=5)
    c = int(best['contrats'])
    ref = SIM.analyse_reference([pour_simulateur(t) for t in refs[:30] if len(t)], regles, c, n_sim=n_sim,
                                ordre='prudent', bloc_jours=5) if refs else {}
    return dict(contrats=c, p_reussite=best.get('p_reussite'), p_1er_payout=best.get('p_1er_payout'),
                ve_usd=best.get('valeur_esperee_usd'), ref_p_reussite=ref.get('p_reussite'),
                ref_p_1er_payout=ref.get('p_1er_payout'), ref_ve_usd=ref.get('valeur_esperee_usd'))
