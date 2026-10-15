import pickle, sys
res = pickle.load(open('grid_res.pkl', 'rb'))
def g(s, k): return s.get(k, 0) if s['n'] else 0
def line(c, o):
    return '%-12s %-12s %-6s %-20s' % c + ' | ' + ' | '.join('%s n%3d R%+.2f PF%4.2f' % (k, o[k]['n'], g(o[k], 'avgR'), min(g(o[k], 'pf'), 9.99)) for k in ('MES', 'NQ', 'A15', 'A2'))
# 1) classement sur MES (apprentissage), n>=40
L = [(c, o) for c, o in res if o['MES']['n'] >= 40]
L.sort(key=lambda x: -x[1]['MES']['avgR'])
print('== TOP 25 sur MES (apprentissage), puis ce que ça donne sur NQ et API')
for c, o in L[:25]: print(line(c, o))
# 2) configurations positives partout (MES, NQ, A15) avec n suffisants
print('\n== positives sur MES ET NQ ET API15 (n>=30/20/15), tri par minimum des moyR')
P = [(c, o) for c, o in res if o['MES']['n'] >= 30 and o['NQ']['n'] >= 20 and o['A15']['n'] >= 15
     and min(o['MES']['avgR'], o['NQ']['avgR'], o['A15']['avgR']) > 0]
P.sort(key=lambda x: -min(x[1]['MES']['avgR'], x[1]['NQ']['avgR'], x[1]['A15']['avgR']))
for c, o in P[:40]: print(line(c, o))
print(len(P), 'configurations positives partout sur', len(res))
# 3) par entrée : part des configurations positives
print('\n== part des configurations positives, par entrée et par jeu')
from collections import defaultdict
D = defaultdict(lambda: defaultdict(list))
for c, o in res:
    for k in ('MES', 'NQ', 'A15', 'A2'):
        if o[k]['n'] >= 10: D[c[0]][k].append(o[k]['avgR'])
for en in D:
    print('%-12s' % en, '  '.join('%s %3.0f%% (méd %+.2f)' % (k, 100 * sum(x > 0 for x in v) / len(v), sorted(v)[len(v) // 2]) for k, v in D[en].items()))
for dim, idx in (('filtre', 1), ('session', 2), ('sortie', 3)):
    print('\n== par', dim)
    D = defaultdict(lambda: defaultdict(list))
    for c, o in res:
        for k in ('MES', 'NQ', 'A15', 'A2'):
            if o[k]['n'] >= 10: D[c[idx]][k].append(o[k]['avgR'])
    for en in D:
        print('%-22s' % en, '  '.join('%s %3.0f%% (méd %+.2f)' % (k, 100 * sum(x > 0 for x in v) / len(v), sorted(v)[len(v) // 2]) for k, v in D[en].items()))
