"""Optimiseur final (FIN) : biais global + déclencheurs + confirmations, et les gestions de STRATEGIE_V1.pine
(objectifs sur niveaux, sortie partielle, break-even, Heishinator, sortie après N bougies).

    ~/venv-quant/bin/python final.py --source cache      # essai à blanc (2 mois)
    ~/venv-quant/bin/python final.py --source dataset    # dès que les exports DATASET 15 min existent
    options : --registre (écrit les 3 lignes FIN), --recalcul (ignore le cache disque), --petit (essai rapide)

TOUT EST FIXÉ À L'AVANCE (avant de regarder un résultat) :
  ENTRÉES (52) : biais (bF, bI) parmi 4 crans {(.33,.2) (.55,.2) (.55,.45) (.78,.45)} x déclencheurs
      {Signator Fort+Moyen ; union} x confirmation {aucune ; Detector 1,5 ; Detector+climax ; Detector+Feu 60 ;
      Detector+TREND 4 h ; Detector+ADX 25} = 48, plus le préréglage 25 tel quel (15:30-22:15) et le préréglage 25
      filtré par le biais (.33,.2) = 50 candidates. Fenêtre 00:20-22:15 Paris (sauf préréglage 25), à plat avant
      15:59 Chicago aussi.
      + 12 entrées de RÉFÉRENCE sans biais (même déclencheur, même confirmation) : jamais choisies, servent à
      mesurer ce que le biais apporte.
  SORTIES (39 formes x stop 1,5 / 2 / 2,5 ATR = 117) :
      R fixe 1 / 1,5 / 2 ; 2 R + break-even à 1 R (+4 ticks) ; sortie après 8 / 12 bougies (1R-8 = préréglage 25,
      1,5R-8, 1,5R-12, 2R-8, 2R-12) ; « prochain niveau » (rrMin 1 / 1,5) x familles {pivots A+M+W ; pivots +
      zone Detector ; + Monday + sessions} x {sans partiel ; sans partiel + Heishinator ; partiel 50 % + reste au
      2e niveau ; idem + Heishinator ; partiel 50 % + reste en « Stop seulement » + Heishinator}. Stop après le
      partiel = prix d'entrée + 4 ticks. Repli sans niveau offrant le ratio = objectif 1,5 R (tpSans).
  = 50 x 117 = 5 850 variantes candidates (+ 1 404 références sans biais).
RÈGLE DE CHOIX : éligible = >= 1 trade/jour, >= 55 % de gagnants, R moyen > 0, n >= N_MIN ; score = moyenne de la
  valeur espérée Tradeify (Select Flex) de la variante ET de ses voisines à un pas (confirmation, biais,
  déclencheur ; stop ; forme de sortie voisine dans l'ordre de la liste) ; repli de palier si personne
  (d'abord sans le >= 1/jour, puis sans le 55 %). RECOMMANDÉE = meilleur score.
  Profils alternatifs (au plus 2, DIFFÉRENTS de la recommandée et entre eux) :
   - « plus de trades » : parmi les éligibles de classe/entrée différente, tpd >= 1,3 x recommandée et score >= 50 % ;
   - « plus de R »      : idem avec R moyen >= R recommandée + 0,10 ; meilleur score. S'il n'y en a aucune : meilleure
                          gestion « niveaux + partiel » (>= 1 trade/jour, R > 0, SANS exigence de 55 %), signalée comme telle
                          (ajout du 17/10 après l'essai sur le cache : aucune gestion sur niveaux n'atteint 55 % de gagnants).
  « Différent » = classe de sortie différente (R fixe / niveau / niveau + partiel) OU entrée éloignée (>= 3 crans).
Walk-forward (3 blocs d'apprentissage -> bloc suivant, 4 plis) + bootstrap de White sur toutes les variantes.
Placebo = entrées AU HASARD de même heure et même sens, dans le sens du biais (espérance exacte de la table
d'issues), avec EXACTEMENT la même gestion.
"""
from __future__ import annotations

import argparse
import itertools
import multiprocessing as mp
import os
import pickle
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')
ICI = os.path.dirname(os.path.abspath(__file__))
REC = os.path.abspath(os.path.join(ICI, '..'))
sys.path[:0] = [ICI, os.path.join(REC, 'biais'), os.path.join(REC, 'optim25'), os.path.join(REC, 'sorties')]
_src = 'cache'
for _i, _a in enumerate(sys.argv):
    if _a == '--source' and _i + 1 < len(sys.argv):
        _src = sys.argv[_i + 1]
os.environ['SOR_SOURCE'] = _src          # donnees_sor lit sa source à l'import

import optimiser as O  # noqa: E402
import votes as VT  # noqa: E402
import donnees_sor as DN  # noqa: E402
import sim_fin as SF  # noqa: E402

B, D, TB, AN, SIM, RG, M = O.B, O.D, O.TB, O.AN, O.SIM, O.RG, O.M
SORTIES = os.path.join(ICI, 'sorties')
os.makedirs(SORTIES, exist_ok=True)
NPROC = O.NPROC
UT = 15
EPS = 1e-9
FEN_DEBUT, FEN_FIN = O.FEN_DEBUT, O.FEN_FIN
GAGNANTS_MIN, TPD_MIN, DETK = 0.55, 1.0, 1.5
TAILLES_MC, TAILLES_PART = [1, 2, 3, 4, 6, 8, 10], [2, 4, 6, 8, 10]
TAILLES_WF = [1, 2, 4, 6]
N_SIM_MC, N_SIM_WF = 300, 120
K_PLIS, RATIO = 4, 3
BE_TICKS = 4


def n_min(source):
    return 80 if source == 'dataset' else 30


# ═════════════════════════════ BALAYAGE ═════════════════════════════
BIAS = [(0.33, 0.2), (0.55, 0.2), (0.55, 0.45), (0.78, 0.45)]
TRIGS = ['sig', 'union']
QUALS = ['aucune', 'det', 'det+clx', 'det+feu', 'det+trend4h', 'det+adx']
STOPS = [1.5, 2.0, 2.5]


def _formes():
    F = [('R1', dict(tp='R', R=1.0)), ('R1.5', dict(tp='R', R=1.5)), ('R2', dict(tp='R', R=2.0)),
         ('R2+BE1', dict(tp='R', R=2.0, be=1.0)),
         ('R1+N8', dict(tp='R', R=1.0, tBar=8)), ('R1.5+N8', dict(tp='R', R=1.5, tBar=8)),
         ('R1.5+N12', dict(tp='R', R=1.5, tBar=12)), ('R2+N8', dict(tp='R', R=2.0, tBar=8)),
         ('R2+N12', dict(tp='R', R=2.0, tBar=12))]
    for rr in (1.0, 1.5):
        for fam, fnom in (('piv', 'pivots'), ('pivdet', 'pivots+Detector'), ('tous', 'pivots+Detector+Monday+sessions')):
            for part, hei in ((0, 0), (0, 1), (1, 0), (1, 1), (2, 1)):
                nom = 'niv%g %s %s%s' % (rr, fnom, {0: 'sans partiel', 1: 'partiel->2e niveau', 2: 'partiel->reste Heishinator'}[part],
                                         ' +Hei' if hei and part != 2 else '')
                F.append((nom, dict(tp='niv', rr=rr, fam=fam, part=part, hei=hei)))
    return F


