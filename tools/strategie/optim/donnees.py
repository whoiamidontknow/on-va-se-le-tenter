"""Chargement d'un ou plusieurs dossiers d'exports TradingView -> séries prêtes pour l'optimiseur.

Deux sources de vrais prix :
  (a) exports Heiken Ashi seuls : vrais prix RECONSTITUÉS depuis le HA (tools/strategie/recon.py,
      fiable en 15 min : +-0,1-0,2 R ; pas en 1-3 min) ;
  (b) exports HA + exports en bougies STANDARD du même graphique (même symbole, même unité) : vrais
      prix EXACTS, appariés par horodatage (la bougie HA doit vérifier c_HA = (o+h+l+c)/4 du standard,
      sinon l'appariement est refusé pour cette série).
Le type de chaque CSV (HA ou standard) est DÉTECTÉ sur les données : en HA, open_t = (open+close)_{t-1}/2.
Fichiers JSON de l'API du terminal web (api_vitrine_*.json) : vrais prix exacts fournis par l'API.

Symbole et unité lus dans le nom du fichier « PREFIXE_SYMBOLE, UNITÉ_hash.csv »
(ex. « CME_MINI_NQZ2026, 15_20e4a.csv » -> racine NQ, unité 15). Plusieurs exports du même
(racine, unité) sont fusionnés : pour un horodatage présent dans plusieurs fichiers on garde la bougie
la plus « chaude » (la plus loin du début de son fichier : l'open HA est récursif). Segments coupés aux
trous entre exports. La chauffe des indicateurs est coupée plus loin (warmup, en barres).
"""
import os, re, sys, glob, json, csv, hashlib, pickle, datetime
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STRAT = os.path.abspath(os.path.join(HERE, '..'))
if STRAT not in sys.path:
    sys.path.insert(0, STRAT)
import data as D0          # noqa: E402  lecture d'un CSV (colonnes de l'indicateur)
import features as F0      # noqa: E402  modules + reconstitution

PARIS = F0.PARIS
NOM = re.compile(r'^(?P<pref>.+?)_(?P<tok>[A-Z0-9]+!?), (?P<tf>[0-9]+[A-Z]?|[DWM])(?:_[0-9a-f]+)?(?: \(\d+\))?\.csv$')
RACINE = re.compile(r'^([A-Z]+?)(?:[FGHJKMNQUVXZ]\d{2,4}|\d!)$')
VERSION = 3


def racine(tok):
    m = RACINE.match(tok)
    return m.group(1) if m else tok


def parse_nom(path):
    m = NOM.match(os.path.basename(path))
    if not m:
        return None
    tf = m.group('tf')
    if tf in ('D', 'W', 'M'):
        tf = '1' + tf
    return dict(tok=m.group('tok'), racine=racine(m.group('tok')), tf=tf)


def lister(dossiers):
    """Tous les CSV au format d'export TradingView et les JSON de l'API, récursivement."""
    csvs, jsons = [], []
    for d in dossiers:
        if os.path.isfile(d):
            (jsons if d.endswith('.json') else csvs).append(d)
            continue
        for f in glob.glob(os.path.join(d, '**', '*'), recursive=True):
            b = os.path.basename(f)
            if b.endswith('.csv') and parse_nom(f):
                csvs.append(f)
            elif b.startswith('api_vitrine') and b.endswith('.json'):
                jsons.append(f)
    return sorted(set(csvs)), sorted(set(jsons))


def type_bougies(rows, tick):
    """'HA' si open_t = (open+close)_{t-1}/2 sur > 80 % des barres consécutives, sinon 'STD'."""
    ok = tot = 0
    for a, b in zip(rows[:-1], rows[1:]):
        if None in (a['o'], a['c'], b['o']):
            continue
        tot += 1
        ok += abs(b['o'] - (a['o'] + a['c']) / 2) <= 0.6 * tick
    return 'HA' if tot and ok / tot > 0.8 else 'STD'


def _segments(ivals, best):
    ts = sorted(best)
    ivals = sorted(ivals)
    segs = []
    for a, b in ivals:
        if segs and a <= segs[-1][1]:
            segs[-1][1] = max(segs[-1][1], b)
        else:
            segs.append([a, b])
    out = []
    for a, b in segs:
        out.append([best[t] for t in ts if a <= t <= b])
    return out


def _fusion(fichiers):
    best, ivals = {}, []
    for rows in fichiers:
        if not rows:
            continue
        ivals.append((rows[0]['t'], rows[-1]['t']))
        for r in rows:
            b = best.get(r['t'])
            if b is None or (r['warm'], r['v'] is not None) > (b['warm'], b['v'] is not None):
                if b is not None and r['v'] is None and b['v'] is not None:
                    r = dict(r, v=b['v'])
                best[r['t']] = r
    return _segments(ivals, best)


