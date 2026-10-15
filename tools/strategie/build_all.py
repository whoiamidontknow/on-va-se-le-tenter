"""Construit toutes les séries (signaux + vrais prix reconstitués) et les met en cache."""
import pickle, os, time
import data, features
OUT = os.path.join(os.path.dirname(__file__), 'cache_series.pkl')
def build():
    D = data.load(); S = []
    for (sym, tf), segs in sorted(D.items()):
        for seg in segs:
            if len(seg) < 300: continue
            t0 = time.time(); s = features.build_series(seg, tf, sym); S.append(s)
            ours = sum(1 for x in s['sig'] if x and x[0] == 'F')
            orig = sum(1 for r in seg if r['oLF'] or r['oSF'])
            both = sum(1 for i, r in enumerate(seg) if (r['oLF'] or r['oSF']) and s['sig'][i] and s['sig'][i][0] == 'F')
            print(sym, tf, len(seg), 'vol' if s['hasv'] else 'NOVOL', 'Fort nous/orig/communs', ours, orig, both,
                  'clx', sum(map(abs, s['clx'])), 'TL', sum(s['rB']), sum(s['sB']), '%.1fs' % (time.time() - t0))
    pickle.dump(S, open(OUT, 'wb'))
    return S
def load():
    return pickle.load(open(OUT, 'rb')) if os.path.exists(OUT) else build()
if __name__ == '__main__':
    build()