FORMES = _formes()
GEOMS = [(k, i) for k in STOPS for i in range(len(FORMES))]          # (stop, indice de forme)


def geom_dict(gk):
    k, fi = gk
    return SF.gestion_defaut(k=k, be_ticks=BE_TICKS, **FORMES[fi][1])


def classe_sortie(gk):
    f = FORMES[gk[1]][1]
    if f['tp'] == 'R':
        return 'R fixe'
    return 'niveau + partiel' if f['part'] else 'niveau'


def entrees():
    E = []
    for bi, tg, q in itertools.product(range(len(BIAS)), TRIGS, QUALS):
        E.append(dict(fam='B', bi=bi, trig=tg, qual=q, cand=True))
    E.append(dict(fam='P', bi=None, trig='p25', qual='p25', cand=True))
    E.append(dict(fam='P', bi=0, trig='p25', qual='p25', cand=True))
    for tg, q in itertools.product(TRIGS, QUALS):
        E.append(dict(fam='R', bi=None, trig=tg, qual=q, cand=False))
    return E


ENTREES = entrees()
IDX_E = {(e['fam'], e['bi'], e['trig'], e['qual']): i for i, e in enumerate(ENTREES)}


def libelle_entree(e):
    if e['fam'] == 'P':
        return 'préréglage 25%s' % (' + biais F>=%g I>=%g' % BIAS[e['bi']] if e['bi'] is not None else '')
    tg = 'Signator F+M' if e['trig'] == 'sig' else 'union'
    q = {'aucune': 'sans confirmation', 'det': 'Detector 1,5', 'det+clx': 'Detector+climax', 'det+feu': 'Detector+Feu 60',
         'det+trend4h': 'Detector+TREND 4 h', 'det+adx': 'Detector+ADX 25'}[e['qual']]
    b = 'sans biais' if e['bi'] is None else 'biais F>=%g I>=%g' % BIAS[e['bi']]
    return '%s | %s | %s' % (b, tg, q)


def libelle(v):
    ei, gi = v
    return '%s | stop %g ATR | %s' % (libelle_entree(ENTREES[ei]), GEOMS[gi][0], FORMES[GEOMS[gi][1]][0])


def voisines(v):
    """Voisines à un pas : une entrée voisine (même sortie) ou une sortie voisine (même entrée)."""
    ei, gi = v
    e = ENTREES[ei]; out = []
    if e['fam'] == 'B':
        for dbi in (-1, 1):
            b = e['bi'] + dbi
            if 0 <= b < len(BIAS):
                out.append((IDX_E[('B', b, e['trig'], e['qual'])], gi))
        out.append((IDX_E[('B', e['bi'], 'sig' if e['trig'] == 'union' else 'union', e['qual'])], gi))
        k = QUALS.index(e['qual'])
        for q in (k - 1, k + 1):
            if 0 <= q < len(QUALS):
                out.append((IDX_E[('B', e['bi'], e['trig'], QUALS[q])], gi))
    elif e['fam'] == 'P':
        out.append((IDX_E[('P', 0 if e['bi'] is None else None, 'p25', 'p25')], gi))
    k, fi = GEOMS[gi]
    for dk in (-1, 1):
        q = STOPS.index(k) + dk
        if 0 <= q < len(STOPS):
            out.append((ei, GEOMS.index((STOPS[q], fi))))
    for df_ in (-1, 1):
        q = fi + df_
        if 0 <= q < len(FORMES):
            out.append((ei, GEOMS.index((k, q))))
    return out


def distance_entree(e1, e2):
    if e1['fam'] != e2['fam']:
        return 9
    if e1['fam'] == 'P':
        return abs((e1['bi'] is not None) - (e2['bi'] is not None))
    return abs(e1['bi'] - e2['bi']) + (e1['trig'] != e2['trig']) + abs(QUALS.index(e1['qual']) - QUALS.index(e2['qual']))


def different(v1, v2):
    return (classe_sortie(GEOMS[v1[1]]) != classe_sortie(GEOMS[v2[1]])
            or distance_entree(ENTREES[v1[0]], ENTREES[v2[0]]) >= 3)


# ═════════════════════════════ DONNÉES (UN SEUL ENDROIT) ═════════════════════════════
def charger(source):
    """Jeux 15 min (développement seulement, scellé fermé) + niveaux de marché alignés. Seul accès aux données."""
    jeux = D.charger_jeux(source, uts=(UT,))
    sor = DN.charger_series(UT)
    for j in jeux:
        df = j['df']
        cible = None; meilleur = 0.0
        for s in sor:
            if s['instrument'] != j['instrument']:
                continue
            part = df.index.isin(s['df'].index).mean()
            if part > meilleur:
                cible, meilleur = s, part
        j['niv'] = None if (cible is None or meilleur < 0.9) else cible['df'].reindex(df.index)
        j['niv_couv'] = meilleur
    return jeux


def _mat(nv, fam_reel, fam_ha):
    """Matrice des niveaux d'une famille (prix réels si présents, sinon Heiken Ashi), (n, m)."""
    def cols(f):
        return [c for c in nv.columns if c.startswith('lv_%s_' % f)]
    a, b = cols(fam_reel), cols(fam_ha)
    ma = nv[a].to_numpy(float) if a else np.full((len(nv), 0), np.nan)
    mb = nv[b].to_numpy(float) if b else np.full((len(nv), 0), np.nan)
    return ma if np.isfinite(ma).sum() >= 0.5 * max(1, np.isfinite(mb).sum()) else mb


def niveaux_jeu(j):
    df = j['df']; n = len(df); nv = j['niv']
    vide = np.full((n, 0), np.nan)
    if nv is None:
        return {(f, d): vide for f in ('piv', 'pivdet', 'tous') for d in (1, -1)}, {}
    piv = np.hstack([_mat(nv, 'PWR', 'PW'), _mat(nv, 'PMR', 'PM'), _mat(nv, 'PYR', 'PY')])
    ses = nv[[c for c in nv.columns if c.startswith('lv_SES_')]].to_numpy(float)
    mon = nv[[c for c in nv.columns if c.startswith('lv_MON_')]].to_numpy(float)
    zl = df['zb_sup_b'].to_numpy(float)[:, None]      # bord bas de la zone baissière au-dessus (objectif d'un long)
    zs = df['zh_inf_h'].to_numpy(float)[:, None]      # bord haut de la zone haussière en dessous (objectif d'un short)
    lev = {}
    for d, z in ((1, zl), (-1, zs)):
        lev[('piv', d)] = piv
        lev[('pivdet', d)] = np.hstack([piv, z])
        lev[('tous', d)] = np.hstack([piv, z, ses, mon])
    couv = {k: float(np.isfinite(v).any(1).mean()) for k, v in lev.items() if k[1] == 1}
    return lev, couv