def _api_rows(jsons, tf):
    u = {'15': '15m', '2': '2m', '5': '5m', '1': '1m', '60': '1h'}.get(tf, tf + 'm')
    rows, marks = {}, {}
    for f in jsons:
        A = json.load(open(f))
        U = A.get('unites', {}).get(u)
        if not U:
            continue
        for k, b in enumerate(U['bougies']):
            t = b['t'] // 1000
            if t in rows and rows[t]['warm'] > k:
                continue
            rows[t] = dict(t=datetime.datetime.fromtimestamp(t, datetime.timezone.utc).astimezone(PARIS),
                           o=b['o'], h=b['h'], l=b['l'], c=b['c'], v=b['v'], cr=b['cr'], hr=b['hr'], lr=b['lr'],
                           warm=k, oLF=False, oSF=False, oLM=False, oSM=False)
        for x in U.get('indicateurs', []):
            i = str(x.get('id', ''))
            if i.startswith('sig_lf'): marks[x['t']] = 1
            if i.startswith('sig_sf'): marks[x['t']] = -1
    step = F0.TFMIN[tf] * 60
    segs = [[]]
    for t in sorted(rows):
        if segs[-1] and t - segs[-1][-1] > step:
            segs.append([])
        segs[-1].append(t)
    out = []
    for s in segs:
        rr = [rows[t] for t in s]
        for r, t in zip(rr, s):
            r['oLF'] = marks.get(t) == 1
            r['oSF'] = marks.get(t) == -1
        if rr:
            out.append(rr)
    return out


def _vrais_prix(S, rr):
    """Remplace les vrais prix reconstitués par des vrais prix connus (liste de (o,h,l,c) ou None)."""
    k = 0
    for i, x in enumerate(rr):
        if x is None:
            continue
        S['ro'][i], S['rh'][i], S['rl'][i], S['rc'][i] = x
        k += 1
    S['ratr'], _, _, _ = F0.adx_atr(S['rh'], S['rl'], S['rc'])
    S['rhx'] = S['rhn'] = S['rh']
    S['rlx'] = S['rln'] = S['rl']
    S['exact'] = k / max(S['n'], 1)


def charger(dossiers, tf, symboles=None, instruments=None, min_barres=300, cache_dir=None, log=print, api=None):
    """Renvoie (liste de séries S au format features.build_series, journal de chargement).
    api : True = lire aussi les JSON de l'API ; None = seulement s'il n'y a aucun CSV de cette unité."""
    instruments = instruments or {}
    csvs, jsons = lister(dossiers)
    if tf not in F0.TFMIN:
        raise SystemExit('Unité %s non gérée (gérées : %s)' % (tf, ', '.join(F0.TFMIN)))
    csvs = [f for f in csvs if parse_nom(f)['tf'] == tf]
    syms = None if not symboles else {s.upper() for s in symboles}
    if syms:
        csvs = [f for f in csvs if parse_nom(f)['racine'] in syms]
    h = hashlib.md5(repr((VERSION, tf, sorted(syms or []), min_barres, api,
                          [(os.path.basename(f), os.path.getsize(f), int(os.path.getmtime(f))) for f in csvs + jsons]))
                    .encode()).hexdigest()[:16]
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cf = os.path.join(cache_dir, 'series_%s.pkl' % h)
        if os.path.exists(cf):
            S, journal = pickle.load(open(cf, 'rb'))
            log('séries lues dans le cache (%d)' % len(S))
            return S, journal
    journal = []
    ha, std = {}, {}
    for f in csvs:
        p = parse_nom(f)
        tick = instruments.get(p['racine'], {}).get('tick', 0.25)
        rows = D0.read(f)
        for r in rows:
            r.pop('src', None)
        rows = [r for r in rows if None not in (r['o'], r['h'], r['l'], r['c'])]
        kind = type_bougies(rows, tick)
        journal.append((os.path.basename(f), p['racine'], kind, len(rows),
                        rows[0]['t'].strftime('%Y-%m-%d %H:%M') if rows else '', rows[-1]['t'].strftime('%Y-%m-%d %H:%M') if rows else ''))
        (ha if kind == 'HA' else std).setdefault(p['racine'], []).append(rows)
    series = []
    for rac in sorted(ha):
        spec = instruments.get(rac, {})
        tick = spec.get('tick', 0.25)
        stdmap = {}
        for rows in std.get(rac, []):
            for r in rows:
                stdmap[r['t']] = (r['o'], r['h'], r['l'], r['c'])
        for seg in _fusion(ha[rac]):
            if len(seg) < min_barres:
                continue
            S = F0.build_series(seg, tf, rac, g=tick, tick=tick)
            S['racine'] = rac
            S['source'] = 'CSV'
            S['exact'] = 0.0
            if stdmap:
                rr = [stdmap.get(t) for t in S['T']]
                ok = [abs(sum(x) / 4 - S['c'][i]) <= 0.6 * tick for i, x in enumerate(rr) if x is not None]
                if ok and sum(ok) / len(ok) >= 0.9:
                    _vrais_prix(S, rr)
                    S['source'] = 'CSV+STD'
                elif ok:
                    log('ATTENTION %s : bougies standard incohérentes avec le HA (%.0f %% d\'accord) : ignorées'
                        % (rac, 100 * sum(ok) / len(ok)))
            series.append(S)
    if api is None:
        api = not ha
    if jsons and api and (not syms or syms & {'NQ', 'API'}):
        for seg in _api_rows(jsons, tf):
            if len(seg) < min_barres:
                continue
            S = F0.build_series(seg, tf, 'API', g=1.0, tick=1.0)
            S['racine'] = 'API'
            S['source'] = 'API'
            _vrais_prix(S, [(4 * r['c'] - r['hr'] - r['lr'] - r['cr'], r['hr'], r['lr'], r['cr']) for r in seg])
            series.append(S)
        journal += [(os.path.basename(f), 'API', 'JSON', 0, '', '') for f in jsons]
    for S in series:
        S['sym'] = S['racine']
    if cache_dir:
        pickle.dump((series, journal), open(cf, 'wb'))
    return series, journal
