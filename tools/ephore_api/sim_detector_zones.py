"""Simule le Detector de COMPLETV2.pine (LuxAlgo OB) et compare aux boites det_ de l'API (copies locales)."""
import json,sys
def sim(B,src='ha',length=5,nkeep=3,mit='Wick',bounds='pine',vol_key='v',anchor=None):
    if src=='ha': H=[b['h'] for b in B];L=[b['l'] for b in B];C=[b['c'] for b in B]
    else: H=[b['hr'] for b in B];L=[b['lr'] for b in B];C=[b['cr'] for b in B]
    V=[b[vol_key] for b in B];T=[b['t']//1000 for b in B];n=len(B)
    bull=[];bear=[];os_=0   # elements [top,btm,avg,left]
    for i in range(n):
        if i<2*length: continue
        w=slice(i-length+1,i+1)
        up=max(H[w]);lo=min(L[w])
        if mit=='Close': tb=min(C[w]);tr=max(C[w])
        else: tb=lo;tr=up
        j=i-length
        os_=0 if H[j]>up else 1 if L[j]<lo else os_
        # pivothigh volume(5,5) au centre j
        pv=V[j]>max(V[j-length:j]) and V[j]>=max(V[j+1:j+length+1]) if j>=length else False
        # Pine pivothigh: strictement > a gauche et droite? (ta.pivothigh: > left, > right ; egalite exclue)
        if j>=length: pv=all(V[j]>x for x in V[j-length:j]) and all(V[j]>x for x in V[j+1:j+length+1])
        if pv and os_==1:
            hl2=(H[j]+L[j])/2; bull.insert(0,[hl2,L[j],(hl2+L[j])/2,T[j]])
        if pv and os_==0:
            hl2=(H[j]+L[j])/2; bear.insert(0,[H[j],hl2,(H[j]+hl2)/2,T[j]])
        for arr,tg,isb in((bull,tb,True),(bear,tr,False)):
            vals=[e[1] if isb else e[0] for e in arr]
            for v in vals:
                idx=next((k for k,e in enumerate(arr) if (e[1] if isb else e[0])==v),-1)
                if idx>=0 and ((tg<v) if isb else (tg>v)): arr.pop(idx)
    return bull[:nkeep],bear[:nkeep]
def api_boxes(U):
    r={'bull':[],'bear':[]}
    for x in U['indicateurs']:
        if x.get('type')=='boite' and x['id'].startswith('det_'):
            r[x['id'].split('_')[1]].append((x['t0'],x['haut'],x['bas']))
    return r
def score(S,A,tol=0.02):
    # S: liste [top,btm,avg,left]; A: (t0,haut,bas) ; appariement par t0
    tp_t=tp_b=0
    for side in('bull','bear'):
        pass
def compare(U,**kw):
    bu,be=sim(U['bougies'],**kw);A=api_boxes(U)
    res={'n_api':0,'n_sim':0,'t0':0,'bornes':0}
    for side,S in(('bull',bu),('bear',be)):
        a=A[side];res['n_api']+=len(a);res['n_sim']+=len(S)
        sd={e[3]:e for e in S}
        for t0,h,l in a:
            if t0 in sd:
                res['t0']+=1
                if abs(sd[t0][0]-h)<0.02 and abs(sd[t0][1]-l)<0.02: res['bornes']+=1
    return res
if __name__=='__main__':
    for f in('api_vitrine_instantane.json','api_vitrine_20261012.json'):
        d=json.load(open(f))
        for u in('15m','2m'):
            U=d['unites'][u]
            print(f,u,compare(U))
            for src in('ha','reel'):
                print('  src',src,compare(U,src=src))
