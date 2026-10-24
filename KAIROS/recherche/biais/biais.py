"""Biais global puis déclencheurs (BIA) — BIAIS_GLOBAL.md.

    ~/venv-quant/bin/python biais.py --source cache      # essai à blanc (2 mois)
    ~/venv-quant/bin/python biais.py --source dataset    # dès que les exports DATASET 15 min / 5 min existent

Balayage FIXÉ À L'AVANCE (432 variantes) :
  bF {0, .33, .55, .78} x bI {0, .2, .45} x déclencheurs {Signator Fort+Moyen ; union} x
  qualité {aucune ; Detector 1,5 ; Detector 1,5 + climax} x objectif {1 ; 1,5 ; 2 R} x unité {15 ; 5 min}
Gestion fixe : stop 2 ATR, sortie après 8 bougies, fenêtre 00:20-22:15 Paris, à plat 22:15 (chargement, tables
d'issues, simulateur Tradeify et placebo de optim25/optimiser.py, importés).

RÈGLE DE CHOIX (fixée avant de regarder) :
  éligible = >= 1 trade/jour en moyenne, >= 55 % de gagnants, R moyen > 0, n >= N_MIN ;
  score = moyenne de la valeur espérée Tradeify de la variante ET de ses voisines à un pas (bF, bI, déclencheur,
  qualité, objectif ; même unité ; voisine à R <= 0 ou n < N_MIN compte 0). On prend le meilleur score.
  Repli (déclaré dans les sorties) si personne n'est éligible : on relâche d'abord « >= 1 trade/jour », puis « 55 % ».
Comparaisons : (a) mêmes déclencheurs/qualité SANS biais ; (b) entrées AU HASARD dans le sens du biais (espérance
exacte : moyenne de la table d'issues sur les barres permises, même heure et même sens) ; (c) préréglage 25.
"""
from __future__ import annotations

import argparse
import itertools
import multiprocessing as mp
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')
ICI = os.path.dirname(os.path.abspath(__file__))
OPT = os.path.abspath(os.path.join(ICI, '..', 'optim25'))
sys.path[:0] = [ICI, OPT]
import optimiser as O  # noqa: E402  (charge aussi taux_combinatoire : B, D, TB, AN, SIM, RG)
import votes as VT  # noqa: E402

B, D, TB, AN, SIM, RG, M = O.B, O.D, O.TB, O.AN, O.SIM, O.RG, O.M

SORTIES = os.path.join(ICI, 'sorties')
os.makedirs(SORTIES, exist_ok=True)
O.SORTIES = SORTIES                       # les tables d'issues vont dans NOTRE dossier
NPROC = O.NPROC

# ═════════════════════════ BALAYAGE (fixé à l'avance) ═════════════════════════
BF = [0.0, 0.33, 0.55, 0.78]
BI = [0.0, 0.2, 0.45]
TRIG = ['sig', 'union']
QUAL = ['aucune', 'det', 'det+clx']
OBJ = [1.0, 1.5, 2.0]
UTS = [15, 5]
STOP, SORTIE = 2.0, 8
GEOMS = [(STOP, o, SORTIE, 0) for o in OBJ]
EPS = 1e-9
GAGNANTS_MIN = 0.55
TPD_MIN = 1.0
DETK = 1.5
FEN_DEBUT, FEN_FIN = O.FEN_DEBUT, O.FEN_FIN
ORDRE = ['bF', 'bI', 'trig', 'qual', 'obj', 'ut']
TAILLES_MC = [1, 2, 3, 4, 6, 8, 10]
TAILLES_WF = [1, 2, 4, 6]
N_SIM_MC, N_SIM_WF = 300, 200
K_PLIS, RATIO = 4, 3
BASE25 = dict(decl='tous', tr=240, det=2.0, feu=0, hr='1530', stop=2.0, obj=1.0, sortie=8, be=0)


def n_min(source):
    return 80 if source == 'dataset' else 30


def toutes():
    return [v for v in itertools.product(BF, BI, TRIG, QUAL, OBJ, UTS)]


def vd(v):
    return dict(zip(ORDRE, v))


def libelle(v):
    d = vd(v)
    return 'biais F>=%g I>=%g | %s | qualité %s | %gR | %d min' % (
        d['bF'], d['bI'], 'Signator F+M' if d['trig'] == 'sig' else 'union', d['qual'], d['obj'], d['ut'])


