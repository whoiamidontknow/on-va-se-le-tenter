from sim_ours import *
order=['1','2','3','5','15','30','60','240','720','1D']
W=100
data={}
for b,s,t,f in sorted(files(),key=lambda x:-len(open(x[3]).read())):
    R=load(f);F=feats(R)
    for i,r in enumerate(R): data.setdefault((s,t),{}).setdefault(r[0],(r,i,F[i],b))
rows=[]
for (s,t),d in sorted(data.items()):
    for tm,(r,i,f,b) in sorted(d.items()):
        if i<W:continue
        for k in(0,1):
            vb=any((r[34+k+2*m] or 0)!=0 for m in(0,1)); vd=any((r[50+k+2*m] or 0)!=0 for m in(0,1))
            vbF=(r[34+k] or 0)!=0; vdF=(r[50+k] or 0)!=0
            me=any((r[22+k+2*m] or 0)!=0 for m in(0,1))
            if vb or vd or me:
                rows.append((s,t,tm,k,vbF,vb,vdF,vd,me,f))
import pickle;pickle.dump(rows,open('rows.pkl','wb'))
def fmt(f):
    if 'score' not in f: return 'n/a'
    return 'sc%.0f adx%.1f dB%.2f vr%.2f rA%.2f cp%.2f run%d'%(f['score'],f['adx'] or -1,f['dB'],f['volr'] or -1,f['rngatr'],f['cpos'],f['run'])
print('--- ours-only vs Vb (trop)')
for s,t,tm,k,vbF,vb,vdF,vd,me,f in rows:
    if me and not vb: print(s,t,tm[:16],'LS'[k],'Vd' if vd else '--',fmt(f))
print('--- Vb-only (manqué)')
for s,t,tm,k,vbF,vb,vdF,vd,me,f in rows:
    if vb and not me: print(s,t,tm[:16],'LS'[k],'F' if vbF else 'M',fmt(f), 'blackout' if news(tm,t) else '')
print('--- Vd-only, ours absent (manqué vs Vd)')
for s,t,tm,k,vbF,vb,vdF,vd,me,f in rows:
    if vd and not vb and not me: print(s,t,tm[:16],'LS'[k],fmt(f),'blackout' if news(tm,t) else '')
