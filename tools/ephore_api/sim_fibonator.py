# Fibonator : transcription bar par bar de FIBONACCI_AUTO.pine V2, comparee a fib_75 / fib_zone
# de l'API (2 copies x 15m/2m). Sens V2 (0 = swing recent) : 4/4. Ancien sens V1 : 0/4.
# Usage : python3 tools/ephore_api/sim_fibonator.py
import json
import os
D=os.path.dirname(os.path.abspath(__file__))+'/'
piv_len=10
def run(b, sens_v1=False):
    high=[x['hr'] for x in b]; low=[x['lr'] for x in b]
    def piv(src,bi,ln,is_high):            # f_piv_strict, src[i] = src[bi-i]
        ok = bi >= 2*ln
        if ok:
            c=src[bi-ln]
            for i in range(0,2*ln+1):
                if i!=ln:
                    v=src[bi-i]
                    if (v>=c if is_high else v<=c): ok=False; break
        return ok
    lph=lphb=lpl=lplb=None
    for bi in range(len(b)):
        if piv(high,bi,piv_len,True):  lph,lphb=high[bi-piv_len],bi-piv_len
        if piv(low,bi,piv_len,False):  lpl,lplb=low[bi-piv_len],bi-piv_len
    last=len(b)-1
    bearish = lplb>lphb
    p0,p100,bar0 = (lpl,lph,lplb) if bearish else (lph,lpl,lphb)
    if sens_v1: p0,p100 = p100,p0       # ancien sens : 0 = swing ancien
    lvl=lambda r: p0+(p100-p0)*r
    T=lambda i: b[0]['t']//1000 + i*(b[1]['t']-b[0]['t'])//1000
    pa,pb=lvl(.618),lvl(.75)
    return dict(l75=lvl(.75), l75_t0=T(bar0), l75_t1=T(last+10),
                z_haut=max(pa,pb), z_bas=min(pa,pb), z_t0=T(bar0), z_t1=T(last+50))
for sens_v1 in (False, True):
  print('=== sens', 'V1 (0 = ancien)' if sens_v1 else 'V2 (0 = recent)')
  tot=0
  for f in ['api_vitrine_instantane.json','api_vitrine_20261012.json']:
      d=json.load(open(D+f))
      for tf,u in d['unites'].items():
          fo={o['id']:o for o in u['indicateurs'] if o.get('id','').startswith('fib')}
          s=run(u['bougies'], sens_v1); a75,az=fo['fib_75'],fo['fib_zone']
          prix_ok = abs(round(s['l75'],2)-a75['prix'])<0.005 and abs(round(s['z_haut'],2)-az['haut'])<0.005 and abs(round(s['z_bas'],2)-az['bas'])<0.005
          t_ok = s['l75_t0']==a75['t0'] and s['z_t0']==az['t0'] and s['l75_t1']==a75['t1'] and s['z_t1']==az['t1']
          tot += prix_ok and t_ok
          print(f[13:-5],tf,'75 %.2f/%s'%(s['l75'],a75['prix']),'zone %.2f-%.2f / %s-%s'%(s['z_bas'],s['z_haut'],az['bas'],az['haut']),'prix',prix_ok,'temps',t_ok)
  print('TOTAL',tot,'/4')
