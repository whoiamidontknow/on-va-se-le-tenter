"""Chargement des séries (signaux calculés sur HA + vrais prix reconstitués) et définition des déclencheurs.

Réutilise tools/strategie : data.py (lecture/fusion des CSV HA), features.py (modules + recon.py),
build_all.py (cache de toutes les séries), api.py (vrais prix), strat.py (générateurs d'entrées).
"""
import os, sys, glob, pickle, hashlib, random
HERE = os.path.dirname(os.path.abspath(__file__))
STRAT = os.path.abspath(os.path.join(HERE, '..'))
if STRAT not in sys.path:
    sys.path.insert(0, STRAT)
import data, features, build_all, strat  # noqa: E402

CACHE_DIR = os.path.join(HERE, 'cache')
TFS_DEFAUT = (5, 15, 30, 60)


def instrument(sym):
    """Instrument (pour la valeur du point et le découpage MES -> NQ)."""
    s = sym.upper()
    if s.startswith('MES'): return 'MES'
    if s.startswith('MNQ'): return 'MNQ'
    if s.startswith('NQ') or s == 'API': return 'NQ'
    if s.startswith('ES'): return 'ES'
    return s


# valeur du point ($) et tick
SPEC = {'MES': (5.0, 0.25), 'NQ': (20.0, 0.25), 'MNQ': (2.0, 0.25), 'ES': (50.0, 0.25)}
COMM_COTE = 1.25          # $ par contrat et par côté
SLIP_TICKS_COTE = 1       # ticks de glissement par côté


def cout_points(inst):
    """Coût aller-retour en points : 2 ticks de glissement + 2 x 1,25 $ de commission."""
    pv, tick = SPEC.get(inst, (5.0, 0.25))
    return 2 * SLIP_TICKS_COTE * tick + 2 * COMM_COTE / pv


def _cle(dossiers):
    h = hashlib.md5()
    for d in sorted(dossiers):
        for f in sorted(glob.glob(os.path.join(d, '**', '*.csv'), recursive=True)):
            st = os.stat(f); h.update(('%s|%d|%d' % (f, st.st_size, int(st.st_mtime))).encode())
    return h.hexdigest()[:12]


def charger_series(dossiers=None, cache=True, verbose=False):
    """Liste des séries S (format features.build_series). dossiers=None : cache commun de tools/strategie
    (tous les dossiers du projet). Sinon : CSV HA de ces dossiers (récursif), fusionnés comme data.build."""
    if not dossiers:
        return build_all.load()
    os.makedirs(CACHE_DIR, exist_ok=True)
    fc = os.path.join(CACHE_DIR, 'series_%s.pkl' % _cle(dossiers))
    if cache and os.path.exists(fc):
        return pickle.load(open(fc, 'rb'))
    ancien = data.DIRS
    try:
        data.DIRS = [os.path.abspath(d) for d in dossiers]
        D = data.build()
    finally:
        data.DIRS = ancien
    S = []
    for (sym, tf), segs in sorted(D.items()):
        if tf not in features.TFMIN:
            continue
        for seg in segs:
            if len(seg) < 300: continue
            S.append(features.build_series(seg, tf, sym))
            if verbose: print('  série', sym, tf, len(seg), flush=True)
    if cache: pickle.dump(S, open(fc, 'wb'))
    return S


def series_api(mode='vrai'):
    """Séries 15 min de l'API (vrais prix si mode='vrai', prix reconstitués si 'recon')."""
    import api
    return api.series('15m', mode)


def selectionner(S_all, tfs):
    """Garde les unités demandées, et pour un même (instrument, unité) écarte une série qui chevauche
    une série plus longue (ex. MES1 continu de septembre recouvert par MESZ)."""
    S = [s for s in S_all if s['tfm'] in tfs]
    S.sort(key=lambda s: -s['n'])
    out = []
    for s in S:
        ins = instrument(s['sym']); a, b = s['T'][0], s['T'][-1]
        if any(instrument(x['sym']) == ins and x['tfm'] == s['tfm'] and a <= x['T'][-1] and x['T'][0] <= b for x in out):
            continue
        out.append(s)
    out.sort(key=lambda s: (instrument(s['sym']), s['tfm'], s['T'][0]))
    return out


# ------------------------------------------------------------------ déclencheurs : f(S) -> [(i, sens)]
def _clx(sens):
    return lambda S: [(i, d) for i, d in strat.e_clx(S) if d == sens]


def _niveaux(S):
    E = dict(strat.e_sess(S))
    for i, d in strat.e_mhl(S):
        E.setdefault(i, d)
    return sorted(E.items())


DECLENCHEURS = {
    'fort': ('Flèche Fort', strat.e_sigF),
    'fort_moyen': ('Flèche Fort+Moyen', strat.e_sigFM),
    'trendline': ('Cassure de trendline', strat.e_tl),
    'climax_buy': ('Climax BUY', _clx(1)),
    'climax_sell': ('Climax SELL', _clx(-1)),
    'heishi': ('Changement Heishinator', strat.e_heishi),
    'niveaux': ('Cassure session/Monday', _niveaux),
    'detector': ('Rebond Detector', strat.e_det_rebond),
}
ALEA = 'aleatoire'


def entrees(S, nom, graine=0):
    """Entrées d'un déclencheur sur la série S. 'aleatoire' : chaque barre, sens tiré au hasard (graine fixe)."""
    if nom == ALEA:
        r = random.Random(graine * 1000003 + S['n'])
        return [(i, r.choice((1, -1))) for i in range(101, S['n'])]
    return DECLENCHEURS[nom][1](S)
