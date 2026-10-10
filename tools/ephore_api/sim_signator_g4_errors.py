from sim_signator_g4 import *
import sys
warm=int(sys.argv[1]); D_=all_data(True)
def row(d,i,tag,r):
    f=lambda x:'na' if x is None else f"{x:.2f}"
    tr='F' if d['LF'][i] or d['SF'][i] else ('M' if d['LM'][i] or d['SM'][i] else '-')
    dayidx=sum(1 for j in range(i) if d['t'][j][:10]==d['t'][i][:10])
    print(tag,d['inst'],d['tf'],d['t'][i][:16],'bull' if d['bull'][i] else 'bear','run',d['run'][i],'truth',tr,'sim',r,'dB',f(d['dband'][i]),'v/ma',f(d['v'][i]/d['vma'][i] if d['vma'][i] else None),'adx',f(d['adx'][i]),'sc',f(d['sc'][i]),'idx',i,'barDuJour',dayidx,'news',d['news'][i],'close-e50/atr',f((d['c'][i]-d['e50'][i])/d['atr'][i]) if d['atr'][i] else '')
for d in D_:
    for i in range(warm,len(d['c'])):
        r=v8(d,i,use_news=False); p=r is not None and r[1]=='F'
        t=d['LF'][i] or d['SF'][i]
        if p and not t: row(d,i,'FP',r)
        if t and not p: row(d,i,'FN',r)
