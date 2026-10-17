"""Optimiseur 25 (OPT) : voisinage du préréglage 25 (WRX-0001), fenêtre 00:20-22:15 Paris, note Tradeify.

    ~/venv-quant/bin/python optimiser.py --source cache      # essai à blanc (2 mois)
    ~/venv-quant/bin/python optimiser.py --source dataset    # dès que le DATASET 15 min est exporté

Une seule commande : charge les données (UNE fonction, `charger`), construit les tables d'issues (moteur commun,
réglages de ce balayage), explore ~2 500 variantes, note chacune (stats, placebo exact de même géométrie,
simulateur Tradeify Select Flex), applique la règle de choix FIXÉE À L'AVANCE (voir REGLE), fait le
walk-forward et le bootstrap de White, puis écrit sorties/ et presets_pine.txt.

RÈGLE DE CHOIX (fixée avant de regarder les résultats) :
  éligible = gagnants >= 55 %, R moyen > 0, n >= N_MIN (30 sur le cache, 80 sur le DATASET) ;
  score = moyenne de la valeur espérée Tradeify de la variante ET de ses voisines à un pas sur un réglage
          (une voisine à R <= 0 ou n < N_MIN compte 0) ; on prend le meilleur score, pas le meilleur isolé.
Tables : celles de taux_combinatoire/tables.py ne couvrent pas ces réglages (stop 2,5, objectif 1,25 / 2,
sortie 4 / 12 bougies, BE + 4 ticks, sortie 22:15) : on en refait ici avec le MÊME procédé (moteur.backtest un
signal toutes les K barres) ; trades_table / glouton / placebo_moyen sont ceux de taux_combinatoire, importés.
Vérification : les 3 retenues sont rejouées directement par le moteur (mêmes n et R).
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
WRX = os.path.abspath(os.path.join(ICI, '..', 'taux_combinatoire'))
sys.path.insert(0, WRX)
import bib_wrx as B  # noqa: E402
import donnees_wrx as D  # noqa: E402
import tables as TB  # noqa: E402  (trades_table : glouton "une position à la fois")
import analyse as AN  # noqa: E402  (white)

M = D.M
sys.path.insert(0, os.path.join(D.SB, 'propfirm'))
sys.path.insert(0, os.path.join(D.SB, 'moteur'))
import simulateur as SIM  # noqa: E402
import registre as RG  # noqa: E402

SORTIES = os.path.join(ICI, 'sorties')
os.makedirs(SORTIES, exist_ok=True)
NPROC = max(1, min(8, (os.cpu_count() or 2) - 1))
UT = 15

# ════════════════════════════════════════════════════════════════════════════════════════
# RÉGLAGES DU BALAYAGE
# ════════════════════════════════════════════════════════════════════════════════════════
FEN_DEBUT, FEN_FIN = 20, 22 * 60 + 15          # 00:20 -> 22:15 Paris
AXES = {
    'decl': ['sig_fort', 'hei_flip', 'tl', 'lvl', 'clx', 'tous'],
    'tr': [0, 60, 240],
    'det': [0, 1.0, 1.5, 2.0, 2.5],
    'feu': [0, 50, 60],
    'hr': ['tout', '0900', '1530', 'nuit'],
    'stop': [1.5, 2.0, 2.5, 3.0],
    'obj': [0.75, 1.0, 1.25, 1.5, 2.0],
    'sortie': [0, 4, 8, 12],
    'be': [0, 1],
}
ORDRE = list(AXES)
BASE = dict(decl='tous', tr=240, det=2.0, feu=0, hr='1530', stop=2.0, obj=1.0, sortie=8, be=0)   # préréglage 25
HR_TXT = {'tout': '0020-2215', '0900': '0900-2215', '1530': '1530-2215', 'nuit': '0020-0800'}
HR_MIN = {'tout': (FEN_DEBUT, FEN_FIN), '0900': (540, FEN_FIN), '1530': (930, FEN_FIN), 'nuit': (FEN_DEBUT, 480)}
HR_VOIS = {'tout': ['0900', '1530', 'nuit'], '0900': ['tout', '1530'], '1530': ['tout', '0900'], 'nuit': ['tout']}
MAX_CHANGEMENTS = 3
BE_R, BE_TICKS = 0.5, 4
GEOMS = [(s, o, x, b) for s in AXES['stop'] for o in AXES['obj'] for x in AXES['sortie'] for b in AXES['be']]

GAGNANTS_MIN = 0.55
TAILLES_MC = [1, 2, 3, 4, 6, 8, 10]
TAILLES_WF = [1, 2, 4, 6]
N_SIM_MC, N_SIM_WF = 300, 200
K_PLIS, RATIO = 4, 3
N_BOOT_WHITE = 1000


def n_min(source):
    return 80 if source == 'dataset' else 30


# ════════════════════════════════════════════════════════════════════════════════════════
# 1. DONNÉES (UNE fonction ; --source cache|dataset)
# ════════════════════════════════════════════════════════════════════════════════════════
def charger(source):
    """Jeux 15 min (développement seulement, scellé fermé) avec colonnes WRX. Seul point d'accès aux données."""
    return D.charger_jeux(source, uts=(UT,))