# ═════════════════════════════ CONTEXTE ═════════════════════════════
_C = {}


def construire_ctx(source):
    jeux = charger(source)
    if not jeux:
        raise SystemExit('aucune donnée 15 min pour la source %s' % source)
    PM = []
    for ji, j in enumerate(jeux):
        df = j['df']; n = len(df)
        V = VT.calculer_votes(df, j, source)
        F, I = V['F'].to_numpy(), V['I'].to_numpy()
        bias = []
        for bf, bi in BIAS:
            bias.append(((F >= bf - EPS) & (I >= bi - EPS), (F <= -bf + EPS) & (I <= -bi + EPS)))
        m = df['min_paris'].to_numpy()
        fen = (m >= FEN_DEBUT) & (m < FEN_FIN) & (m + UT < FEN_FIN)
        fen25 = fen & (m >= 930)
        sig = (df['sig_long_fort'].to_numpy(bool) | df['sig_long_moyen'].to_numpy(bool),
               df['sig_short_fort'].to_numpy(bool) | df['sig_short_moyen'].to_numpy(bool))
        un = [np.asarray(x, bool).copy() for x in sig]
        for k in ('hei_flip', 'tl', 'lvl', 'clx'):
            a, b = B.DECL[k]
            un[0] |= df[a].to_numpy(bool); un[1] |= df[b].to_numpy(bool)
        trig = {'sig': sig, 'union': (un[0], un[1]), 'p25': B.declencheur(df, 'tous')}
        tout = (np.ones(n, bool), np.ones(n, bool))
        det = B._det(DETK)(df); det = (np.asarray(det[0], bool), np.asarray(det[1], bool))
        clx = B._clx(df); feu = B._feu(60)(df); adx = B._adx(25)(df)
        t4 = B._trend('trend_240')(df)
        def et(*xs):
            return (np.logical_and.reduce([np.asarray(x[0], bool) for x in xs]), np.logical_and.reduce([np.asarray(x[1], bool) for x in xs]))
        qual = {'aucune': tout, 'det': det, 'det+clx': et(det, clx), 'det+feu': et(det, feu),
                'det+adx': et(det, adx), 'det+trend4h': et(det, t4) if t4 is not None else et(det, tout)}
        det2 = B._det(2.0)(df)
        qual['p25'] = et((np.asarray(det2[0], bool), np.asarray(det2[1], bool)), t4 if t4 is not None else tout)
        # jours -> blocs de walk-forward
        jr = M.barres(df).jour_cme(); uj = np.unique(jr)
        bornes = np.linspace(0, len(uj), RATIO + K_PLIS + 1).round().astype(int)
        blk = np.zeros(n, np.int64)
        for q in range(RATIO + K_PLIS):
            blk[np.isin(jr, uj[bornes[q]:bornes[q + 1]])] = q
        b = M.barres(df)
        f1, i1 = b.drapeaux_heure('22:15', '00:20', 'Europe/Paris')
        f2, i2 = b.drapeaux_heure('15:59', '17:00', 'America/Chicago')
        lev, couv = niveaux_jeu(j)
        heure = pd.DatetimeIndex(pd.to_datetime(b.t_clo, unit='ns', utc=True)).tz_convert('Europe/Paris').hour.to_numpy()
        PM.append(dict(fen=fen, fen25=fen25, trig=trig, qual=qual, bias=bias, blk=blk, jour=jr, ndays=len(uj), votes=V,
                       fin=f1 | f2, intl=i1 | i2, lev=lev, couv=couv, heure=heure))
    return dict(jeux=jeux, PM=PM, OFF=O.decalages(jeux), ndays=sum(p['ndays'] for p in PM))


def masques(ci, ji, e):
    pm = ci['PM'][ji]
    if e['fam'] == 'P':
        a = pm['trig']['p25']; q = pm['qual']['p25']; fen = pm['fen25']
    else:
        a = pm['trig'][e['trig']]; q = pm['qual'][e['qual']]; fen = pm['fen']
    L = a[0] & q[0] & fen; S = a[1] & q[1] & fen
    if e['bi'] is not None:
        bl, bs = pm['bias'][e['bi']]
        L = L & bl; S = S & bs
    return L, S


def placebo(T, pm, e, cache, ji):
    """Moyennes (gagne, r) par (sens, heure) sur les barres permises : fenêtre de l'entrée + sens du biais."""
    cle = (ji, e['fam'] == 'P', e['bi'])
    if cle in cache:
        return cache[cle]
    pw = np.zeros((2, 24)); pr = np.zeros((2, 24))
    fen = pm['fen25'] if e['fam'] == 'P' else pm['fen']
    for d in range(2):
        ok = T['ok'][d] & fen
        if e['bi'] is not None:
            ok = ok & pm['bias'][e['bi']][d]
        h = pm['heure']
        cnt = np.bincount(h[ok], minlength=24).astype(float)
        sw = np.bincount(h[ok], weights=T['gagne'][d][ok].astype(float), minlength=24)
        sr = np.bincount(h[ok], weights=T['r'][d][ok], minlength=24)
        tot = max(cnt.sum(), 1.0)
        with np.errstate(invalid='ignore', divide='ignore'):
            pw[d] = np.where(cnt > 0, sw / cnt, sw.sum() / tot); pr[d] = np.where(cnt > 0, sr / cnt, sr.sum() / tot)
    cache[cle] = (pw, pr)
    return pw, pr


def rassembler(ci, T, e, cache):
    cols = {k: [] for k in ('jeu', 'jour', 'blk', 'pnl', 'r', 'pw', 'pr', 'ent', 'sor', 'mae', 'mfe', 'risque', 'sens', 'bar')}
    for ji in range(len(ci['jeux'])):
        L, S = masques(ci, ji, e)
        idx, sens = TB.trades_table(T[ji], L, S)
        if not len(idx):
            continue
        pm = ci['PM'][ji]; tab = T[ji]
        pw, pr = placebo(tab, pm, e, cache, ji)
        h = pm['heure'][idx]
        cols['jeu'].append(np.full(len(idx), ji)); cols['jour'].append(pm['jour'][idx]); cols['blk'].append(pm['blk'][idx])
        cols['pnl'].append(tab['pnl'][sens, idx]); cols['r'].append(tab['r'][sens, idx])
        cols['pw'].append(pw[sens, h]); cols['pr'].append(pr[sens, h])
        cols['ent'].append(tab['ent'][sens, idx] + ci['OFF'][ji]); cols['sor'].append(tab['sor'][sens, idx] + ci['OFF'][ji])
        cols['mae'].append(tab['mae'][sens, idx]); cols['mfe'].append(tab['mfe'][sens, idx])
        cols['risque'].append(tab['risque'][sens, idx]); cols['sens'].append(sens); cols['bar'].append(idx)
    return {k: (np.concatenate(x) if x else np.zeros(0)) for k, x in cols.items()}


