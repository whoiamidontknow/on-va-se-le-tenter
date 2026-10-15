from sim_ours import *
import pickle
rows=pickle.load(open('rows.pkl','rb'))
def fmt(f): return 'sc%.0f(S%.2f M%.2f V%.2f G%.2f) adx%.1f dB%.2f vr%.2f rA%.2f cp%.2f'%(f['score'],f['sS'],f['sM'],f['sV'],f['sG'],f['adx'],f['dB'],f['volr'] or -1,f['rngatr'],f['cpos'])
print('--- Vb MOYEN (cibles) : score nôtre')
for s,t,tm,k,vbF,vb,vdF,vd,me,f in rows:
    if vb and not vbF: print(s,t,tm[:16],'LS'[k],'ours' if me else 'ours-absent',fmt(f))
print('--- distribution score des Vb FORT : min/médiane/max', end=' ')
sc=sorted(f['score'] for *_,vbF,vb,vdF,vd,me,f in [(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9]) for r in rows] if vbF)
print(sc[0],sc[len(sc)//2],sc[-1],len(sc))