def voisines(v):
    d = vd(v); out = []
    for a, L in (('bF', BF), ('bI', BI), ('qual', QUAL), ('obj', OBJ)):
        k = L.index(d[a])
        for q in (k - 1, k + 1):
            if 0 <= q < len(L):
                w = dict(d); w[a] = L[q]; out.append(tuple(w[x] for x in ORDRE))
    w = dict(d); w['trig'] = 'union' if d['trig'] == 'sig' else 'sig'
    out.append(tuple(w[x] for x in ORDRE))
    return out


# ═════════════════════════ CONTEXTES (une par unité) ═════════════════════════
_C = {}


def construire_ctx(source, ut, recalcul):
    O.UT = ut
    jeux = D.charger_jeux(source, uts=(ut,))
    if not jeux:
        return None
    O.GEOMS = GEOMS
    T = O.construire_tables(jeux, '%s_%d' % (source, ut), recalcul)
    PM = []; pl = {}
    for ji, j in enumerate(jeux):
        df = j['df']; n = len(df)
        V = VT.calculer_votes(df, j, source)
        F, I = V['F'].to_numpy(), V['I'].to_numpy()
        bias = {}
        for bf in BF:
            for bi in BI:
                bl = (F >= bf - EPS) & (I >= bi - EPS)
                bs = (F <= -bf + EPS) & (I <= -bi + EPS)
                bias[(bf, bi)] = (bl, bs)
        m = df['min_paris'].to_numpy()
        fen = (m >= FEN_DEBUT) & (m < FEN_FIN) & (m + ut < FEN_FIN)
        sig = (df['sig_long_fort'].to_numpy(bool) | df['sig_long_moyen'].to_numpy(bool),
               df['sig_short_fort'].to_numpy(bool) | df['sig_short_moyen'].to_numpy(bool))
        un = [np.asarray(x, bool).copy() for x in sig]
        for k in ('hei_flip', 'tl', 'lvl', 'clx'):
            a, b = B.DECL[k]
            un[0] |= df[a].to_numpy(bool); un[1] |= df[b].to_numpy(bool)
        trig = {'sig': sig, 'union': (un[0], un[1])}
        dt = B._det(DETK)(df); cl = B._clx(df)
        tout = (np.ones(n, bool), np.ones(n, bool))
        qual = {'aucune': tout, 'det': (np.asarray(dt[0], bool), np.asarray(dt[1], bool)),
                'det+clx': (np.asarray(dt[0], bool) & cl[0], np.asarray(dt[1], bool) & cl[1])}
        t1 = B._trend('trend_240')(df)
        # jours -> blocs de walk-forward
        jr = M.barres(df).jour_cme(); uj = np.unique(jr)
        nb = RATIO + K_PLIS
        bornes = np.linspace(0, len(uj), nb + 1).round().astype(int)
        blk = np.zeros(n, np.int64)
        for q in range(nb):
            blk[np.isin(jr, uj[bornes[q]:bornes[q + 1]])] = q
        PM.append(dict(fen=fen, trig=trig, qual=qual, bias=bias, blk=blk, jour=jr, ndays=len(uj), votes=V, df=df,
                       tr240=t1))
    return dict(ut=ut, jeux=jeux, T=T, PM=PM, OFF=O.decalages(jeux), PLAC={},
                ndays=sum(p['ndays'] for p in PM))


def masques(ctx, ji, v, avec_biais=True):
    d = vd(v); pm = ctx['PM'][ji]
    a = pm['trig'][d['trig']]; q = pm['qual'][d['qual']]
    L = a[0] & q[0] & pm['fen']; S = a[1] & q[1] & pm['fen']
    if avec_biais:
        bl, bs = pm['bias'][(d['bF'], d['bI'])]
        L = L & bl; S = S & bs
    return L, S


def trades_v(ctx, v, avec_biais=True):
    g = (STOP, vd(v)['obj'], SORTIE, 0)
    out = []
    for ji in range(len(ctx['jeux'])):
        L, S = masques(ctx, ji, v, avec_biais)
        idx, sens = TB.trades_table(ctx['T'][(ji, g)], L, S)
        out.append((ji, idx, sens))
    return out