def sous(c, blocs):
    m = np.isin(c['blk'], blocs)
    return {k: v[m] for k, v in c.items()}


def stats(c, ndays=None):
    s = O.stats(c)
    s['tpd'] = s['n'] / ndays if ndays else np.nan
    return s


def tradeify(c, tailles, n_sim):
    return O.note_tradeify(c, tailles, n_sim)


def vide_tr():
    return dict(p_reussite=np.nan, p_payout=np.nan, ve=np.nan, micros=0)


# ═════════════════════════════ TRAVAIL PAR GESTION (processus fils) ═════════════════════════════
def travail(gi):
    ci = _C['ci']; nm = _C['nmin']
    gk = GEOMS[gi]; g = geom_dict(gk)
    T = []
    for ji, j in enumerate(ci['jeux']):
        pm = ci['PM'][ji]
        J = SF.Jeu(M, j['df'], j['instrument'], pm['fin'], pm['intl'], pm['lev'])
        t = J.table(g, pm['fen'])
        t['heure'] = pm['heure']
        T.append(t)
    cache = {}
    sortie = {}
    tail = TAILLES_PART if g['part'] else TAILLES_MC
    for ei, e in enumerate(ENTREES):
        c = rassembler(ci, T, e, cache)
        s = stats(c, ci['ndays'])
        if e['cand'] and s['n'] >= nm and s['r_moyen'] > 0:
            s.update(tradeify(c, tail, N_SIM_MC))
        else:
            s.update(vide_tr())
        sortie[ei] = (c if e['cand'] else None, s)
    motifs = {}
    for t in T:
        for k, x in t['motifs'].items():
            motifs[k] = motifs.get(k, 0) + x
    return gi, sortie, motifs


# ═════════════════════════════ RÈGLE ═════════════════════════════
def ve_compte(S, v, nm):
    s = S.get(v)
    if s is None or not (s['n'] >= nm and s['r_moyen'] > 0) or s.get('ve') is None or not np.isfinite(s['ve']):
        return 0.0
    return float(s['ve'])


def score_lisse(S, v, nm):
    liste = [ve_compte(S, v, nm)] + [ve_compte(S, w, nm) for w in voisines(v) if w in S]
    return float(np.mean(liste)), len(liste) - 1


def eligible(s, nm, tier=1):
    if not (s['n'] >= nm and s['r_moyen'] > 0):
        return False
    if tier <= 2 and not s['gagnants'] >= GAGNANTS_MIN:
        return False
    if tier <= 1 and not s['tpd'] >= TPD_MIN:
        return False
    return True


def choisir(S, nm, tiers=(1, 2, 3)):
    for tier in tiers:
        cand = sorted([(score_lisse(S, v, nm)[0], v) for v, s in S.items() if eligible(s, nm, tier)], key=lambda x: (-x[0], -x[1][0]))
        if cand:
            return tier, cand
    return 0, []


def profils(S, nm, tier, cand):
    """Recommandée + au plus 2 alternatives différentes (règle fixée en tête de fichier)."""
    if not cand:
        return []
    sc0, v0 = cand[0]
    rec = (sc0, v0, 'recommandé')
    out = [rec]
    s0 = S[v0]
    def prend(filtre, nom):
        for sc, v in cand:
            s = S[v]
            if sc >= 0.5 * sc0 and all(different(v, w[1]) for w in out) and filtre(s):
                out.append((sc, v, nom)); return True
        return False
    if not prend(lambda s: s['tpd'] >= 1.3 * s0['tpd'], 'plus de trades'):
        prend(lambda s: s['tpd'] >= 1.15 * s0['tpd'], 'plus de trades')
    if not prend(lambda s: s['r_moyen'] >= s0['r_moyen'] + 0.10, 'plus de R') and len(out) < 3:
        # aucune éligible n'a nettement plus de R : on montre la meilleure gestion SUR NIVEAUX AVEC PARTIEL (demande de
        # Jeremy), même si elle n'atteint pas 55 % de gagnants (>= 1 trade/jour, R > 0, n >= N_MIN seulement).
        rel = sorted([(score_lisse(S, v, nm)[0], v) for v, s in S.items()
                      if s['n'] >= nm and s['r_moyen'] > 0 and s['tpd'] >= TPD_MIN and classe_sortie(GEOMS[v[1]]) == 'niveau + partiel'],
                     key=lambda x: -x[0])
        for sc, v in rel:
            if sc >= 0.5 * sc0 and all(different(v, w[1]) for w in out):
                out.append((sc, v, 'niveaux + partiel (55 % de gagnants NON atteint)')); break
    return out


# ═════════════════════════════ PINE ═════════════════════════════
def ligne_pine(v, micros):
    ei, gi = v; e = ENTREES[ei]; k, fi = GEOMS[gi]; f = FORMES[fi][1]
    kv = {}
    if e['fam'] == 'P':
        kv.update(sens='Les deux', clx=1, sig=1, sigNiv='Fort seulement', hei=1, tl=1, lvl=1, div=0, tr=1, tr4h=1, feu=0, ema=0,
                  adx=0, det=1, detK='2', clxF=0, bo=0, maxJour=0, hr=1, hr1On=1, hr1='1530-2215', hr2On=0)
        if e['bi'] is not None:
            kv.update(bias=1, bF='%g' % BIAS[e['bi']][0], bI='%g' % BIAS[e['bi']][1])
    else:
        un = e['trig'] == 'union'
        kv.update(sens='Les deux', sig=1, sigNiv='Fort + Moyen', hei=int(un), tl=int(un), lvl=int(un), clx=int(un), div=0,
                  tr=int(e['qual'] == 'det+trend4h'), feu=int(e['qual'] == 'det+feu'), ema=0, adx=int(e['qual'] == 'det+adx'),
                  det=int(e['qual'] != 'aucune'), detK='%g' % DETK, clxF=int(e['qual'] == 'det+clx'), bo=0, maxJour=0,
                  hr=1, hr1On=1, hr1='0020-2215', hr2On=0)
        if e['qual'] == 'det+trend4h':
            kv['tr4h'] = 1
        if e['qual'] == 'det+feu':
            kv.update(feuMode='Part dans le sens ≥ seuil', feuSeuil=60)
        if e['qual'] == 'det+adx':
            kv['adxMin'] = 25
        if e['bi'] is not None:
            kv.update(bias=1, bF='%g' % BIAS[e['bi']][0], bI='%g' % BIAS[e['bi']][1])
    kv.update({'stop': 'ATR × k', 'atrK': '%g' % k, 'trail': 'Aucun', 'oppArr': 0, 'fin': 0, 'pf': 1, 'beTk': BE_TICKS})
    kv['be'] = int(bool(f.get('be'))); kv['oppHei'] = int(bool(f.get('hei'))); kv['tBar'] = f.get('tBar', 0)
    if f.get('be'):
        kv['beR'] = '%g' % f['be']
    if f['tp'] == 'R':
        kv.update(tp='En R', tpR='%g' % f['R'], part=0)
    else:
        fam = f['fam']
        kv.update(tp='Prochain niveau', tpA=1, tpM=1, tpW=1, tpD=int(fam != 'piv'), tpMo=int(fam == 'tous'), tpSe=int(fam == 'tous'),
                  tpRo=0, rrMin='%g' % f['rr'], tpMarge=4, tpSans='Objectif en R', tpR='1.5', part=int(bool(f['part'])), partPct=50,
                  partRest='2e niveau' if f['part'] == 1 else 'Stop seulement (suiveur, break-even, signaux)', partBE=1)
    kv.update(taille='Contrats fixes', fixe=int(max(2 if f.get('part') else 1, micros)))
    return ';'.join('%s=%s' % (a, b) for a, b in kv.items())


