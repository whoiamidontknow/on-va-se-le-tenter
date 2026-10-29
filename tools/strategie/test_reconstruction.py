"""Teste si les vrais prix (high/low/close/open) se reconstituent depuis les seules bougies HA.
Vérité = API (o/h/l/c HA + cr/hr/lr réels). open_reel = 4*c_HA - hr - lr - cr."""
import json,statistics as st
P='/Users/jeremk/ERGON/on-va-se-le-tenter/tools/ephore_api/'
for f in ['api_vitrine_instantane.json','api_vitrine_20261012.json']:
    A=json.load(open(P+f))
    for u in ['15m','2m']:
        B=A['unites'][u]['bougies']; n=len(B)
        o=[b['o'] for b in B];h=[b['h'] for b in B];l=[b['l'] for b in B];c=[b['c'] for b in B]
        hr=[b['hr'] for b in B];lr=[b['lr'] for b in B];cr=[b['cr'] for b in B]
        orl=[4*c[i]-hr[i]-lr[i]-cr[i] for i in range(n)]
        # high exact quand h_HA > max(o_HA,c_HA)+eps
        eh=[abs(h[i]-hr[i]) for i in range(n) if h[i]>max(o[i],c[i])+0.01]
        nh=sum(1 for i in range(n) if not h[i]>max(o[i],c[i])+0.01)
        el=[abs(l[i]-lr[i]) for i in range(n) if l[i]<min(o[i],c[i])-0.01]
        nl=sum(1 for i in range(n) if not l[i]<min(o[i],c[i])-0.01)
        gap=[orl[i]-cr[i-1] for i in range(1,n)]
        # surestimation quand h_HA==o_HA
        over=[h[i]-hr[i] for i in range(n) if not h[i]>max(o[i],c[i])+0.01]
        # reconstruction close avec open=close precedent (vrai) -> erreur = gap
        # reconstruction recursive (sans aucun vrai prix) avec bornage
        H=[h[i] if h[i]>max(o[i],c[i])+0.01 else None for i in range(n)]
        L=[l[i] if l[i]<min(o[i],c[i])-0.01 else None for i in range(n)]
        cc=[None]*n; cc[0]=c[0]; err=[]
        for i in range(1,n):
            hi=H[i] if H[i] is not None else h[i]; lo=L[i] if L[i] is not None else l[i]
            S=4*c[i]-hi-lo   # o+c (approx si hi/lo inconnus)
            oo=cc[i-1]; oo=min(max(oo,max(lo,S-hi)),min(hi,S-lo)); cc[i]=S-oo
            err.append(abs(cc[i]-cr[i]))
        q=lambda x,p: sorted(x)[int(p*(len(x)-1))]
        print(f,u,'n',n,'| high exact sur',n-nh,'(err max %.2f)'%max(eh),'inconnu',nh,'surestim med %.1f'%st.median(over),
              '| low exact',n-nl,'inconnu',nl,'| gap open-close prec: med %.2f p95 %.2f max %.2f'%(st.median(map(abs,gap)),q(list(map(abs,gap)),.95),max(map(abs,gap))),
              '| close reconstruit: err med %.2f p90 %.2f p99 %.2f'%(st.median(err),q(err,.9),q(err,.99)))
