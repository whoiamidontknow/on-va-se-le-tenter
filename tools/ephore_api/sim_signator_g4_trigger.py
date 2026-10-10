from sim_signator_g4 import *
import sys
warm=int(sys.argv[1]); D_=all_data(True)
tot=dict(tp=0,fp=0,fn=0)
def f(x): return 'na' if x is None else f"{x:.2f}"
for d in D_:
    for i in range(warm,len(d['c'])):
        r=v8(d,i,use_news=False); p=r is not None
        t=d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i]
        tot['tp']+=bool(p and t); tot['fp']+=bool(p and not t); tot['fn']+=bool(t and not p)
        if p!=bool(t):
            print('FP' if p else 'FN',d['inst'],d['tf'],d['t'][i][:16],'run',d['run'][i],'bull',d['bull'][i],'dB',f(d['dband'][i]),'v/ma',f(d['v'][i]/d['vma'][i] if d['vma'][i] else None),'adx',f(d['adx'][i]),'sc',f(d['sc'][i]),'news',d['news'][i],'c-e50',f((d['c'][i]-d['e50'][i])/d['atr'][i]) if d['atr'][i] else '', 'ema50 side ok')
print(tot)