def placebo_biais(ctx, ji, g, bkey):
    """Entrées au hasard DANS LE SENS DU BIAIS : moyenne (gagne, r) de la table sur les barres permises
    (fenêtre + sens du biais), par (sens, heure). bkey=None : sans biais (toutes les barres de la fenêtre)."""
    cle = (ji, g, bkey)
    if cle in ctx['PLAC']:
        return ctx['PLAC'][cle]
    tab = ctx['T'][(ji, g)]; pm = ctx['PM'][ji]
    pw = np.zeros((2, 24)); pr = np.zeros((2, 24))
    for d in range(2):
        ok = tab['ok'][d] & pm['fen']
        if bkey is not None:
            ok = ok & pm['bias'][bkey][d]
        h = tab['heure']
        cnt = np.bincount(h[ok], minlength=24).astype(float)
        sw = np.bincount(h[ok], weights=tab['gagne'][d][ok].astype(float), minlength=24)
        sr = np.bincount(h[ok], weights=tab['r'][d][ok], minlength=24)
        tot = max(cnt.sum(), 1.0)
        with np.errstate(invalid='ignore', divide='ignore'):
            pw[d] = np.where(cnt > 0, sw / cnt, sw.sum() / tot); pr[d] = np.where(cnt > 0, sr / cnt, sr.sum() / tot)
    ctx['PLAC'][cle] = (pw, pr)
    return pw, pr


def rassembler(ctx, v, tr, blocs=None, avec_biais=True):
    d = vd(v); g = (STOP, d['obj'], SORTIE, 0)
    bkey = (d['bF'], d['bI']) if avec_biais else None
    cols = {k: [] for k in ('jeu', 'jour', 'pnl', 'r', 'pw', 'pr', 'ent', 'sor', 'mae', 'mfe', 'risque', 'sens', 'bar')}
    for ji, idx, sens in tr:
        if not len(idx):
            continue
        tab = ctx['T'][(ji, g)]
        if blocs is not None:
            m = np.isin(ctx['PM'][ji]['blk'][idx], blocs)
            idx, sens = idx[m], sens[m]
            if not len(idx):
                continue
        pw, pr = placebo_biais(ctx, ji, g, bkey)
        h = tab['heure'][idx]
        cols['jeu'].append(np.full(len(idx), ji)); cols['jour'].append(ctx['PM'][ji]['jour'][idx])
        cols['pnl'].append(tab['pnl'][sens, idx]); cols['r'].append(tab['r'][sens, idx])
        cols['pw'].append(pw[sens, h]); cols['pr'].append(pr[sens, h])
        cols['ent'].append(tab['ent'][sens, idx] + ctx['OFF'][ji]); cols['sor'].append(tab['sor'][sens, idx] + ctx['OFF'][ji])
        cols['mae'].append(tab['mae'][sens, idx]); cols['mfe'].append(tab['mfe'][sens, idx])
        cols['risque'].append(tab['risque'][sens, idx]); cols['sens'].append(sens); cols['bar'].append(idx)
    return {k: (np.concatenate(x) if x else np.zeros(0)) for k, x in cols.items()}


def jours_de(c):
    return len(np.unique(c['jeu'] * 10 ** 7 + c['jour'])) if len(c['pnl']) else 0


def stats(c, ndays=None):
    s = O.stats(c)
    s['tpd'] = s['n'] / ndays if ndays else np.nan
    return s


# ═════════════════════════ ÉVALUATION (processus fils) ═════════════════════════
def _eval(v):
    ctx = _C[vd(v)['ut']]
    tr = trades_v(ctx, v)
    c = rassembler(ctx, v, tr)
    s = stats(c, ctx['ndays'])
    nm = _C['nmin']
    if s['n'] >= nm and s['r_moyen'] > 0:
        s.update(O.note_tradeify(c, TAILLES_MC, N_SIM_MC))
    else:
        s.update(p_reussite=np.nan, p_payout=np.nan, ve=np.nan, micros=0)
    return v, tr, s


def _eval_ref(v):
    """Références : sans biais (a) et au hasard dans le sens du biais (b : espérance exacte, déjà dans pw/pr)."""
    ctx = _C[vd(v)['ut']]
    tr = trades_v(ctx, v, avec_biais=False)
    c = rassembler(ctx, v, tr, avec_biais=False)
    s = stats(c, ctx['ndays'])
    if s['n'] >= _C['nmin'] and s['r_moyen'] > 0:
        s.update(O.note_tradeify(c, TAILLES_MC, N_SIM_MC))
    else:
        s.update(p_reussite=np.nan, p_payout=np.nan, ve=np.nan, micros=0)
    return v, s