def nom_court(v):
    ei, gi = v; e = ENTREES[ei]; k, fi = GEOMS[gi]
    if e['fam'] == 'P':
        ent = 'P25' + ('+biais%g/%g' % BIAS[e['bi']] if e['bi'] is not None else '')
    else:
        ent = 'biais%g/%g %s %s' % (BIAS[e['bi']] + ({'sig': 'Sig', 'union': 'union'}[e['trig']], e['qual'].replace('det', 'Det')))
    return '%s · %gATR · %s' % (ent, k, FORMES[fi][0].replace('pivots+Detector+Monday+sessions', 'tous niv.').replace('pivots+Detector', 'piv+Det')
                                .replace('partiel->2e niveau', 'partiel+2e').replace('partiel->reste Heishinator', 'partiel+Hei').replace('sans partiel', 'simple'))


def verifier_sim(ci, k=120, graine=3):
    """Re-vérifie la simulation FIN contre moteur.backtest (R fixe, tBar, BE, Heishinator, niveaux, partiel)."""
    j = ci['jeux'][0]; df = j['df']; n = len(df); pm = ci['PM'][0]
    fin_p, intl_p = M.barres(df).drapeaux_heure('22:15', '00:20', 'Europe/Paris')
    J = SF.Jeu(M, df, j['instrument'], fin_p, intl_p, pm['lev'])
    lev = pm['lev'].get(('tous', 1))
    rng = np.random.default_rng(graine)
    ids = rng.choice(np.flatnonzero(pm['fen']), min(k, int(pm['fen'].sum())), replace=False)
    tests = [SF.gestion_defaut(k=2, tp='R', R=1.5, tBar=8), SF.gestion_defaut(k=1.5, tp='R', R=2, be=1.0),
             SF.gestion_defaut(k=2, tp='R', R=2, hei=1, tBar=12), SF.gestion_defaut(k=2, tp='Rpart', R=2, R1=1.0, be_ticks=1)]
    if lev is not None and lev.shape[1]:
        tests += [SF.gestion_defaut(k=2, tp='niv', fam='tous', rr=1.0, hei=1), SF.gestion_defaut(k=2.5, tp='niv', fam='tous', rr=1.5)]
    ecarts = 0; total = 0
    for g in tests:
        for i in ids:
            for d in (1, -1):
                G = dict(instrument=j['instrument'], stop={'mode': 'atr', 'k': g['k']}, heure_sortie='22:15',
                         fuseau_sortie='Europe/Paris', heure_reprise='00:20')
                if g['tp'] in ('R', 'Rpart'):
                    G['objectif'] = {'mode': 'R', 'k': g['R']}
                if g['tp'] == 'Rpart':
                    G['partiel'] = {'R': g['R1'], 'fraction': 0.5, 'be_apres': True}
                if g['tp'] == 'niv':
                    lv = pm['lev'][(g['fam'], d)]
                    G['objectif'] = {'mode': 'niveau', 'long': {'a%d' % q: lv[:, q] for q in range(lv.shape[1])},
                                     'short': {'a%d' % q: lv[:, q] for q in range(lv.shape[1])},
                                     'ratio_min': g['rr'], 'marge_ticks': g['marge'], 'si_absent': ('R', g['repliR'])}
                if g['be']:
                    G['break_even'] = {'R': g['be'], 'ticks': g['be_ticks']}
                if g['tBar']:
                    G['sortie_barres'] = g['tBar']
                if g['hei']:
                    G['sortie_signal'] = {'long': 'hei_flip_bas', 'short': 'hei_flip_haut'}
                sig = np.zeros(n, bool); sig[int(i)] = True
                T = M.backtest(df, **{('long' if d == 1 else 'short'): sig}, gestion=G)
                r = J.trade(int(i), d, g)
                if r is None and not len(T):
                    continue
                total += 1
                if (r is None) != (not len(T)) or abs(r[0] - T['r'].iloc[0]) > 1e-9:
                    ecarts += 1
    return total, ecarts


def df_trades_complet(c, ci, v):
    """Liste détaillée des trades d'une variante (rejoués par le simulateur FIN : prix d'entrée, stop, objectifs,
    prix de sortie, motif, niveau utilisé)."""
    g = geom_dict(GEOMS[v[1]]); J = {}
    rows = []
    for ji, i, sens in zip(c['jeu'].astype(int), c['bar'].astype(int), c['sens'].astype(int)):
        if ji not in J:
            j = ci['jeux'][ji]; pm = ci['PM'][ji]
            J[ji] = SF.Jeu(M, j['df'], j['instrument'], pm['fin'], pm['intl'], pm['lev'])
        d = 1 if sens == 0 else -1
        r = J[ji].trade(int(i), d, g, det=True)
        px, s, tg0, pp0, xp, nom_o = r[9]
        rows.append(dict(entree_t=pd.Timestamp(r[5], tz='UTC').tz_convert('Europe/Paris'),
                         sortie_t=pd.Timestamp(r[6], tz='UTC').tz_convert('Europe/Paris'),
                         sens='long' if d == 1 else 'short', jeu=ci['jeux'][ji]['nom'], prix_entree=px, stop_initial=s,
                         objectif=tg0 if tg0 is not None else np.nan, objectif_partiel=pp0 if pp0 is not None else np.nan,
                         prix_sortie=xp, motif_sortie=r[8], niveau_objectif=nom_o, r=r[0], pnl_usd=r[1], risque_usd=r[2],
                         mae_usd=r[3], mfe_usd=r[4]))
    return pd.DataFrame(rows).sort_values('entree_t').reset_index(drop=True)


