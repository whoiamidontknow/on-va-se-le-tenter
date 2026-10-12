"""Validation croisee des deux variantes de bande qui battent la reference :
balayage continu de la position de reference dans la bande, puis decoupage MES/NQ et par unite."""
import impl_lab_core as C
import collections
base=[C.feats(d) for d in C.DATA]

def reband_w(ds,w):
    """ref = w*bord_eloigne + (1-w)*bord_proche. w=1 -> max/min (reference), w=0.5 -> milieu, w=0 -> bord proche."""
    out=[]
    for d in ds:
        e=dict(d); n=len(d['c']); db=[None]*n
        for i in range(n):
            if not d['atr'][i] or d['e50'][i] is None or d['e60'][i] is None: continue
            hi,lo=max(d['e50'][i],d['e60'][i]),min(d['e50'][i],d['e60'][i])
            if d['bull'][i]: ref=w*hi+(1-w)*lo; db[i]=(d['cc'][i]-ref)/d['atr'][i]
            else:            ref=w*lo+(1-w)*hi; db[i]=(ref-d['cc'][i])/d['atr'][i]
        e['dband']=db; out.append(e)
    return out

print("=== A. balayage continu de la position de reference dans la bande (seuil 0.3) ===")
print(f"  {'w':>5} {'ou':14} {'exactes':>7} {'trop':>5} {'manq':>5} {'erreurs':>8}")
for w in [1.0,0.9,0.8,0.7,0.6,0.5,0.4,0.3,0.2,0.1,0.0]:
    ds=reband_w(base,w); tp,fp,fn,_=C.score(ds)
    lab='max/min (ref)' if w==1 else ('milieu' if w==.5 else ('bord proche' if w==0 else ''))
    print(f"  {w:5.1f} {lab:14} {tp:7} {fp:5} {fn:5} {fp+fn:8}")

print("\n=== B. detail par instrument / unite (reference w=1 vs milieu w=0.5 vs EMA60 seule) ===")
def bytf(ds,**kw):
    agg=collections.defaultdict(lambda:[0,0,0])
    for d in ds:
        for i in range(C.WARM,len(d['c'])):
            r=C.trig(d,i,**kw); p=r is not None
            t=bool(d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i])
            for k in ((d['inst'],d['tf']),(d['inst'],'*'),('*','*')):
                agg[k][0]+=p and t; agg[k][1]+=p and not t; agg[k][2]+=t and not p
    return agg
def reband_mode(ds,mode):
    out=[]
    for d in ds:
        e=dict(d); n=len(d['c']); db=[None]*n
        for i in range(n):
            if not d['atr'][i] or d['e50'][i] is None or d['e60'][i] is None: continue
            a,b=d['e50'][i],d['e60'][i]
            ref={'far':(max(a,b) if d['bull'][i] else min(a,b)),'mid':(a+b)/2,'e60':b}[mode]
            db[i]=(d['cc'][i]-ref)/d['atr'][i] if d['bull'][i] else (ref-d['cc'][i])/d['atr'][i]
        e['dband']=db; out.append(e)
    return out
A={m:bytf(reband_mode(base,m)) for m in ('far','mid','e60')}
keys=sorted(A['far'],key=lambda k:(k[0]!='*',k[0],k[1]))
print(f"  {'cle':12} {'far (ref)':>14} {'milieu':>14} {'EMA60':>14}")
for k in keys:
    print(f"  {k[0]+' '+k[1]:12} " + " ".join(f"{A[m][k][0]}/{A[m][k][1]}/{A[m][k][2]:<6}".rjust(14) for m in ('far','mid','e60')))

print("\n=== C. validation croisee : on choisit la variante sur un sous-ensemble, on mesure sur l'autre ===")
def part(ds,pred): return [d for d in ds if pred(d)]
splits=[('MES seul -> teste sur NQ', lambda d:d['inst']=='MES', lambda d:d['inst']=='NQ'),
        ('NQ seul -> teste sur MES', lambda d:d['inst']=='NQ', lambda d:d['inst']=='MES'),
        ('TF courtes (2,5,15) -> longues (30,60,240,1D)', lambda d:d['tf'] in ('2','5','15'), lambda d:d['tf'] in ('30','60','240','1D')),
        ('TF longues -> courtes', lambda d:d['tf'] in ('30','60','240','1D'), lambda d:d['tf'] in ('2','5','15'))]
for lab,ftr,fte in splits:
    print(f"  {lab}")
    for m in ('far','mid','e60'):
        ds=reband_mode(base,m)
        a=C.score(part(ds,ftr))[:3]; b=C.score(part(ds,fte))[:3]
        print(f"    {m:4} apprentissage {a[0]}/{a[1]}/{a[2]} ({a[1]+a[2]} err)   test {b[0]}/{b[1]}/{b[2]} ({b[1]+b[2]} err)")

print("\n=== D. ou l'ecart se joue : les 3 barres qui changent ===")
for m in ('far','mid','e60'):
    ds=reband_mode(base,m)
    for d in ds:
        for key,i in ((('MES','5'),266),(('NQ','240'),354),(('NQ','15'),151)):
            if (d['inst'],d['tf'])==key:
                print(f"  {m:4} {d['inst']:3} {d['tf']:3} {d['t'][i][:16]} dBand={d['dband'][i]:+.3f} "
                      f"verite={'fleche' if (d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i]) else 'rien  '} "
                      f"sim={C.trig(d,i)}")