# ════════════════════════════════════════════════════════════════════════════════════════
# 2. TABLES D'ISSUES (fenêtre 22:15, BE + 4 ticks, sortie après N bougies)
# ════════════════════════════════════════════════════════════════════════════════════════
def gestion(instrument, g):
    s, o, x, b = g
    G = dict(instrument=instrument, stop={'mode': 'atr', 'k': s}, objectif={'mode': 'R', 'k': o},
             heure_sortie='22:15', fuseau_sortie='Europe/Paris', heure_reprise='00:20')
    if b:
        G['break_even'] = {'R': BE_R, 'ticks': BE_TICKS}
    if x:
        G['sortie_barres'] = int(x)
    return G


def table_issues(df, instrument, g):
    n = len(df)
    G = gestion(instrument, g)
    K = int(1440 // UT) + 3
    ar = np.arange(n)
    z = lambda t=float: np.zeros((2, n), t)  # noqa: E731
    ok = z(bool); r = z(); pnl = z(); kl = z(np.int64); mae = z(); mfe = z(); risq = z()
    ent = z(np.int64); sor = z(np.int64)
    for di, cle in enumerate(('long', 'short')):
        for dec in range(K):
            sig = (ar % K) == dec
            T = M.backtest(df, **{cle: sig}, gestion=G, details=True)
            if not len(T):
                continue
            i = T['i_signal'].to_numpy(); ke = T['k_entree'].to_numpy(); ks = T['k_sortie'].to_numpy()
            ouv = T['barres'].to_numpy() == (ks - ke)
            ok[di, i] = True
            r[di, i] = T['r'].to_numpy(); pnl[di, i] = T['pnl_usd'].to_numpy()
            mae[di, i] = T['mae_usd'].to_numpy(); mfe[di, i] = T['mfe_usd'].to_numpy()
            risq[di, i] = T['risque_usd'].to_numpy()
            ent[di, i] = pd.DatetimeIndex(T['entree_t']).tz_convert('UTC').as_unit('ns').asi8
            sor[di, i] = pd.DatetimeIndex(T['sortie_t']).tz_convert('UTC').as_unit('ns').asi8
            kl[di, i] = np.where(ouv, ks - 1, ks)
    b = M.barres(df)
    heure = pd.DatetimeIndex(pd.to_datetime(b.t_clo, unit='ns', utc=True)).tz_convert('Europe/Paris').hour.to_numpy()
    return dict(ok=ok, gagne=pnl > 0, r=r, pnl=pnl, klibre=kl, mae=mae, mfe=mfe, risque=risq, ent=ent, sor=sor,
                heure=heure, jour=b.jour_cme())


_G = {}          # état partagé avec les processus fils (fork)


def _travail_table(args):
    ji, g = args
    j = _G['jeux'][ji]
    return ji, g, table_issues(j['df'], j['instrument'], g)


def pool():
    return mp.get_context('fork').Pool(NPROC)


def construire_tables(jeux, source, recalcul=False):
    chemin = os.path.join(SORTIES, 'tables_%s.pkl' % source)
    sig = [(j['nom'], len(j['df']), str(j['df'].index[0]), str(j['df'].index[-1])) for j in jeux]
    if os.path.exists(chemin) and not recalcul:
        with open(chemin, 'rb') as fh:
            obj = pickle.load(fh)
        if obj.get('sig') == sig and obj.get('geoms') == GEOMS:
            print('tables : relues (%s)' % chemin, flush=True)
            return obj['T']
    _G['jeux'] = jeux
    t0 = time.time()
    taches = [(ji, g) for ji in range(len(jeux)) for g in GEOMS]
    T = {}
    with pool() as p:
        for ji, g, tab in p.imap_unordered(_travail_table, taches, chunksize=2):
            T[(ji, g)] = tab
    print('tables : %d en %.0f s' % (len(T), time.time() - t0), flush=True)
    with open(chemin, 'wb') as fh:
        pickle.dump(dict(sig=sig, geoms=GEOMS, T=T), fh)
    return T


# ════════════════════════════════════════════════════════════════════════════════════════
# 3. MASQUES, VARIANTES, TRADES
# ════════════════════════════════════════════════════════════════════════════════════════
def preparer(jeux):
    """Par jeu : masques (L, S) de chaque modalité de chaque réglage ; fenêtre ; blocs de walk-forward."""
    PM = []
    for j in jeux:
        df = j['df']; n = len(df)
        dec = {k: B.declencheur(df, k) for k in B.DECLENCHEURS}
        tout = (np.ones(n, bool), np.ones(n, bool))
        tr = {0: tout}
        for u in (60, 240):
            f = B._trend('trend_%d' % u)(df)
            tr[u] = tout if f is None else (np.asarray(f[0], bool), np.asarray(f[1], bool))
        det = {0: tout}
        for k in AXES['det'][1:]:
            f = B._det(k)(df); det[k] = (np.asarray(f[0], bool), np.asarray(f[1], bool))
        feu = {0: tout}
        for s in (50, 60):
            f = B._feu(s)(df); feu[s] = (np.asarray(f[0], bool), np.asarray(f[1], bool))
        m = df['min_paris'].to_numpy()           # ouverture de la bougie signal ; la bougie qui finit >= 22:15 est refusée
        hr = {}
        for h, (a, b) in HR_MIN.items():
            ok = (m >= a) & (m < b) & (m + UT < FEN_FIN)
            hr[h] = (ok, ok)
        # jours -> blocs de walk-forward (ratio + k blocs de journées CME consécutives)
        jr = M.barres(df).jour_cme()
        uj = np.unique(jr)
        nb = RATIO + K_PLIS
        bornes = np.linspace(0, len(uj), nb + 1).round().astype(int)
        blk = np.zeros(n, np.int64)
        for q in range(nb):
            blk[np.isin(jr, uj[bornes[q]:bornes[q + 1]])] = q
        PM.append(dict(dec=dec, tr=tr, det=det, feu=feu, hr=hr, blk=blk, jour=jr))
    return PM


def decalages(jeux):
    """Les jeux sont posés bout à bout dans le temps (multiples de 7 jours : jours de semaine conservés), pour
    que le simulateur voie UN compte qui trade un instrument à la fois, sans trou de plusieurs mois ni doublon."""
    ordre = sorted(range(len(jeux)), key=lambda i: jeux[i]['df'].index[0])
    off = {}; fin_prec = None
    for i in ordre:
        d0 = jeux[i]['df'].index[0].tz_convert('UTC'); d1 = jeux[i]['df'].index[-1].tz_convert('UTC')
        if fin_prec is None:
            o = pd.Timedelta(0)
        else:
            sem = int(np.ceil((fin_prec + pd.Timedelta(days=2) - d0) / pd.Timedelta(days=7)))
            o = pd.Timedelta(days=7 * sem)
        off[i] = int(o.value)
        fin_prec = d1 + o
    return off


def voisines(v):
    """Voisines à un pas sur un réglage (ordinaux : ±1 cran ; déclencheur : union <-> chacun ; plage : graphe)."""
    out = []
    for a in ORDRE:
        val = v[a]
        if a == 'decl':
            cand = [x for x in AXES[a] if x != 'tous'] if val == 'tous' else ['tous']
        elif a == 'hr':
            cand = HR_VOIS[val]
        else:
            k = AXES[a].index(val)
            cand = [AXES[a][q] for q in (k - 1, k + 1) if 0 <= q < len(AXES[a])]
        for c in cand:
            w = dict(v); w[a] = c
            out.append(tuple(w[x] for x in ORDRE))
    return out


def toutes_variantes():
    cles = []
    for combo in itertools.product(*[AXES[a] for a in ORDRE]):
        if sum(combo[i] != BASE[a] for i, a in enumerate(ORDRE)) <= MAX_CHANGEMENTS:
            cles.append(combo)
    return cles


def vdict(v):
    return dict(zip(ORDRE, v))


def trades_variante(v):
    """[(jeu, idx, sens)] : trades de la variante sur chaque jeu (règle « une position à la fois »)."""
    d = vdict(v)
    g = (d['stop'], d['obj'], d['sortie'], d['be'])
    out = []
    for ji, pm in enumerate(_G['PM']):
        a = pm['dec'][d['decl']]
        L = a[0] & pm['tr'][d['tr']][0] & pm['det'][d['det']][0] & pm['feu'][d['feu']][0] & pm['hr'][d['hr']][0]
        S = a[1] & pm['tr'][d['tr']][1] & pm['det'][d['det']][1] & pm['feu'][d['feu']][1] & pm['hr'][d['hr']][1]
        idx, sens = TB.trades_table(_G['T'][(ji, g)], L, S)
        out.append((ji, idx, sens))
    return out


def rassembler(v, tr, blocs=None):
    """Colonnes des trades d'une variante (tous jeux), éventuellement restreints à des blocs de walk-forward."""
    d = vdict(v)
    g = (d['stop'], d['obj'], d['sortie'], d['be'])
    cols = {k: [] for k in ('jeu', 'jour', 'pnl', 'r', 'pw', 'pr', 'ent', 'sor', 'mae', 'mfe', 'risque', 'sens', 'bar')}
    for ji, idx, sens in tr:
        if not len(idx):
            continue
        tab = _G['T'][(ji, g)]
        if blocs is not None:
            m = np.isin(_G['PM'][ji]['blk'][idx], blocs)
            idx, sens = idx[m], sens[m]
            if not len(idx):
                continue
        pw, pr, _ = _G['PLAC'][(ji, g)]
        h = tab['heure'][idx]
        cols['jeu'].append(np.full(len(idx), ji)); cols['jour'].append(_G['PM'][ji]['jour'][idx])
        cols['pnl'].append(tab['pnl'][sens, idx]); cols['r'].append(tab['r'][sens, idx])
        cols['pw'].append(pw[sens, h]); cols['pr'].append(pr[sens, h])
        cols['ent'].append(tab['ent'][sens, idx] + _G['OFF'][ji]); cols['sor'].append(tab['sor'][sens, idx] + _G['OFF'][ji])
        cols['mae'].append(tab['mae'][sens, idx]); cols['mfe'].append(tab['mfe'][sens, idx])
        cols['risque'].append(tab['risque'][sens, idx]); cols['sens'].append(sens); cols['bar'].append(idx)
    return {k: (np.concatenate(x) if x else np.zeros(0)) for k, x in cols.items()}


def stats(c):
    n = len(c['pnl'])
    if n == 0:
        return dict(n=0, gagnants=np.nan, r_moyen=np.nan, pf=np.nan, net_usd=0.0, plac_gagnants=np.nan,
                    plac_r=np.nan, ecart_pts=np.nan, z_ecart=np.nan, ecart_r=np.nan)
    w = c['pnl'] > 0
    gain = c['pnl'][c['pnl'] > 0].sum(); perte = -c['pnl'][c['pnl'] < 0].sum()
    pw = c['pw']
    sd = np.sqrt((pw * (1 - pw)).sum())
    return dict(n=n, gagnants=w.mean(), r_moyen=c['r'].mean(), pf=gain / perte if perte > 0 else np.inf,
                net_usd=c['pnl'].sum(), plac_gagnants=pw.mean(), plac_r=c['pr'].mean(),
                ecart_pts=100 * (w.mean() - pw.mean()), z_ecart=(w.sum() - pw.sum()) / sd if sd > 0 else 0.0,
                ecart_r=c['r'].mean() - c['pr'].mean())


def df_trades(c):
    t = pd.DataFrame(dict(
        entree_t=pd.to_datetime(c['ent'], unit='ns', utc=True), sortie_t=pd.to_datetime(c['sor'], unit='ns', utc=True),
        sens=np.where(c['sens'] == 0, 'long', 'short'), r=c['r'], pnl_usd=c['pnl'], risque_usd=c['risque'],
        mae_usd=c['mae'], mfe_usd=c['mfe']))
    return t.sort_values('entree_t').reset_index(drop=True)


def note_tradeify(c, tailles, n_sim):
    """(P(réussite), P(1er payout), valeur espérée, micros) à la taille de plus forte valeur espérée."""
    if len(c['pnl']) < 5:
        return dict(p_reussite=np.nan, p_payout=np.nan, ve=np.nan, micros=0)
    try:
        tab, b = SIM.optimise_taille(df_trades(c), _G['flex'], tailles=tailles, critere='valeur_esperee',
                                     n_sim=n_sim, ordre='prudent')
    except Exception:
        return dict(p_reussite=np.nan, p_payout=np.nan, ve=np.nan, micros=0)
    if not b:
        return dict(p_reussite=np.nan, p_payout=np.nan, ve=np.nan, micros=0)
    return dict(p_reussite=b.get('p_reussite'), p_payout=b.get('p_1er_payout'), ve=b.get('valeur_esperee_usd'),
                micros=int(b.get('contrats', 1)))


def _eval(v):
    tr = trades_variante(v)
    c = rassembler(v, tr)
    s = stats(c)
    # Tradeify : seulement si la variante peut compter (R > 0 et n >= N_MIN) ; sinon valeur comptée 0 dans le lissage
    if s['n'] >= _G['nmin'] and s['r_moyen'] > 0:
        s.update(note_tradeify(c, TAILLES_MC, N_SIM_MC))
    else:
        s.update(p_reussite=np.nan, p_payout=np.nan, ve=np.nan, micros=0)
    return v, tr, s


def _eval_pli(args):
    """Note Tradeify de la variante sur les blocs d'apprentissage d'un pli."""
    v, tr, blocs = args
    c = rassembler(v, tr, blocs)
    return v, note_tradeify(c, TAILLES_WF, N_SIM_WF)


# ════════════════════════════════════════════════════════════════════════════════════════
# 4. RÈGLE DE CHOIX
# ════════════════════════════════════════════════════════════════════════════════════════
def ve_compte(S, v, nmin):
    """Valeur espérée comptée pour le lissage : 0 si R <= 0 ou n < nmin."""
    s = S.get(v)
    if s is None or not (s['n'] >= nmin and s['r_moyen'] > 0) or s.get('ve') is None or not np.isfinite(s['ve']):
        return 0.0
    return float(s['ve'])


def score_lisse(S, v, nmin):
    liste = [ve_compte(S, v, nmin)] + [ve_compte(S, w, nmin) for w in voisines_presentes(S, v)]
    return float(np.mean(liste)), len(liste) - 1


def voisines_presentes(S, v):
    return [w for w in voisines(vdict(v)) if w in S]


def eligible(s, nmin):
    return s['n'] >= nmin and s['gagnants'] >= GAGNANTS_MIN and s['r_moyen'] > 0


def choisir(S, nmin, k=1):
    cand = [(score_lisse(S, v, nmin)[0], v) for v, s in S.items() if eligible(s, nmin)]
    cand.sort(key=lambda x: -x[0])
    return cand[:k] if k else cand


def distinctes(S, tr, cand, k=3):
    """Les k premières sans doublon (mêmes trades) — évite 3 fois la même ligne."""
    vus = set(); out = []
    for sc, v in cand:
        s = S[v]
        cle = (s['n'], round(s['r_moyen'], 6), round(s['net_usd'], 2))
        if cle in vus:
            continue
        vus.add(cle); out.append((sc, v))
        if len(out) >= k:
            break
    return out


# ════════════════════════════════════════════════════════════════════════════════════════
# 5. PRÉRÉGLAGE PINE
# ════════════════════════════════════════════════════════════════════════════════════════
def ligne_pine(v, micros):
    d = vdict(v)
    on = set(B.TOUS) if d['decl'] == 'tous' else {d['decl']}
    kv = dict(sens='Les deux', clx=int('clx' in on), sig=int('sig_fort' in on), hei=int('hei_flip' in on),
              tl=int('tl' in on), lvl=int('lvl' in on), div=0,
              tr=int(d['tr'] > 0), tr4h=int(d['tr'] == 240), feu=int(d['feu'] > 0), ema=0, adx=0, det=int(d['det'] > 0),
              clxF=0, bo=0, maxJour=0, be=d['be'], trail='Aucun', oppArr=0, oppHei=0, fin=0, pf=1, part=0, hr=1,
              tBar=d['sortie'], taille='Contrats fixes')
    if 'sig_fort' in on:
        kv['sigNiv'] = 'Fort seulement'
    if d['feu']:
        kv['feuMode'] = 'Part dans le sens ≥ seuil'; kv['feuSeuil'] = d['feu']
    if d['det']:
        kv['detK'] = ('%g' % d['det'])
    if d['be']:
        kv['beR'] = BE_R; kv['beTk'] = BE_TICKS
    kv.update(hr1On=1, hr1=HR_TXT[d['hr']], hr2On=0)
    kv.update({'stop': 'ATR × k', 'atrK': '%g' % d['stop'], 'tp': 'En R', 'tpR': '%g' % d['obj'], 'fixe': int(max(1, micros))})
    return ';'.join('%s=%s' % (k, x) for k, x in kv.items())


def nom_preset(v, rang):
    d = vdict(v)
    decl = {'tous': 'tous', 'sig_fort': 'Signator', 'hei_flip': 'Heishi', 'tl': 'trendline', 'lvl': 'niveaux', 'clx': 'climax'}[d['decl']]
    f = []
    if d['tr']:
        f.append('TREND %s' % ('4h' if d['tr'] == 240 else '1h'))
    if d['det']:
        f.append('Detector %g' % d['det'])
    if d['feu']:
        f.append('Feu %d' % d['feu'])
    h = {'tout': '0h20-22h15', '0900': '9h-22h15', '1530': '15h30-22h15', 'nuit': '0h20-8h'}[d['hr']]
    tail = '%g ATR · %gR' % (d['stop'], d['obj']) + (' · %d bougies' % d['sortie'] if d['sortie'] else '') + (' · BE' if d['be'] else '')
    return ('%d OPT-%d %s · %s · %s · %s' % (37 + rang - 1, rang, decl, '+'.join(f) or 'sans filtre', h, tail)).replace(',', ',')


def libelle(v):
    d = vdict(v)
    return '%s | TREND %s | Detector %s | Feu %s | %s | SL %g | TP %gR | sortie %s | BE %s' % (
        d['decl'], d['tr'] or '-', d['det'] or '-', d['feu'] or '-', HR_TXT[d['hr']], d['stop'], d['obj'],
        d['sortie'] or '-', 'oui' if d['be'] else 'non')


# ════════════════════════════════════════════════════════════════════════════════════════
# 6. PROGRAMME
# ════════════════════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', choices=('cache', 'dataset'), default='cache')
    ap.add_argument('--recalcul', action='store_true', help='refaire les tables d\'issues')
    ap.add_argument('--registre', action='store_true', help='écrire la meilleure recette au registre (préfixe OPT)')
    a = ap.parse_args()
    t0 = time.time()
    nm = n_min(a.source)
    jeux = charger(a.source)
    print('source %s : %s' % (a.source, ', '.join('%s %d barres %s -> %s' % (
        j['nom'], len(j['df']), j['df'].index[0].date(), j['df'].index[-1].date()) for j in jeux)), flush=True)
    T = construire_tables(jeux, a.source, a.recalcul)
    PM = preparer(jeux)
    PLAC = {k: B.placebo_moyen(tab) for k, tab in T.items()}
    _G.update(jeux=jeux, T=T, PM=PM, PLAC=PLAC, OFF=decalages(jeux), nmin=nm,
              flex=SIM.charge_regles()['tradeify_50k_select_flex'])

    # ---- balayage ---------------------------------------------------------------------
    cles = toutes_variantes()
    if BASE and tuple(BASE[a_] for a_ in ORDRE) not in cles:
        raise SystemExit('base absente')
    print('%d variantes (au plus %d réglages changés par rapport au préréglage 25) ; %d géométries de table' % (
        len(cles), MAX_CHANGEMENTS, len(GEOMS)), flush=True)
    S, TR = {}, {}
    with pool() as p:
        for v, tr, s in p.imap_unordered(_eval, cles, chunksize=8):
            S[v] = s; TR[v] = tr
    print('balayage + Tradeify : %.0f s' % (time.time() - t0), flush=True)

    # ---- choix ------------------------------------------------------------------------
    cand = choisir(S, nm, k=0)
    top = distinctes(S, TR, cand, 3)
    base_v = tuple(BASE[a_] for a_ in ORDRE)
    lignes = []
    for v in cles:
        s = S[v]; sc, nv = score_lisse(S, v, nm)
        lignes.append(dict(variante=libelle(v), **vdict(v), **{k: s[k] for k in (
            'n', 'gagnants', 'r_moyen', 'pf', 'net_usd', 'plac_gagnants', 'plac_r', 'ecart_pts', 'z_ecart', 'ecart_r',
            'p_reussite', 'p_payout', 've', 'micros')}, score_lisse=sc, nb_voisines=nv,
            eligible=bool(eligible(s, nm))))
    CSV = pd.DataFrame(lignes).sort_values('score_lisse', ascending=False)
    CSV.to_csv(os.path.join(SORTIES, 'balayage_%s.csv.gz' % a.source), index=False, float_format='%.5g')
    print('éligibles : %d / %d' % (int(CSV['eligible'].sum()), len(CSV)), flush=True)

    # ---- bootstrap de White sur tout le balayage --------------------------------------
    jours_id = {}
    for ji in range(len(jeux)):
        for jr in np.unique(PM[ji]['jour']):
            jours_id[(ji, int(jr))] = len(jours_id)
    ND = len(jours_id)
    Vw = [v for v in cles if S[v]['n'] >= 20]
    X = np.zeros((len(Vw), ND), np.float32); XW = np.zeros((len(Vw), ND), np.float32)
    for q, v in enumerate(Vw):
        c = rassembler(v, TR[v])
        di = np.array([jours_id[(int(j), int(jr))] for j, jr in zip(c['jeu'], c['jour'])], int)
        np.add.at(X[q], di, c['r'] - c['pr'])
        np.add.at(XW[q], di, (c['pnl'] > 0) - c['pw'])
    tR, pR, pR_best, _ = AN.white(X, n_boot=N_BOOT_WHITE, graine=1)
    tW, pW, pW_best, _ = AN.white(XW, n_boot=N_BOOT_WHITE, graine=0)
    pos = {v: q for q, v in enumerate(Vw)}
    print('White (%d variantes, %d jours) : meilleure t R = %.2f (p=%.2f) ; meilleure t taux = %.2f (p=%.2f)' % (
        len(Vw), ND, tR.max(), pR_best, tW.max(), pW_best), flush=True)

    # ---- walk-forward -----------------------------------------------------------------
    nm_pli = max(10, int(round(nm * RATIO / (RATIO + K_PLIS))))
    wf = []
    for p_ in range(K_PLIS):
        app = list(range(p_, p_ + RATIO)); tst = [p_ + RATIO]
        Sp = {}
        for v in cles:
            c = rassembler(v, TR[v], app)
            Sp[v] = stats(c)
            Sp[v].update(p_reussite=np.nan, p_payout=np.nan, ve=np.nan, micros=0)
        todo = [(v, TR[v], app) for v in cles if Sp[v]['n'] >= nm_pli and Sp[v]['r_moyen'] > 0]
        with pool() as pl:
            for v, nt in pl.imap_unordered(_eval_pli, todo, chunksize=8):
                Sp[v].update(nt)
        ch = choisir(Sp, nm_pli, k=1)
        if not ch:
            wf.append(dict(pli=p_, choix=None)); continue
        v = ch[0][1]
        ct = rassembler(v, TR[v], tst); st = stats(ct)
        wf.append(dict(pli=p_, choix=libelle(v), v=v, app_n=Sp[v]['n'], app_gagnants=Sp[v]['gagnants'], app_r=Sp[v]['r_moyen'],
                       app_ve=Sp[v]['ve'], score=ch[0][0], test=st, ct=ct))
        print('  pli %d : choix %s | appr. n=%d %.0f %% R %+.2f | test n=%d %.0f %% (placebo %.0f %%) R %+.2f' % (
            p_, libelle(v), Sp[v]['n'], 100 * Sp[v]['gagnants'], Sp[v]['r_moyen'], st['n'],
            100 * st['gagnants'] if st['n'] else float('nan'), 100 * st['plac_gagnants'] if st['n'] else float('nan'),
            st['r_moyen'] if st['n'] else float('nan')), flush=True)
    pool_wf = {k: np.concatenate([w['ct'][k] for w in wf if w.get('ct') is not None and len(w['ct']['pnl'])] or [np.zeros(0)])
               for k in ('pnl', 'r', 'pw', 'pr')}
    sw = stats(pool_wf)
    print('walk-forward (%d plis avec choix) : n=%d gagnants %.1f %% (placebo %.1f %%) R %+.3f PF %.2f net %+.0f $ (1 micro)' % (
        sum(1 for w in wf if w.get('v')), sw['n'], 100 * sw['gagnants'] if sw['n'] else np.nan,
        100 * sw['plac_gagnants'] if sw['n'] else np.nan, sw['r_moyen'] if sw['n'] else np.nan,
        sw['pf'] if sw['n'] else np.nan, sw['net_usd']), flush=True)

    # ---- sorties : base, top 3, Pine, vérification moteur -----------------------------
    out = []
    out.append('SOURCE %s | %d variantes | n_min %d | White: meilleure t(R)=%.2f p=%.2f, t(taux)=%.2f p=%.2f' % (
        a.source, len(cles), nm, tR.max(), pR_best, tW.max(), pW_best))
    sb = S[base_v]
    out.append('PRÉRÉGLAGE 25 (fenêtre 22:15) : n=%d gagnants %.1f %% (placebo %.1f %%) R %+.3f PF %.2f | P=%s VE=%s (%s micros)' % (
        sb['n'], 100 * sb['gagnants'], 100 * sb['plac_gagnants'], sb['r_moyen'], sb['pf'], sb['p_reussite'], sb['ve'], sb['micros']))
    pine_lignes = []
    verifs = []
    for rang, (sc, v) in enumerate(top, 1):
        s = S[v]
        nom = nom_preset(v, rang)
        pl = ligne_pine(v, s['micros'])
        pine_lignes.append((nom, pl, v, s, sc))
        # vérification moteur : rejoue les signaux, compare n et somme des R
        d = vdict(v); g = (d['stop'], d['obj'], d['sortie'], d['be'])
        Tm = []
        for ji, j in enumerate(jeux):
            pm = PM[ji]; aa = pm['dec'][d['decl']]
            L = aa[0] & pm['tr'][d['tr']][0] & pm['det'][d['det']][0] & pm['feu'][d['feu']][0] & pm['hr'][d['hr']][0]
            Sg = aa[1] & pm['tr'][d['tr']][1] & pm['det'][d['det']][1] & pm['feu'][d['feu']][1] & pm['hr'][d['hr']][1]
            t = M.backtest(j['df'], long=L, short=Sg, gestion=gestion(j['instrument'], g))
            t['jeu'] = j['nom']; Tm.append(t)
        Tm = pd.concat(Tm, ignore_index=True).sort_values('entree_t').reset_index(drop=True)
        ok = (len(Tm) == s['n']) and abs(Tm['r'].sum() - s['r_moyen'] * s['n']) < 1e-6 * max(1, s['n'])
        verifs.append(ok)
        q = pos.get(v)
        wp = (pR[q], pW[q]) if q is not None else (np.nan, np.nan)
        out.append('\n#%d %s\n   n=%d gagnants %.1f %% (placebo %.1f %%, écart %+.1f pts, z=%.1f) R moyen %+.3f (placebo %+.3f) PF %.2f net %+.0f $/micro\n'
                   '   Tradeify Select Flex : %d micros, P(réussite)=%.2f P(1er payout)=%.2f VE=%+.0f $ | score lissé %+.0f $ (%d voisines) | White p: R %.2f, taux %.2f | moteur=%s' % (
                       rang, libelle(v), s['n'], 100 * s['gagnants'], 100 * s['plac_gagnants'], s['ecart_pts'], s['z_ecart'],
                       s['r_moyen'], s['plac_r'], s['pf'], s['net_usd'], s['micros'], s['p_reussite'], s['p_payout'], s['ve'], sc,
                       score_lisse(S, v, nm)[1], wp[0], wp[1], 'identique' if ok else 'ÉCART'))
        if rang == 1:
            Tbest = Tm.drop(columns=['jeu'])
            best = (v, s, sc, wp)
    if not top:
        out.append('\nAUCUNE variante ne passe la règle (>= 55 %% de gagnants, R > 0, n >= %d).' % nm)
    out.append('\nWALK-FORWARD (%d plis ; choix sur 3 blocs, test sur le suivant) : n=%d gagnants %s (placebo %s) R %s PF %s net %s $ (1 micro)' % (
        K_PLIS, sw['n'], '%.1f %%' % (100 * sw['gagnants']) if sw['n'] else 'n/a', '%.1f %%' % (100 * sw['plac_gagnants']) if sw['n'] else 'n/a',
        '%+.3f' % sw['r_moyen'] if sw['n'] else 'n/a', '%.2f' % sw['pf'] if sw['n'] else 'n/a', '%+.0f' % sw['net_usd']))
    for w in wf:
        if w.get('v'):
            t = w['test']
            out.append('   pli %d : %s | appr. %d tr. %.0f %% R %+.2f | test %d tr. %s (placebo %s) R %s' % (
                w['pli'], w['choix'], w['app_n'], 100 * w['app_gagnants'], w['app_r'], t['n'],
                '%.0f %%' % (100 * t['gagnants']) if t['n'] else '-', '%.0f %%' % (100 * t['plac_gagnants']) if t['n'] else '-',
                '%+.2f' % t['r_moyen'] if t['n'] else '-'))
        else:
            out.append('   pli %d : aucune variante éligible à l\'apprentissage' % w['pli'])
    txt = '\n'.join(out)
    with open(os.path.join(SORTIES, 'resume_%s.txt' % a.source), 'w') as fh:
        fh.write(txt + '\n')
    print('\n' + txt, flush=True)

    with open(os.path.join(ICI, 'presets_pine.txt'), 'w') as fh:
        fh.write('// Optimiseur 25 (OPT), source %s, %s. 3 meilleures lignes pour f_pr_def() de STRATEGIE_V1.pine.\n' % (
            a.source, pd.Timestamp.now(tz='Europe/Paris').strftime('%d/%m/%Y %H:%M')))
        fh.write('// Ajouter chaque nom EXACT dans options=[...] du menu « Préréglage », puis coller la ligne dans f_pr_def().\n')
        fh.write('// Fenêtre 00:20-22:15 Paris via hr1 ; « Niveaux mesurés sur » = Vrais prix à régler à la main (lvl=1) ;\n')
        fh.write('// TREND 4 h : tr4h=1 ; taille : fixe=N micros (Contrats fixes) ; sortie temps : tBar=N bougies.\n')
        fh.write('// REJETÉ si la source est le cache (2 mois) : à passer au testeur sur 3 ans, pas à trader.\n\n')
        if not pine_lignes:
            fh.write('// Aucune variante éligible avec la règle fixée.\n')
        for nom, pl, v, s, sc in pine_lignes:
            fh.write('// %s | n=%d gagnants %.0f %% R %+.2f PF %.2f | %d micros P=%.2f VE=%+.0f $\n' % (
                libelle(v), s['n'], 100 * s['gagnants'], s['r_moyen'], s['pf'], s['micros'], s['p_reussite'], s['ve']))
            fh.write('     nom == "%s" ? "%s" :\n\n' % (nom, pl))

    if a.registre and top:
        v, s, sc, wp = best
        ok = all(verifs)
        verdict = ('essai à blanc sur %s : %s | walk-forward %d tr. %.0f %% gagnants (placebo %.0f %%) R %+.2f | White p(R)=%.2f, '
                   'meilleur du balayage p=%.2f ; VE Tradeify %+.0f $ avec %d micros ; score lissé %+.0f $' % (
                       a.source, 'NON CONCLUANT (2 mois)' if a.source == 'cache' else 'à juger', sw['n'],
                       100 * sw['gagnants'] if sw['n'] else float('nan'), 100 * sw['plac_gagnants'] if sw['n'] else float('nan'),
                       sw['r_moyen'] if sw['n'] else float('nan'), wp[0], pR_best, s['ve'], s['micros'], sc))
        idr = RG.ajouter_test(dict(agent='OPT', famille='optim25/voisinage-25', recette=libelle(v), marche='MES+MNQ (micros)',
                                   ut_signal='15', ut_entree='15', echantillon='dev_%s' % a.source,
                                   n_variantes_testees=len(cles), p_tradeify=s['p_reussite'],
                                   p_ref_hasard='', verdict=verdict, trades=Tbest), prefixe='OPT')
        print('registre :', idr, '(moteur identique: %s)' % ok)
    print('terminé en %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