# ═════════════════════════════ PROGRAMME ═════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', choices=('cache', 'dataset'), default='cache')
    ap.add_argument('--recalcul', action='store_true')
    ap.add_argument('--registre', action='store_true')
    ap.add_argument('--rangs', default='', help='avec --registre : ne passer que ces rangs (ex. 3)')
    ap.add_argument('--petit', action='store_true', help='essai rapide : 1 stop seulement')
    a = ap.parse_args()
    t0 = time.time()
    nm = n_min(a.source)
    O._G['flex'] = SIM.charge_regles()['tradeify_50k_select_flex']
    ci = construire_ctx(a.source)
    _C['ci'] = ci; _C['nmin'] = nm
    out = []
    pr = lambda s='': (out.append(s), print(s, flush=True))   # noqa: E731
    pr('SOURCE %s | %d jeux : %s | %d jours | N_MIN %d' % (a.source, len(ci['jeux']), ', '.join(
        '%s %d barres %s->%s' % (j['nom'], len(j['df']), j['df'].index[0].date(), j['df'].index[-1].date()) for j in ci['jeux']), ci['ndays'], nm))
    for ji, j in enumerate(ci['jeux']):
        Vt = ci['PM'][ji]['votes']
        z = (Vt.drop(columns=['F', 'I']) == 0).mean()
        pr('  %s : niveaux alignés %.0f %% | couverture niveaux (long) %s | votes à 0 : %s' % (
            j['nom'], 100 * j['niv_couv'], {k[0]: round(v, 2) for k, v in ci['PM'][ji]['couv'].items()},
            ', '.join('%s %.0f%%' % (k, 100 * x) for k, x in z.items() if x > 0.3)))
    tot, ec = verifier_sim(ci)
    pr('VÉRIFICATION simulation FIN vs moteur.backtest : %d trades comparés, %d écarts' % (tot, ec))
    gis = [gi for gi in range(len(GEOMS)) if not a.petit or GEOMS[gi][0] == 2.0]
    pr('%d entrées x %d gestions = %d variantes candidates (+ références sans biais)' % (
        sum(e['cand'] for e in ENTREES), len(gis), sum(e['cand'] for e in ENTREES) * len(gis)))
    chemin = os.path.join(SORTIES, 'brut_%s%s.pkl' % (a.source, '_petit' if a.petit else ''))
    sig_ctx = (a.source, tuple((j['nom'], len(j['df']), str(j['df'].index[0]), str(j['df'].index[-1])) for j in ci['jeux']),
               tuple(gis), len(ENTREES), N_SIM_MC, 3)
    S, TR, REFS, MOTIFS = {}, {}, {}, {}
    if os.path.exists(chemin) and not a.recalcul:
        obj = pickle.load(open(chemin, 'rb'))
        if obj['sig'] == sig_ctx:
            S, TR, REFS, MOTIFS = obj['S'], obj['TR'], obj['REFS'], obj['MOTIFS']
            print('balayage : relu (%s)' % chemin, flush=True)
    if not S:
        with mp.get_context('fork').Pool(NPROC) as p:
            for gi, sortie, motifs in p.imap_unordered(travail, gis, chunksize=1):
                for ei, (c, s) in sortie.items():
                    if ENTREES[ei]['cand']:
                        S[(ei, gi)] = s; TR[(ei, gi)] = c
                    else:
                        REFS[(ei, gi)] = s
                MOTIFS[gi] = motifs
        pickle.dump(dict(sig=sig_ctx, S=S, TR=TR, REFS=REFS, MOTIFS=MOTIFS), open(chemin, 'wb'))
    pr('balayage + Tradeify : %.0f s' % (time.time() - t0))

    tier, cand = choisir(S, nm)
    prof = profils(S, nm, tier, cand)
    pr('palier de la règle : %d (1 = règle complète) ; éligibles palier 1 : %d / %d' % (
        tier, sum(eligible(s, nm, 1) for s in S.values()), len(S)))

    # --- CSV complet
    def ref_de(v):
        ei, gi = v; e = ENTREES[ei]
        if e['fam'] != 'B':
            return None
        return REFS.get((IDX_E[('R', None, e['trig'], e['qual'])], gi))
    lignes = []
    for v, s in S.items():
        sc, nv = score_lisse(S, v, nm)
        r = ref_de(v)
        e = ENTREES[v[0]]; k, fi = GEOMS[v[1]]
        lignes.append(dict(variante=libelle(v), entree=libelle_entree(e), famille_entree=e['fam'], stop=k, sortie=FORMES[fi][0],
                           classe_sortie=classe_sortie(GEOMS[v[1]]),
                           **{x: s[x] for x in ('n', 'tpd', 'gagnants', 'r_moyen', 'pf', 'net_usd', 'plac_gagnants', 'plac_r',
                                                'ecart_pts', 'z_ecart', 'ecart_r', 'p_reussite', 'p_payout', 've', 'micros')},
                           score_lisse=sc, eligible1=bool(eligible(s, nm, 1)),
                           sans_biais_n=(r or {}).get('n'), sans_biais_gagnants=(r or {}).get('gagnants'),
                           sans_biais_r=(r or {}).get('r_moyen'), sans_biais_pf=(r or {}).get('pf')))
    CSV = pd.DataFrame(lignes).sort_values('score_lisse', ascending=False)
    CSV.to_csv(os.path.join(SORTIES, 'balayage_%s.csv.gz' % a.source), index=False, float_format='%.5g')

    # --- agrégats : ce que chaque choix apporte (variantes n >= N_MIN)
    ok = CSV[CSV['n'] >= nm]
    pr('\nAGRÉGATS (variantes n >= %d : %d)' % (nm, len(ok)))
    if len(ok):
        b = ok[ok['famille_entree'] == 'B']
        d_t = (b['gagnants'] - b['sans_biais_gagnants']).dropna(); d_r = (b['r_moyen'] - b['sans_biais_r']).dropna()
        pr('  biais vs sans biais (mêmes déclencheurs/confirmation/sortie) : taux %+.1f pts (%.0f %% mieux), R %+.3f (%.0f %% mieux)' % (
            100 * d_t.mean(), 100 * (d_t > 0).mean(), d_r.mean(), 100 * (d_r > 0).mean()))
        pr('  déclencheurs vs hasard dans le biais : taux %+.1f pts, R %+.3f (%.0f %% des variantes > 0)' % (
            100 * (ok['gagnants'] - ok['plac_gagnants']).mean(), (ok['r_moyen'] - ok['plac_r']).mean(),
            100 * ((ok['r_moyen'] - ok['plac_r']) > 0).mean()))
        for cl in ('R fixe', 'niveau', 'niveau + partiel'):
            o2 = ok[ok['classe_sortie'] == cl]
            if len(o2):
                pr('  sortie %-17s : %4d variantes | %.2f trades/jour | %.1f %% gagnants | R %+.3f | écart au placebo %+.3f R | VE moy. %.0f $ | P(réussite) moy. %.2f' % (
                    cl, len(o2), o2['tpd'].mean(), 100 * o2['gagnants'].mean(), o2['r_moyen'].mean(), o2['ecart_r'].mean(),
                    o2['ve'].fillna(0).mean(), o2['p_reussite'].mean()))
        for k in STOPS:
            o2 = ok[ok['stop'] == k]
            pr('  stop %g ATR : R %+.3f, %.1f %% gagnants, VE moy. %.0f $' % (k, o2['r_moyen'].mean(), 100 * o2['gagnants'].mean(), o2['ve'].fillna(0).mean()))
        for f_ in sorted(set(CSV['sortie'])):
            o2 = ok[ok['sortie'] == f_]
            if len(o2):
                pr('  forme %-52s : %3d | %.2f /j | %.1f %% | R %+.3f | écart placebo %+.3f | VE %.0f $' % (
                    f_, len(o2), o2['tpd'].mean(), 100 * o2['gagnants'].mean(), o2['r_moyen'].mean(), o2['ecart_r'].mean(), o2['ve'].fillna(0).mean()))
    # --- préréglage 25 tel quel
    v25 = (IDX_E[('P', None, 'p25', 'p25')], GEOMS.index((2.0, [f[0] for f in FORMES].index('R1+N8'))))
    if v25 in S:
        s = S[v25]
        pr('\nPRÉRÉGLAGE 25 tel quel (15:30-22:15, 2 ATR, 1R, 8 bougies) : n=%d (%.2f /jour) %.1f %% gagnants R %+.3f PF %.2f | P(réussite)=%s VE=%s' % (
            s['n'], s['tpd'], 100 * s['gagnants'], s['r_moyen'], s['pf'], s['p_reussite'], s['ve']))

    # --- bootstrap de White (R brut, et R - placebo), toutes variantes n >= 10
    jours_id = {}
    for ji, pm in enumerate(ci['PM']):
        for jr in np.unique(pm['jour']):
            jours_id[(ji, int(jr))] = len(jours_id)
    ND = len(jours_id)
    Vw = [v for v in S if S[v]['n'] >= 10]
    X = np.zeros((len(Vw), ND), np.float32); XP = np.zeros((len(Vw), ND), np.float32)
    for q, v in enumerate(Vw):
        c = TR[v]
        di = np.array([jours_id[(int(j), int(jr))] for j, jr in zip(c['jeu'], c['jour'])], int)
        np.add.at(X[q], di, c['r']); np.add.at(XP[q], di, c['r'] - c['pr'])
    tR, pR, pR_best, _ = AN.white(X, n_boot=1000, graine=1)
    tP, pP, pP_best, _ = AN.white(XP, n_boot=1000, graine=2)
    pos = {v: q for q, v in enumerate(Vw)}
    pr('\nWHITE (%d variantes n>=10, %d jours) : meilleure t(R brut)=%.2f p=%.2f ; meilleure t(R - placebo)=%.2f p=%.2f' % (
        len(Vw), ND, tR.max(), pR_best, tP.max(), pP_best))

    # --- walk-forward : la règle complète (avec profils) sur 3 blocs, test sur le suivant
    nm_pli = max(8, int(round(nm * RATIO / (RATIO + K_PLIS))))
    ndays_pli = ci['ndays'] * RATIO / (RATIO + K_PLIS)
    wf = []
    t1 = time.time()
    for p_ in range(K_PLIS):
        app = list(range(p_, p_ + RATIO)); tst = [p_ + RATIO]
        Sp = {}
        for v in S:
            c = sous(TR[v], app)
            Sp[v] = stats(c, ndays_pli); Sp[v].update(vide_tr())
        _C['wf'] = (Sp, app)
        todo = [v for v in S if Sp[v]['n'] >= nm_pli and Sp[v]['r_moyen'] > 0 and Sp[v]['gagnants'] >= 0.5]   # (allègement déclaré : la note d'apprentissage n'est calculée qu'à partir de 50 % de gagnants)
        # coût : la note Tradeify d'apprentissage n'est calculée que pour les variantes qui peuvent compter
        _C['TR'] = TR
        with mp.get_context('fork').Pool(NPROC) as pl:
            for v, nt in pl.imap_unordered(_eval_pli, [(v, app) for v in todo], chunksize=8):
                Sp[v].update(nt)
        tp, ch = choisir(Sp, nm_pli)
        if not ch:
            wf.append(dict(pli=p_, choix=None)); continue
        v = ch[0][1]
        ct = sous(TR[v], tst); st = stats(ct)
        wf.append(dict(pli=p_, choix=libelle(v), palier=tp, app_n=Sp[v]['n'], app_g=Sp[v]['gagnants'], app_r=Sp[v]['r_moyen'], test=st, ct=ct))
    pool_wf = {k: np.concatenate([w['ct'][k] for w in wf if w.get('ct') is not None and len(w['ct']['pnl'])] or [np.zeros(0)])
               for k in ('pnl', 'r', 'pw', 'pr')}
    sw = stats(pool_wf)
    pr('WALK-FORWARD (%d plis, %.0f s) : n=%d gagnants %s (placebo %s) R %s PF %s net %s $ (1 micro)' % (
        K_PLIS, time.time() - t1, sw['n'], '%.1f %%' % (100 * sw['gagnants']) if sw['n'] else 'n/a',
        '%.1f %%' % (100 * sw['plac_gagnants']) if sw['n'] else 'n/a', '%+.3f' % sw['r_moyen'] if sw['n'] else 'n/a',
        '%.2f' % sw['pf'] if sw['n'] else 'n/a', '%+.0f' % sw['net_usd']))
    for w in wf:
        if w.get('choix'):
            t = w['test']
            pr('   pli %d (palier %d) : %s | appr. %d tr. %.0f %% R %+.2f | test %d tr. %s R %s' % (
                w['pli'], w['palier'], w['choix'], w['app_n'], 100 * w['app_g'], w['app_r'], t['n'],
                '%.0f %%' % (100 * t['gagnants']) if t['n'] else '-', '%+.2f' % t['r_moyen'] if t['n'] else '-'))
        else:
            pr('   pli %d : aucune variante éligible' % w['pli'])

    # --- les livrés
    pine = []; livres = []
    from scipy import stats as sps
    for rang, (sc, v, nom) in enumerate(prof, 1):
        s = S[v]; r = ref_de(v); c = TR[v]
        tt = c['r'] - c['pr']
        pval = float(1 - sps.t.cdf(tt.mean() / (tt.std(ddof=1) / np.sqrt(len(tt))), len(tt) - 1)) if len(tt) > 2 else np.nan
        q = pos.get(v); wp = (pR[q], pP[q]) if q is not None else (np.nan, np.nan)
        e = ENTREES[v[0]]
        txt = ('\n#%d [%s] %s\n   n=%d (%.2f /jour) gagnants %.1f %% R %+.3f PF %.2f net %+.0f $/micro\n'
               '   placebo (hasard%s, même gestion) : gagnants %.1f %% R %+.3f | écart %+.1f pts, %+.3f R (z=%.1f, p(R)=%.2f)\n'
               '   %s\n'
               '   Tradeify Select Flex : %d micros P(réussite)=%.2f P(1er payout)=%.2f VE=%+.0f $ | score lissé %+.0f $ (%d voisines) | White p: R brut %.2f, R-placebo %.2f') % (
            rang, nom, libelle(v), s['n'], s['tpd'], 100 * s['gagnants'], s['r_moyen'], s['pf'], s['net_usd'],
            ' dans le sens du biais' if e['bi'] is not None else '', 100 * s['plac_gagnants'], s['plac_r'], s['ecart_pts'], s['ecart_r'], s['z_ecart'], pval,
            ('SANS biais, mêmes déclencheurs : n=%d gagnants %.1f %% R %+.3f PF %.2f' % (r['n'], 100 * r['gagnants'], r['r_moyen'], r['pf'])) if r and r['n'] else '(pas de référence sans biais)',
            s['micros'], s['p_reussite'], s['p_payout'], s['ve'], sc, score_lisse(S, v, nm)[1], wp[0], wp[1])
        pr(txt)
        mo = MOTIFS.get(v[1], {})
        tot_m = max(sum(mo.values()), 1)
        pr('   issues de la table (toutes barres) : ' + ', '.join('%s %.0f %%' % (k_, 100 * x / tot_m) for k_, x in sorted(mo.items(), key=lambda z: -z[1])[:6]))
        pine.append((nom, v, s))
        livres.append((nom, v, s, sc, pval, wp))
    if not prof:
        pr('\nAUCUNE variante ne passe même le dernier palier de la règle.')

    # --- top 10 pour mémoire
    pr('\nTOP 10 par score lissé (éligibles palier %d) :' % tier)
    for sc, v in cand[:10]:
        s = S[v]
        pr('  %+7.0f $ | %s | n=%d %.2f/j %.0f %% R %+.2f | VE %+.0f $ P=%.2f' % (sc, libelle(v), s['n'], s['tpd'], 100 * s['gagnants'], s['r_moyen'], s['ve'], s['p_reussite']))
    open(os.path.join(SORTIES, 'resume_%s.txt' % a.source), 'w').write('\n'.join(out) + '\n')

    with open(os.path.join(ICI, 'presets_pine.txt'), 'w') as fh:
        fh.write('// Optimiseur final (FIN), source %s, %s. 3 lignes MAXIMUM pour f_pr_def() de STRATEGIE_V1.pine (1 recommandée + au plus 2 alternatives).\n' % (
            a.source, pd.Timestamp.now(tz='Europe/Paris').strftime('%d/%m/%Y %H:%M')))
        fh.write('// Palier de la règle : %d (1 = règle complète : >= 1 trade/jour, >= 55 %% gagnants, R > 0). Source cache = 2 mois : REJETÉ comme décision, à relancer sur le DATASET.\n' % tier)
        fh.write('// Ajouter chaque nom EXACT dans options=[...] du menu « Préréglage », puis coller la ligne dans f_pr_def().\n')
        fh.write('// Réglages à la main (non modifiables par préréglage) : « Niveaux mesurés sur » = Vrais prix ; graphique en 15 MIN ; unité TREND supérieur = 4 h.\n')
        fh.write('// Taille : contrats FIXES (micros). Avec sortie partielle, au moins 2 micros, nombre pair (50 % de chaque côté).\n\n')
        for rang, (nom, v, s) in enumerate(pine, 1):
            titre = '%d FIN-%d %s' % (43 + rang - 1, rang, nom_court(v))
            fh.write('// %s | n=%d (%.2f/jour) gagnants %.0f %% R %+.2f PF %.2f | %d micros P=%.2f VE=%+.0f $\n' % (
                libelle(v), s['n'], s['tpd'], 100 * s['gagnants'], s['r_moyen'], s['pf'], s['micros'], s['p_reussite'], s['ve']))
            fh.write('     nom == "%s" ? "%s" :\n\n' % (titre[:110], ligne_pine(v, s['micros'])))

    if a.registre and prof:
        for rang, (nom, v, s, sc, pval, wp) in enumerate(livres, 1):
            if a.rangs and str(rang) not in a.rangs.split(','):
                continue
            c = TR[v]
            r = ref_de(v)
            verdict = ('essai à blanc %s : %s | profil %s | palier %d | %.2f trades/jour, placebo %.0f %% R %+.2f (écart %+.2f R, p=%.2f) | '
                       'sans biais %s | walk-forward n=%d %.0f %% R %+.2f | White p(R brut)=%.2f p(R-placebo)=%.2f ; VE Tradeify %+.0f $ (%d micros, P %.2f)') % (
                a.source, 'NON CONCLUANT (2 mois)' if a.source == 'cache' else 'à juger', nom, tier, s['tpd'], 100 * s['plac_gagnants'], s['plac_r'],
                s['ecart_r'], pval, ('%.0f %% R %+.2f' % (100 * r['gagnants'], r['r_moyen'])) if r and r['n'] else 'n/a',
                sw['n'], 100 * sw['gagnants'] if sw['n'] else float('nan'), sw['r_moyen'] if sw['n'] else float('nan'),
                pR_best, pP_best, s['ve'], s['micros'], s['p_reussite'])
            idr = RG.ajouter_test(dict(agent='FIN', famille='optimiseur-final', recette=libelle(v) + ' | 00:20-22:15, à plat 15:59 Chicago',
                                       marche='MES+MNQ (micros)', ut_signal='15', ut_entree='15', echantillon='dev_%s' % a.source,
                                       n_variantes_testees=len(S), p_tradeify=s['p_reussite'], p_ref_hasard='', verdict=verdict,
                                       trades=df_trades_complet(c, ci, v)), prefixe='FIN')
            print('registre :', idr)
    print('terminé en %.0f s' % (time.time() - t0))


def _eval_pli(args):
    v, app = args
    c = sous(_C['TR'][v], app)
    g = GEOMS[v[1]]
    tail = TAILLES_PART if FORMES[g[1]][1].get('part') else TAILLES_WF
    if FORMES[g[1]][1].get('part'):
        tail = [2, 4, 6]
    return v, O.note_tradeify(c, tail, N_SIM_WF)


if __name__ == '__main__':
    main()
