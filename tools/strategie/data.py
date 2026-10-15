"""Chargement et fusion de TOUS les exports CSV TradingView (graphique Heiken Ashi) par (symbole, unité).

- open/high/low/close des CSV = valeurs HA (pas les vrais prix).
- Fusion : pour chaque horodatage, on garde la ligne de l'export où cette bougie est la plus « chaude »
  (le plus loin du début du fichier : l'open HA est récursif et dépend du début de l'historique).
- Segments : si deux exports ne se recouvrent pas, on coupe (pas d'indicateur à cheval sur un trou).
- Flèches de l'original : OU sur tous les groupes de colonnes « Signal Long/Short Fort|Moyen ».
"""
import csv, glob, os, datetime, pickle
from zoneinfo import ZoneInfo
PARIS = ZoneInfo('Europe/Paris')
DIRS = ["/Users/jeremk/Jeu 15:10", "/Users/jeremk/Ephore/Lun12:10", "/Users/jeremk/Ephore/Base 10:10",
        "/Users/jeremk/Ephore/Singal", "/Users/jeremk/Ephore/Filtres", "/Users/jeremk/Ephore",
        "/Users/jeremk/Ephore/Trendlinehelper"]
CACHE = os.path.join(os.path.dirname(__file__), 'cache_data.pkl')


def parse_t(s):
    s = s.strip()
    if s.isdigit():
        return datetime.datetime.fromtimestamp(int(s), tz=datetime.timezone.utc).astimezone(PARIS)
    if len(s) == 10:
        return datetime.datetime.fromisoformat(s).replace(tzinfo=PARIS)
    return datetime.datetime.fromisoformat(s).astimezone(PARIS)


def files():
    out = []
    for d in DIRS:
        rec = d != "/Users/jeremk/Ephore"
        pat = os.path.join(d, '**', '*.csv') if rec else os.path.join(d, '*.csv')
        for f in glob.glob(pat, recursive=rec):
            b = os.path.basename(f)
            if 'CME_MINI_' not in b:
                continue
            sym = b.split('CME_MINI_')[1][:3]
            if 'MES1!' in b:
                sym = 'MES1'          # continu, ancienne période (avril-juillet)
            tf = b.split(', ')[1].split('_')[0]
            out.append((sym, tf, f))
    return sorted(set(out))


def read(f):
    r = list(csv.reader(open(f)))
    h = r[0]
    idx = {}
    for j, k in enumerate(h):
        idx.setdefault(k, j)
    arr = {k: [j for j, x in enumerate(h) if x == k] for k in
           ('Signal Long Fort', 'Signal Short Fort', 'Signal Long Moyen', 'Signal Short Moyen')}
    rows = []
    n = len(r) - 1
    for i, x in enumerate(r[1:]):
        def g(k):
            j = idx.get(k)
            if j is None or j >= len(x) or x[j] in ('', 'NaN'):
                return None
            return float(x[j])
        def anyc(k):
            return any(j < len(x) and x[j] not in ('', '0', '0.0', 'NaN') for j in arr[k])
        rows.append(dict(t=parse_t(x[0]), o=g('open'), h=g('high'), l=g('low'), c=g('close'), v=g('Volume'),
                         e50=g('Moyenator 1'), e60=g('Moyenator 2'),
                         oLF=anyc('Signal Long Fort'), oSF=anyc('Signal Short Fort'),
                         oLM=anyc('Signal Long Moyen'), oSM=anyc('Signal Short Moyen'),
                         hasvol='Volume' in idx, hasorig=bool(arr['Signal Long Fort']), warm=i, src=f))
    return rows


def build():
    groups = {}
    for sym, tf, f in files():
        groups.setdefault((sym, tf), []).append(f)
    data = {}
    for key, fl in groups.items():
        best = {}
        ivals = []
        for f in fl:
            rows = read(f)
            if not rows:
                continue
            ivals.append((rows[0]['t'], rows[-1]['t']))
            for r in rows:
                b = best.get(r['t'])
                # priorité : bougie la plus chaude ; à égalité, fichier avec volume
                if b is None or (r['warm'], r['v'] is not None) > (b['warm'], b['v'] is not None):
                    if b is not None and r['v'] is None and b['v'] is not None:
                        r = dict(r, v=b['v'])
                    best[r['t']] = r
        ts = sorted(best)
        # segments : union d'intervalles de fichiers
        ivals.sort()
        segs = []
        for a, b in ivals:
            if segs and a <= segs[-1][1]:
                segs[-1][1] = max(segs[-1][1], b)
            else:
                segs.append([a, b])
        out = []
        for a, b in segs:
            out.append([best[t] for t in ts if a <= t <= b])
        data[key] = out
    return data


def load():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    d = build()
    pickle.dump(d, open(CACHE, 'wb'))
    return d


if __name__ == '__main__':
    if os.path.exists(CACHE):
        os.remove(CACHE)
    D = load()
    for k in sorted(D, key=lambda k: (k[0], int(k[1].replace('D', '000')) if k[1] != '1D' else 9999)):
        for s in D[k]:
            nv = sum(r['v'] is not None for r in s)
            no = sum(r['oLF'] or r['oSF'] or r['oLM'] or r['oSM'] for r in s)
            print(k, len(s), s[0]['t'].strftime('%Y-%m-%d %H:%M'), '->', s[-1]['t'].strftime('%Y-%m-%d %H:%M'),
                  'vol', nv, 'fleches orig', no)