def _eval_pli(args):
    v, tr, blocs = args
    ctx = _C[vd(v)['ut']]
    c = rassembler(ctx, v, tr, blocs)
    return v, O.note_tradeify(c, TAILLES_WF, N_SIM_WF)


def pool():
    return mp.get_context('fork').Pool(NPROC)


# ═════════════════════════ RÈGLE DE CHOIX ═════════════════════════
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


def choisir(S, nm, k=3, tiers=(1, 2, 3)):
    for tier in tiers:
        cand = sorted([(score_lisse(S, v, nm)[0], v) for v, s in S.items() if eligible(s, nm, tier)], key=lambda x: -x[0])
        if cand:
            return tier, cand
    return 0, []


def distinctes(S, cand, k=3):
    vus = set(); out = []
    for sc, v in cand:
        s = S[v]
        cle = (s['n'], round(s['r_moyen'], 6), round(s['net_usd'], 2), vd(v)['ut'])
        if cle in vus:
            continue
        vus.add(cle); out.append((sc, v))
        if len(out) >= k:
            break
    return out


# ═════════════════════════ PINE ═════════════════════════
def ligne_pine(v, micros):
    d = vd(v); un = d['trig'] == 'union'
    kv = dict(bias=1, bF='%g' % d['bF'], bI='%g' % d['bI'], sens='Les deux', sig=1, sigNiv='Fort + Moyen',
              hei=int(un), tl=int(un), lvl=int(un), clx=int(un), div=0, tr=0, feu=0, ema=0, adx=0,
              lvl_=None, det=int(d['qual'] != 'aucune'), detK='%g' % DETK, clxF=int(d['qual'] == 'det+clx'), bo=0,
              maxJour=0, be=0, trail='Aucun', oppArr=0, oppHei=0, fin=0, part=0, hr=1, hr1On=1, hr1='0020-2215', hr2On=0,
              stop='ATR × k', atrK='%g' % STOP, tp='En R', tpR='%g' % d['obj'], tBar=SORTIE, pf=1,
              taille='Contrats fixes', fixe=int(max(1, micros)))
    kv = {k: x for k, x in kv.items() if x is not None}
    return ';'.join('%s=%s' % (k, x) for k, x in kv.items())


def nom_preset(v, rang):
    d = vd(v)
    q = {'aucune': 'sans filtre', 'det': 'Detector 1,5', 'det+clx': 'Detector 1,5 + climax'}[d['qual']]
    return '%d BIA-%d biais F%g I%g · %s · %s · %gR · %d min' % (
        40 + rang - 1, rang, d['bF'], d['bI'], 'Signator F+M' if d['trig'] == 'sig' else 'union', q, d['obj'], d['ut'])


