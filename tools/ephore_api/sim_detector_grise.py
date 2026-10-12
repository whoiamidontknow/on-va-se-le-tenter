import json,csv
d=json.load(open('api_vitrine_instantane.json'))
rows=[]
for u in ('15m','2m'):
    U=d['unites'][u]; B=U['bougies']; ts=[b['t']//1000 for b in B]
    last=B[-1]; px=last['cr']
    # ATR14 simple sur reel
    tr=[max(b['hr']-b['lr'],abs(b['hr']-B[i-1]['cr']),abs(b['lr']-B[i-1]['cr'])) for i,b in enumerate(B) if i]
    atr=sum(tr[-14:])/14
    dets=[x for x in U['indicateurs'] if str(x.get('id','')).startswith('det_')]
    for x in dets:
        i0=ts.index(x['t0']) if x['t0'] in ts else None
        sens='bull' if 'bull' in x['id'] else 'bear'
        pos='dessus' if x['bas']>px else ('dessous' if x['haut']<px else 'dedans')
        dist=(x['bas']-px) if pos=='dessus' else (px-x['haut'] if pos=='dessous' else 0)
        # traversee depuis creation (reel)
        trav=None
        if i0 is not None:
            seg=B[i0+1:]
            trav=any(b['lr']<=x['haut'] and b['hr']>=x['bas'] for b in seg)
            touches=sum(1 for b in seg if b['lr']<=x['haut'] and b['hr']>=x['bas'])
            vol=B[i0]['v']; vmoy=sum(b['v'] for b in B[max(0,i0-20):i0])/20
        rows.append(dict(u=u,id=x['id'],grise=x['grise'],pos=pos,dist=round(dist,2),pct=round(100*dist/px,3),atr=round(dist/atr,2),larg=round(x['haut']-x['bas'],2),d_larg=round(dist/(x['haut']-x['bas']),1),age=len(B)-1-i0 if i0 is not None else None,trav=trav,touches=touches,volrel=round(vol/vmoy,2)))
w=csv.DictWriter(open('oracle_detector_grise.csv','w'),rows[0].keys());w.writeheader();w.writerows(rows)
print(len(rows),'boites; grisees',sum(r['grise'] for r in rows))
for u in ('15m','2m'):
    print(u,'prix',d['unites'][u]['bougies'][-1]['cr'],'grisees',sum(r['grise'] for r in rows if r['u']==u))
for r in rows: print(r)
