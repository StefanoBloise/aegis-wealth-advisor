"""Synthetic walk-forward regression experiment; not investment-performance evidence."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from aegis.core import *

def run():
    data=synthetic_data(n=504,seed=73)
    profile=Profile.parse(json.loads((ROOT/'examples/profile.json').read_text()))
    specs=json.loads((ROOT/'examples/constraints.json').read_text())
    result={}
    for name,eps in [('Robust',.00002),('Empirical',0),('Fixed feasible allocation',None)]:
        nav=1.;w=np.array([0.,0.,0.,0.,0.,1.]);wealth=[1.];fees=0;solves=0
        for day in range(252,504):
            if (day-252)%21==0:
                if eps is None:target=np.array([.1,.1,.2,.1,.1,.4])
                else:
                    o=solve(data[day-252:day],profile,specs,epsilon=eps,gamma=.02,cost_bps=1,previous=w)
                    if o['status']!='PROPOSED':raise RuntimeError(o['status'])
                    target=np.array([o['weights'][k] for k in IDS]);solves+=1
                fee=nav*.0001*abs(target-w).sum();nav-=fee;fees+=fee;w=target
            growth=1+data[day];factor=float(w@growth);nav*=factor;w=w*growth/factor;wealth.append(nav)
        a=np.array(wealth);d=a/np.maximum.accumulate(a)-1
        result[name]={'net_return':nav-1,'max_drawdown':float(d.min()),'fees_initial_nav_fraction':fees,'rebalances':12,'optimization_runs':solves}
    out={'scope':'One synthetic path, seed 73; trailing 252 rows only, 21-day rebalancing, drifting weights, 1bp L1 costs. No historical or statistical superiority claim.', 'results':result}
    print(json.dumps(out,indent=2))
if __name__=='__main__':run()
