import charge as c
D=c.load()
for k,t in D.items(): print(k,len(t),t.pnl.sum(),(t.pnl>0).mean(),t.qty.iloc[0],t.entry.min(),t.exit.max(), t.reason.value_counts().to_dict())
for f in c.files(): print(c.preset(f))