# ═════════════════════════ PROGRAMME ═════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', choices=('cache', 'dataset'), default='cache')
    ap.add_argument('--recalcul', action='store_true')
    ap.add_argument('--registre', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    nm = n_min(a.source)
    flex = SIM.charge_regles()['tradeify_50k_select_flex']
    O._G['flex'] = flex
    for ut in UTS:
        c = construire_ctx(a.source, ut, a.recalcul)
        if c is not None:
            _C[ut] = c
            print('unité %d min : %s | %d jours' % (ut, ', '.join('%s %d barres %s->%s' % (
                j['nom'], len(j['df']), j['df'].index[0].date(), j['df'].index[-1].date()) for j in c['jeux']), c['ndays']), flush=True)
    _C['nmin'] = nm
    dispo = [ut for ut in UTS if ut in _C]
    cles = [v for v in toutes() if vd(v)['ut'] in dispo]
    print('%d variantes (grille fixée : %d) ; N_MIN=%d' % (len(cles), len(toutes()), nm), flush=True)

    # --- votes : résumé de couverture (à écrire dans RESULTATS.md)
    cov = []
    for ut in dispo:
        for ji, pm in enumerate(_C[ut]['PM']):
            Vt = pm['votes']
            z = (Vt.drop(columns=['F', 'I']) == 0).mean()
            cov.append('%s : F moyen %+.2f, I moyen %+.2f ; votes à 0 : %s' % (
                _C[ut]['jeux'][ji]['nom'], Vt['F'].mean(), Vt['I'].mean(),
                ', '.join('%s %.0f%%' % (k, 100 * x) for k, x in z.items() if x > 0.3)))
    # --- balayage
    S, TR = {}, {}
    with pool() as p:
        for v, tr, s in p.imap_unordered(_eval, cles, chunksize=4):
            S[v] = s; TR[v] = tr
    print('balayage + Tradeify : %.0f s' % (time.time() - t0), flush=True)
    tier, cand = choisir(S, nm)
    top = distinctes(S, cand, 3)
    print('palier de la règle : %d (1 = règle complète) ; %d candidates ; éligibles palier 1 : %d' % (
        tier, len(cand), sum(eligible(s, nm, 1) for s in S.values())), flush=True)

    # --- références (a) sans biais, (b) hasard dans le biais, pour toutes les variantes
    cles_ref = sorted({(v[2], v[3], v[4], v[5]) for v in cles})
    REF = {}
    with pool() as p:
        for v, s in p.imap_unordered(_eval_ref, [(0.0, 0.0, t, q, o, u) for (t, q, o, u) in cles_ref], chunksize=2):
            REF[(v[2], v[3], v[4], v[5])] = s

    # --- CSV complet
    lignes = []
    for v in cles:
        s = S[v]; sc, nv = score_lisse(S, v, nm)
        r = REF[(v[2], v[3], v[4], v[5])]
        lignes.append(dict(variante=libelle(v), **vd(v), **{k: s[k] for k in (
            'n', 'tpd', 'gagnants', 'r_moyen', 'pf', 'net_usd', 'plac_gagnants', 'plac_r', 'ecart_pts', 'z_ecart', 'ecart_r',
            'p_reussite', 'p_payout', 've', 'micros')}, score_lisse=sc, eligible1=bool(eligible(s, nm, 1)),
            eligible2=bool(eligible(s, nm, 2)), sans_biais_n=r['n'], sans_biais_tpd=r['tpd'], sans_biais_gagnants=r['gagnants'],
            sans_biais_r=r['r_moyen'], sans_biais_pf=r['pf'], sans_biais_ve=r.get('ve')))
    CSV = pd.DataFrame(lignes).sort_values('score_lisse', ascending=False)
    CSV.to_csv(os.path.join(SORTIES, 'balayage_%s.csv.gz' % a.source), index=False, float_format='%.5g')

    # --- agrégats utiles : le biais apporte-t-il ? (a) ; les déclencheurs apportent-ils ? (b)
    ok = CSV[CSV['n'] >= nm]
    out = []
    out.append('SOURCE %s | %d variantes | n_min %d | palier de la règle %d' % (a.source, len(cles), nm, tier))
    out.append('COUVERTURE DES VOTES (cache) :\n  ' + '\n  '.join(cov))
    out.append('LIMITES DU CACHE :\n  ' + '\n  '.join(VT.LIMITES_CACHE if a.source == 'cache' else ['(aucune : colonnes DATASET lues)']))
    if len(ok):
        d_taux = (ok['gagnants'] - ok['sans_biais_gagnants']).dropna()
        d_r = (ok['r_moyen'] - ok['sans_biais_r']).dropna()
        d_plr = (ok['r_moyen'] - ok['plac_r']).dropna()
        d_plw = (ok['gagnants'] - ok['plac_gagnants']).dropna()
        out.append('(a) AVEC biais - SANS biais (variantes n>=%d, %d) : taux %+.1f pts en moyenne (%.0f %% des variantes mieux), '
                   'R %+.3f (%.0f %% mieux)' % (nm, len(ok), 100 * d_taux.mean(), 100 * (d_taux > 0).mean(), d_r.mean(), 100 * (d_r > 0).mean()))
        out.append('(b) déclencheurs - hasard dans le sens du biais : taux %+.1f pts (%.0f %% des variantes mieux), R %+.3f (%.0f %% mieux)' % (
            100 * d_plw.mean(), 100 * (d_plw > 0).mean(), d_plr.mean(), 100 * (d_plr > 0).mean()))
        for ut in dispo:
            o2 = ok[ok['ut'] == ut]
            if len(o2):
                out.append('   %d min : n moyen %.0f, trades/jour moyen %.2f, gagnants %.1f %%, R %+.3f ; sans biais : %.2f /jour, %.1f %%, R %+.3f ; '
                           'hasard-biais : %.1f %%, R %+.3f' % (
                               ut, o2['n'].mean(), o2['tpd'].mean(), 100 * o2['gagnants'].mean(), o2['r_moyen'].mean(),
                               o2['sans_biais_tpd'].mean(), 100 * o2['sans_biais_gagnants'].mean(), o2['sans_biais_r'].mean(),
                               100 * o2['plac_gagnants'].mean(), o2['plac_r'].mean()))
    # --- (c) préréglage 25, fenêtre 00:20-22:15 (15 min)
    ref25 = None
    if 15 in _C:
        c15 = _C[15]
        g25 = (BASE25['stop'], BASE25['obj'], BASE25['sortie'], BASE25['be'])
        tr25 = []
        for ji, pm in enumerate(c15['PM']):
            a_ = B.declencheur(pm['df'], 'tous')
            dt = B._det(BASE25['det'])(pm['df'])
            m_ = pm['df']['min_paris'].to_numpy()
            h_ = (m_ >= 930) & (m_ < FEN_FIN) & (m_ + 15 < FEN_FIN)
            tr = pm['tr240']
            Lm = a_[0] & np.asarray(dt[0], bool) & np.asarray(tr[0], bool) & h_
            Sm = a_[1] & np.asarray(dt[1], bool) & np.asarray(tr[1], bool) & h_
            # table obj=1 existe (GEOMS contient (2,1,8,0))
            idx, sens = TB.trades_table(c15['T'][(ji, g25)], Lm, Sm)
            tr25.append((ji, idx, sens))
        v25 = (0.0, 0.0, 'union', 'aucune', 1.0, 15)
        c25 = rassembler(c15, v25, tr25, avec_biais=False)
        ref25 = stats(c25, c15['ndays'])
        ref25.update(O.note_tradeify(c25, TAILLES_MC, N_SIM_MC))
        out.append('(c) PRÉRÉGLAGE 25 (fenêtre 00:20-22:15, 15 min) : n=%d (%.2f /jour) gagnants %.1f %% R %+.3f PF %.2f | P(réussite)=%s VE=%s (%s micros)' % (
            ref25['n'], ref25['tpd'], 100 * ref25['gagnants'], ref25['r_moyen'], ref25['pf'], ref25['p_reussite'], ref25['ve'], ref25['micros']))

    # --- bootstrap de White (r brut, et r - hasard dans le biais)
    jours_id = {}
    for ut in dispo:
        for ji, pm in enumerate(_C[ut]['PM']):
            for jr in np.unique(pm['jour']):
                jours_id[(ut, ji, int(jr))] = len(jours_id)
    ND = len(jours_id)
    Vw = [v for v in cles if S[v]['n'] >= 10]
    X = np.zeros((len(Vw), ND), np.float32); XP = np.zeros((len(Vw), ND), np.float32)
    for q, v in enumerate(Vw):
        ut = vd(v)['ut']; c = rassembler(_C[ut], v, TR[v])
        di = np.array([jours_id[(ut, int(j), int(jr))] for j, jr in zip(c['jeu'], c['jour'])], int)
        np.add.at(X[q], di, c['r']); np.add.at(XP[q], di, c['r'] - c['pr'])
    tR, pR, pR_best, _ = AN.white(X, n_boot=1000, graine=1)
    tP, pP, pP_best, _ = AN.white(XP, n_boot=1000, graine=2)
    pos = {v: q for q, v in enumerate(Vw)}
    out.append('WHITE (%d variantes n>=10, %d jours) : meilleure t(R brut)=%.2f p=%.2f ; meilleure t(R - hasard-dans-le-biais)=%.2f p=%.2f' % (
        len(Vw), ND, tR.max(), pR_best, tP.max(), pP_best))

    # --- walk-forward (la règle complète, avec repli de palier ; choix sur 3 blocs, test sur le suivant)
    wf = []
    nm_pli = max(8, int(round(nm * RATIO / (RATIO + K_PLIS))))
    ndays_pli = {ut: _C[ut]['ndays'] * RATIO / (RATIO + K_PLIS) for ut in dispo}
    for p_ in range(K_PLIS):
        app = list(range(p_, p_ + RATIO)); tst = [p_ + RATIO]
        Sp = {}
        for v in cles:
            c = rassembler(_C[vd(v)['ut']], v, TR[v], app)
            Sp[v] = stats(c, ndays_pli[vd(v)['ut']]); Sp[v].update(p_reussite=np.nan, p_payout=np.nan, ve=np.nan, micros=0)
        todo = [(v, TR[v], app) for v in cles if Sp[v]['n'] >= nm_pli and Sp[v]['r_moyen'] > 0]
        with pool() as pl:
            for v, nt in pl.imap_unordered(_eval_pli, todo, chunksize=4):
                Sp[v].update(nt)
        tp, ch = choisir(Sp, nm_pli)
        if not ch:
            wf.append(dict(pli=p_, choix=None)); continue
        v = ch[0][1]
        ct = rassembler(_C[vd(v)['ut']], v, TR[v], tst); st = stats(ct)
        wf.append(dict(pli=p_, choix=libelle(v), palier=tp, app_n=Sp[v]['n'], app_g=Sp[v]['gagnants'], app_r=Sp[v]['r_moyen'], test=st, ct=ct))
    pool_wf = {k: np.concatenate([w['ct'][k] for w in wf if w.get('ct') is not None and len(w['ct']['pnl'])] or [np.zeros(0)])
               for k in ('pnl', 'r', 'pw', 'pr')}
    sw = stats(pool_wf)
    out.append('WALK-FORWARD (%d plis) : n=%d gagnants %s (hasard-biais %s) R %s PF %s net %s $ (1 micro)' % (
        K_PLIS, sw['n'], '%.1f %%' % (100 * sw['gagnants']) if sw['n'] else 'n/a',
        '%.1f %%' % (100 * sw['plac_gagnants']) if sw['n'] else 'n/a', '%+.3f' % sw['r_moyen'] if sw['n'] else 'n/a',
        '%.2f' % sw['pf'] if sw['n'] else 'n/a', '%+.0f' % sw['net_usd']))
    for w in wf:
        if w.get('choix'):
            t = w['test']
            out.append('   pli %d (palier %d) : %s | appr. %d tr. %.0f %% R %+.2f | test %d tr. %s R %s' % (
                w['pli'], w['palier'], w['choix'], w['app_n'], 100 * w['app_g'], w['app_r'], t['n'],
                '%.0f %%' % (100 * t['gagnants']) if t['n'] else '-', '%+.2f' % t['r_moyen'] if t['n'] else '-'))
        else:
            out.append('   pli %d : aucune variante éligible à l\'apprentissage' % w['pli'])

    # --- top 3 : détail, vérification moteur, Pine
    pine = []; verifs = []; best = None; trades_top = []
    for rang, (sc, v) in enumerate(top, 1):
        s = S[v]; d = vd(v); ctx = _C[d['ut']]
        g = (STOP, d['obj'], SORTIE, 0)
        Tm = []
        for ji, j in enumerate(ctx['jeux']):
            L, Sg = masques(ctx, ji, v)
            t = M.backtest(j['df'], long=L, short=Sg, gestion=O.gestion(j['instrument'], g))
            t['jeu'] = j['nom']; Tm.append(t)
        Tm = pd.concat(Tm, ignore_index=True).sort_values('entree_t').reset_index(drop=True)
        okm = (len(Tm) == s['n']) and abs(Tm['r'].sum() - s['r_moyen'] * s['n']) < 1e-6 * max(1, s['n'])
        verifs.append(okm); trades_top.append(Tm.drop(columns=['jeu']))
        r = REF[(v[2], v[3], v[4], v[5])]
        q = pos.get(v); wp = (pR[q], pP[q]) if q is not None else (np.nan, np.nan)
        c = rassembler(ctx, v, TR[v])
        tt = (c['r'] - c['pr']); pval = float(1 - __import__('scipy.stats', fromlist=['t']).t.cdf(tt.mean() / (tt.std(ddof=1) / np.sqrt(len(tt))), len(tt) - 1)) if len(tt) > 2 else np.nan
        out.append('\n#%d %s\n   n=%d (%.2f /jour) gagnants %.1f %% R %+.3f PF %.2f net %+.0f $/micro\n'
                   '   (a) SANS biais : n=%d (%.2f /jour) gagnants %.1f %% R %+.3f PF %.2f VE=%s\n'
                   '   (b) HASARD dans le sens du biais : gagnants %.1f %% R %+.3f | écart déclencheurs : %+.1f pts, %+.3f R (z=%.1f, p(R)=%.2f)\n'
                   '   Tradeify Select Flex : %d micros P(réussite)=%.2f P(1er payout)=%.2f VE=%+.0f $ | score lissé %+.0f $ (%d voisines) | White p: R brut %.2f, vs hasard %.2f | moteur=%s' % (
                       rang, libelle(v), s['n'], s['tpd'], 100 * s['gagnants'], s['r_moyen'], s['pf'], s['net_usd'],
                       r['n'], r['tpd'], 100 * r['gagnants'] if r['n'] else float('nan'), r['r_moyen'] if r['n'] else float('nan'),
                       r['pf'] if r['n'] else float('nan'), r.get('ve'),
                       100 * s['plac_gagnants'], s['plac_r'], s['ecart_pts'], s['ecart_r'], s['z_ecart'], pval,
                       s['micros'], s['p_reussite'], s['p_payout'], s['ve'], sc, score_lisse(S, v, nm)[1], wp[0], wp[1],
                       'identique' if okm else 'ÉCART'))
        pine.append((nom_preset(v, rang), ligne_pine(v, s['micros']), v, s))
        if rang == 1:
            best = (v, s, sc, pval)
    if not top:
        out.append('\nAUCUNE variante ne passe même le dernier palier de la règle.')
    txt = '\n'.join(out)
    open(os.path.join(SORTIES, 'resume_%s.txt' % a.source), 'w').write(txt + '\n')
    print('\n' + txt, flush=True)

    with open(os.path.join(ICI, 'presets_pine.txt'), 'w') as fh:
        fh.write('// Biais global (BIA), source %s, %s. 3 meilleures lignes pour f_pr_def() de STRATEGIE_V1.pine.\n' % (
            a.source, pd.Timestamp.now(tz='Europe/Paris').strftime('%d/%m/%Y %H:%M')))
        fh.write('// Palier de la règle : %d (1 = règle complète : >= 1 trade/jour, >= 55 %% gagnants, R > 0 ; 2 = sans le >= 1/jour ; 3 = sans le 55 %%).\n' % tier)
        fh.write('// Ajouter chaque nom EXACT dans options=[...] du menu « Préréglage », puis coller la ligne dans f_pr_def().\n')
        fh.write('// Fenêtre 00:20-22:15 Paris via hr1 ; « Niveaux mesurés sur » = Vrais prix (lvl). UNITÉ DU GRAPHIQUE à régler à la main (voir chaque commentaire).\n')
        fh.write('// REJETÉ si la source est le cache (2 mois) : à passer au testeur sur 3 ans, pas à trader.\n\n')
        if not pine:
            fh.write('// Aucune variante éligible.\n')
        for nom, pl, v, s in pine:
            fh.write('// %s | n=%d (%.2f/jour) gagnants %.0f %% R %+.2f PF %.2f | %d micros P=%.2f VE=%+.0f $ | GRAPHIQUE %d MIN\n' % (
                libelle(v), s['n'], s['tpd'], 100 * s['gagnants'], s['r_moyen'], s['pf'], s['micros'], s['p_reussite'], s['ve'], vd(v)['ut']))
            fh.write('     nom == "%s" ? "%s" :\n\n' % (nom, pl))

    if a.registre and top:
        for rang, (sc, v) in enumerate(top, 1):
            s = S[v]
            verdict = ('essai à blanc %s : %s | palier %d | %.2f trades/jour, hasard-dans-le-biais %.0f %% R %+.2f | sans biais %.0f %% R %+.2f | '
                       'walk-forward n=%d %.0f %% R %+.2f | White p(R brut)=%.2f ; VE Tradeify %+.0f $ (%d micros) ; moteur %s' % (
                           a.source, 'NON CONCLUANT (2 mois)' if a.source == 'cache' else 'à juger', tier, s['tpd'],
                           100 * s['plac_gagnants'], s['plac_r'],
                           100 * REF[(v[2], v[3], v[4], v[5])]['gagnants'], REF[(v[2], v[3], v[4], v[5])]['r_moyen'],
                           sw['n'], 100 * sw['gagnants'] if sw['n'] else float('nan'), sw['r_moyen'] if sw['n'] else float('nan'),
                           pR_best, s['ve'], s['micros'], 'identique' if verifs[rang - 1] else 'ÉCART'))
            idr = RG.ajouter_test(dict(agent='BIA', famille='biais-global', recette=libelle(v) + ' | 2 ATR, 8 bougies, 00:20-22:15',
                                       marche='MES+MNQ (micros)', ut_signal=str(vd(v)['ut']), ut_entree=str(vd(v)['ut']),
                                       echantillon='dev_%s' % a.source, n_variantes_testees=len(cles), p_tradeify=s['p_reussite'],
                                       p_ref_hasard='', verdict=verdict, trades=trades_top[rang - 1]), prefixe='BIA')
            print('registre :', idr)
    print('terminé en %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
