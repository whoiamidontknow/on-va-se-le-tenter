"""Séries de l'API (Nasdaq XYZ100, 15m et 2m) : signaux calculés sur HA, exécution possible sur
VRAIS prix (mode='vrai') ou sur prix reconstitués depuis HA (mode='recon') pour valider la reconstitution."""
import json, datetime
import features
P = '/Users/jeremk/ERGON/on-va-se-le-tenter/tools/ephore_api/'
FILES = ['api_vitrine_instantane.json', 'api_vitrine_20261012.json']
UTC = datetime.timezone.utc


def load_rows(u):
    rows = {}; marks = {}
    for f in FILES:
        A = json.load(open(P + f))
        U = A['unites'][u]
        B = U['bougies']
        for k, b in enumerate(B):
            t = b['t'] // 1000
            if t in rows and rows[t]['warm'] > k: continue
            rows[t] = dict(t=datetime.datetime.fromtimestamp(t, UTC).astimezone(features.PARIS), o=b['o'], h=b['h'], l=b['l'],
                           c=b['c'], v=b['v'], cr=b['cr'], hr=b['hr'], lr=b['lr'], warm=k,
                           oLF=False, oSF=False, oLM=False, oSM=False)
        for x in U['indicateurs']:
            i = str(x.get('id', ''))
            if i.startswith('sig_lf'): marks[x['t']] = 1
            if i.startswith('sig_sf'): marks[x['t']] = -1
    ts = sorted(rows)
    # segments contigus
    segs = [[]]
    step = 900 if u == '15m' else 120
    for t in ts:
        if segs[-1] and t - segs[-1][-1] > step: segs.append([])
        segs[-1].append(t)
    out = []
    for s in segs:
        rr = [rows[t] for t in s]
        for r, t in zip(rr, s):
            if marks.get(t) == 1: r['oLF'] = True
            if marks.get(t) == -1: r['oSF'] = True
        out.append(rr)
    return out


def series(u, mode='vrai'):
    tf = '15' if u == '15m' else '2'
    res = []
    for seg in load_rows(u):
        if len(seg) < 300: continue
        S = features.build_series(seg, tf, 'API', g=1.0, tick=1.0)
        S['api_arrow'] = [1 if r['oLF'] else -1 if r['oSF'] else 0 for r in seg]
        if mode == 'vrai':
            n = len(seg)
            S['rc'] = [r['cr'] for r in seg]; S['rh'] = [r['hr'] for r in seg]; S['rl'] = [r['lr'] for r in seg]
            S['ro'] = [4 * r['c'] - r['hr'] - r['lr'] - r['cr'] for r in seg]
            S['ratr'], _, _, _ = features.adx_atr(S['rh'], S['rl'], S['rc'])
            S['rhx'] = S['rhn'] = S['rh']; S['rlx'] = S['rln'] = S['rl']
        res.append(S)
    return res


if __name__ == '__main__':
    for u in ('15m', '2m'):
        for S in series(u):
            ours = sum(1 for x in S['sig'] if x and x[0] == 'F'); api = sum(1 for x in S['api_arrow'] if x)
            both = sum(1 for i in range(S['n']) if S['api_arrow'][i] and S['sig'][i] and S['sig'][i][1] == S['api_arrow'][i])
            print(u, S['n'], S['T'][0], S['T'][-1], 'fleches nous(F)/API/communes', ours, api, both)
