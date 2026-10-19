"""Daily robust mean-CVaR LP. All products and data are synthetic."""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
import numpy as np
from scipy.optimize import linprog
from scipy import sparse

PRODUCTS = [
 {'id':'EQ','name':'Global equity model','class':'Equity','fee_bps':12,'risk':'Equity drawdown and currency risk'},
 {'id':'TECH','name':'Technology equity model','class':'Equity','fee_bps':25,'risk':'Sector concentration and valuation risk'},
 {'id':'BOND','name':'Intermediate government bond model','class':'Bond','fee_bps':10,'risk':'Interest-rate and inflation risk'},
 {'id':'CREDIT','name':'Investment-grade credit model','class':'Bond','fee_bps':18,'risk':'Default, spread and liquidity risk'},
 {'id':'GOLD','name':'Gold model','class':'Commodity','fee_bps':20,'risk':'Price volatility, no contractual income'},
 {'id':'CASH','name':'Simulated uninvested cash','class':'Cash','fee_bps':0,'risk':'Inflation; real custody risks are not simulated'}]
IDS = [p['id'] for p in PRODUCTS]
TOL = 1e-7

class InputError(ValueError):
    pass

def number(x, name, lo, hi):
    if isinstance(x, bool) or not isinstance(x, (int,float)) or not math.isfinite(x) or not lo <= x <= hi:
        raise InputError(f'{name} must be a finite number in [{lo}, {hi}]')
    return float(x)

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',',':'), allow_nan=False)

def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()

@dataclass(frozen=True)
class Profile:
    horizon_years: float
    risk: str
    liquidity_fraction: float
    loss_tolerance: float
    experience: str
    @classmethod
    def parse(cls, data):
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            raise InputError('Complete all five profile fields; unknown fields are rejected')
        if data['risk'] not in ('conservative','balanced','growth'):
            raise InputError('risk must be conservative, balanced or growth')
        if data['experience'] not in ('beginner','experienced'):
            raise InputError('experience must be beginner or experienced')
        return cls(number(data['horizon_years'],'horizon_years',0,50), data['risk'],
                   number(data['liquidity_fraction'],'liquidity_fraction',0,1),
                   number(data['loss_tolerance'],'loss_tolerance',0,1), data['experience'])
    def policy(self):
        cap = {'conservative':.30,'balanced':.60,'growth':.85}[self.risk]
        reasons = [f'{self.risk} policy permits at most {cap:.0%} in risky products']
        if self.horizon_years < 2 or self.loss_tolerance == 0:
            cap = 0.0
            reasons.append('Short horizon or zero loss tolerance: retain simulated cash')
        elif self.loss_tolerance < .10:
            cap = min(cap,.25)
            reasons.append('Low stated loss tolerance limits risky allocation to 25%')
        if self.experience == 'beginner':
            cap = min(cap,.50)
            reasons.append('Beginner policy limits risky allocation to 50%')
        cap = min(cap,1-self.liquidity_fraction)
        return cap, reasons

def validate_constraints(items):
    if not isinstance(items,list) or len(items)>20:
        raise InputError('constraints must be a list of at most 20 entries')
    result=[]
    for i,s in enumerate(items):
        if not isinstance(s,dict) or set(s)!={'asset','sense','weight'}:
            raise InputError('Each constraint needs exactly asset, sense, weight')
        if s['asset'] not in IDS or s['sense'] not in ('<=','>='):
            raise InputError('Unknown product or constraint sense')
        result.append({'asset':s['asset'],'sense':s['sense'],
                       'weight':number(s['weight'],f'constraint {i} weight',0,1)})
    return result

def synthetic_data(n=252,seed=42):
    if type(n) is not int or not 20<=n<=5000 or type(seed) is not int or seed<0:
        raise InputError('n must be 20..5000 and seed a nonnegative integer')
    rng=np.random.default_rng(seed)
    factor=rng.normal(size=(n,2))
    load=np.array([[.007,0],[.010,0],[0,.003],[.002,.002],[.001,-.001]])
    r=factor@load.T + rng.normal(size=(n,5))*np.array([.005,.008,.002,.003,.007])
    r += np.array([.00055,.00070,.00018,.00025,.00020])
    # Designed stress segment, not a reconstructed historical event.
    r[n//2:n//2+5] += np.array([-.025,-.035,-.008,-.012,.004])
    r -= np.array([p['fee_bps'] for p in PRODUCTS[:-1]])*1e-4/252
    return np.column_stack([r,np.zeros(n)])

def validate_data(data):
    try:
        r=np.asarray(data,dtype=float)
    except (ValueError,TypeError) as e:
        raise InputError('Return matrix must be numeric') from e
    if r.ndim!=2 or r.shape[1]!=6 or not 20<=r.shape[0]<=5000:
        raise InputError('Return matrix requires 20..5000 rows and six fixed-order columns')
    if not np.isfinite(r).all() or np.any(r<=-1) or np.any(r>1) or np.any(r[:,-1]!=0):
        raise InputError('Returns must be finite in (-1,1], with zero simulated cash returns')
    return r

def cvar(losses,alpha=.95):
    """Exact empirical Rockafellar-Uryasev value, including fractional tail mass."""
    alpha=number(alpha,'alpha',.5,.99)
    x=np.asarray(losses,dtype=float)
    if x.ndim!=1 or len(x)==0 or not np.isfinite(x).all():
        raise InputError('losses must be a finite nonempty vector')
    q=float(np.quantile(x,alpha,method='inverted_cdf'))
    return float(q+np.maximum(x-q,0).mean()/(1-alpha))

def constraints_matrix(profile, constraints):
    cap,reasons=profile.policy()
    rows=[]; rhs=[]; labels=[]
    def add(a,b,l):
        rows.append(a); rhs.append(b); labels.append(l)
    add([1,1,1,1,1,0],cap,'Suitability: total risky allocation')
    for j in range(5):
        a=np.zeros(6); a[j]=1
        add(a,.35,f'Concentration: {IDS[j]} <= 35%')
    for i,s in enumerate(constraints):
        sign=1 if s['sense']=='<=' else -1
        a=np.zeros(6); a[IDS.index(s['asset'])]=sign
        add(a,sign*s['weight'],f"Client {i+1}: {s['asset']} {s['sense']} {s['weight']:.2%}")
    return np.asarray(rows),np.asarray(rhs),labels,reasons

def solve(data,profile,constraints=None,epsilon=.0001,gamma=.1,alpha=.95,previous=None,cost_bps=10):
    """Return structured abstention on infeasibility or solver failure; never relax mandates."""
    r=validate_data(data)
    if not isinstance(profile,Profile): profile=Profile.parse(profile)
    # Revalidate even directly constructed dataclass instances.
    profile=Profile.parse(asdict(profile))
    specs=validate_constraints([] if constraints is None else constraints)
    epsilon=number(epsilon,'epsilon',0,.01)
    gamma=number(gamma,'gamma',.001,10)
    alpha=number(alpha,'alpha',.5,.99)
    cost=number(cost_bps,'cost_bps',0,100)*1e-4
    if previous is None: previous=[0,0,0,0,0,1]
    try: prev=np.asarray(previous,dtype=float)
    except (ValueError,TypeError) as e: raise InputError('Invalid previous weights') from e
    if prev.shape!=(6,) or not np.isfinite(prev).all() or np.any(prev<0) or abs(prev.sum()-1)>TOL:
        raise InputError('Previous weights must be a nonnegative six-vector summing to one')
    A,b,labels,reasons=constraints_matrix(profile,specs)
    n=6; t=len(r); tau=n; us=slice(n+1,n+1+t); z=n+1+t; ds=slice(z+1,z+1+n); m=z+1+n
    # Variables [w(6), tau, u(T), z, d(6)].
    obj=np.zeros(m); obj[:n]=-r.mean(axis=0); obj[tau]=gamma
    obj[us]=gamma/((1-alpha)*t); obj[z]=epsilon*(1+gamma/(1-alpha)); obj[ds]=cost
    blocks=[]; bs=[]
    base=sparse.hstack([sparse.csr_matrix(A),sparse.csr_matrix((len(A),m-n))])
    blocks.append(base); bs.extend(b)
    hinge=sparse.hstack([-sparse.csr_matrix(r),-np.ones((t,1)),-sparse.eye(t),sparse.csr_matrix((t,1+n))])
    blocks.append(hinge); bs.extend(np.zeros(t))
    extra=[]; eb=[]
    for j in range(5):
        row=np.zeros(m); row[j]=1; row[z]=-1; extra.append(row); eb.append(0)
    for j in range(n):
        row=np.zeros(m); row[j]=1; row[z+1+j]=-1; extra.append(row); eb.append(prev[j])
        row=np.zeros(m); row[j]=-1; row[z+1+j]=-1; extra.append(row); eb.append(-prev[j])
    blocks.append(sparse.csr_matrix(extra)); bs.extend(eb)
    Aub=sparse.vstack(blocks).tocsr(); bub=np.asarray(bs)
    eq=np.zeros((1,m)); eq[0,:n]=1
    bounds=[(0,1)]*n+[(None,None)]+[(0,None)]*t+[(0,1)]+[(0,1)]*n
    base_info={'data_kind':'synthetic','data_sha256':hashlib.sha256(r.astype('<f8').tobytes()).hexdigest(),
               'policy_reasons':reasons,'assumptions':{'epsilon':epsilon,'gamma':gamma,'alpha':alpha,'cost_bps':cost_bps},
               'profile':asdict(profile),'constraints':specs}
    try:
        opt=linprog(obj,A_ub=Aub,b_ub=bub,A_eq=eq,b_eq=[1],bounds=bounds,method='highs',
                    options={'time_limit':10,'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
    except Exception as e:
        return {**base_info,'status':'UNAVAILABLE','message':'Solver failed; no proposal issued','error_type':type(e).__name__}
    if not opt.success or opt.x is None:
        return {**base_info,'status':'NEEDS_REVISION' if opt.status==2 else 'UNAVAILABLE',
                'message':'Constraints conflict. Revise the mandate; no constraints were relaxed.' if opt.status==2 else 'Solver did not certify an optimum; no proposal issued.',
                'solver_status':int(opt.status),'constraint_labels':labels}
    x=opt.x; w=x[:n]
    bound_error=max([0.]+[float(lo-x[i]) for i,(lo,hi) in enumerate(bounds) if lo is not None]+[float(x[i]-hi) for i,(lo,hi) in enumerate(bounds) if hi is not None])
    residual=max(float(np.max(Aub@x-bub)),abs(w.sum()-1),bound_error,0.)
    if not np.isfinite(x).all() or not np.isfinite(opt.fun) or residual>TOL:
        return {**base_info,'status':'UNAVAILABLE','message':'Independent feasibility validation failed'}
    daily=r@w; ec=cvar(-daily,alpha); norm=float(np.max(w[:5]))
    turnover=float(np.abs(w-prev).sum()); objective=-daily.mean()+gamma*ec+epsilon*(1+gamma/(1-alpha))*norm+cost*turnover
    gap=abs(float(opt.fun)-objective)
    if gap>1e-7:
        return {**base_info,'status':'UNAVAILABLE','message':'Independent objective validation failed'}
    duals=np.asarray(opt.ineqlin.marginals)
    stationarity=obj-Aub.T@duals-eq.T@np.asarray(opt.eqlin.marginals)-np.asarray(opt.lower.marginals)-np.asarray(opt.upper.marginals)
    complementarity=float(np.max(np.abs(duals*(bub-Aub@x))))
    return {**base_info,'status':'PROPOSED','weights':dict(zip(IDS,map(float,w))),
            'metrics':{'daily_mean':float(daily.mean()),'daily_cvar':ec,
             'daily_robust_cvar':ec+epsilon*norm/(1-alpha),'daily_volatility':float(np.std(daily,ddof=1)),
             'turnover_l1':turnover,'estimated_rebalance_cost_fraction':cost*turnover,'objective':float(objective)},
            'validation':{'max_primal_residual':residual,'objective_reconstruction_error':gap,
             'stationarity_residual':float(np.max(np.abs(stationarity))),'complementarity_residual':complementarity},
            'constraint_audit':[{'label':label,'slack':float(b[i]-A[i]@w),
                                  'rhs_local_derivative':float(duals[i])} for i,label in enumerate(labels)],
            'message':'Review synthetic allocation and constraints before approving a simulated rebalance.'}
