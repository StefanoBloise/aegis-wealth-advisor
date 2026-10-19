"""Single-user simulation capability boundary and replayable audit events."""
import copy
import datetime
import json
import secrets
import time
from pathlib import Path
from .core import IDS, PRODUCTS, Profile, InputError, canonical, digest, solve, synthetic_data
from .parser import parse_offline, parse_llm

class Audit:
    def __init__(self,path=None):
        self.path=Path(path) if path else None
        if self.path and self.path.exists() and self.path.stat().st_size:
            raise InputError('Use a new audit file for each simulation session')
        if self.path: self.path.parent.mkdir(parents=True,exist_ok=True)
        self.records=[]
    def append(self,event,payload):
        body={'seq':len(self.records)+1,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'event':event,'payload':copy.deepcopy(payload),'previous_hash':self.records[-1]['hash'] if self.records else '0'*64}
        row={**body,'hash':digest(body)}
        if self.path:
            with self.path.open('a',encoding='utf-8') as f:
                f.write(canonical(row)+'\n'); f.flush()
        self.records.append(row)
        return row
    @staticmethod
    def verify(records):
        previous='0'*64
        for i,row in enumerate(records):
            body={k:v for k,v in row.items() if k!='hash'}
            if row.get('seq')!=i+1 or row.get('previous_hash')!=previous or row.get('hash')!=digest(body): return False
            previous=row['hash']
        return True

class Advisor:
    """READ, PROPOSE and APPROVE_SIM are trusted application roles, never LLM fields.
    This is a process-local capability demo, not production identity management.
    """
    def __init__(self,log=None,data=None,clock=time.monotonic):
        self.audit=Audit(log); self.data=synthetic_data() if data is None else data
        self.clock=clock; self.proposals={}; self.tokens={}; self.revision=0
        self.weights=[0.,0.,0.,0.,0.,1.]; self.nav=100000.
        self.audit.append('SESSION_STARTED',{'mode':'local_simulation','nav':self.nav,'weights':self.weights,'products':IDS})
    def products(self):
        return {'data_kind':'illustrative_catalog','products':copy.deepcopy(PRODUCTS),
                'disclosure':'Fictional products and illustrative fees. No eligibility, tax or regulatory determination.'}
    def parse(self,text,use_llm=False,consent=False):
        if use_llm and consent is not True: raise InputError('Explicit consent is required to send text to the LLM provider')
        result=parse_llm(text) if use_llm else parse_offline(text)
        # Do not log raw client dialogue or provider credentials.
        self.audit.append('PARSED',{'status':result['status'],'source':result['source']})
        return result
    def propose(self,profile,constraints,role='READ',**params):
        if role!='PROPOSE':
            self.audit.append('DENIED',{'action':'propose','reason':'role'})
            return {'status':'DENIED','message':'PROPOSE capability required'}
        result=solve(self.data,Profile.parse(profile),constraints,previous=self.weights,**params)
        if result['status']=='PROPOSED':
            result['account_revision']=self.revision
            result['nav_before']=self.nav
            result['proposal_id']=digest(result)
            result['expires_at_monotonic']=self.clock()+300
            self.proposals[result['proposal_id']]=copy.deepcopy(result)
        self.audit.append('PROPOSAL',result)
        return copy.deepcopy(result)
    def approve(self,proposal_id,confirmed=False,role='READ'):
        p=self.proposals.get(proposal_id)
        if role!='APPROVE_SIM' or confirmed is not True or not p or p['account_revision']!=self.revision or self.clock()>p['expires_at_monotonic']:
            self.audit.append('DENIED',{'action':'approve','reason':'role, confirmation, missing, expired or stale proposal'})
            return {'status':'DENIED'}
        token=secrets.token_urlsafe(32)
        # Invalidate previous approvals for this proposal.
        self.tokens={t:v for t,v in self.tokens.items() if v!=proposal_id}
        self.tokens[token]=proposal_id
        self.audit.append('APPROVED',{'proposal_id':proposal_id,'revision':self.revision})
        return {'status':'APPROVED','approval_token':token,'proposal_id':proposal_id}
    def execute(self,proposal_id,token,role='READ'):
        p=self.proposals.get(proposal_id)
        if role!='APPROVE_SIM' or not isinstance(token,str) or self.tokens.get(token)!=proposal_id or not p or p['account_revision']!=self.revision or self.clock()>p['expires_at_monotonic']:
            self.audit.append('DENIED',{'action':'execute','reason':'missing approval, replay, expiry or stale proposal'})
            return {'status':'DENIED','message':'No account change'}
        # Write audit before mutation; logging failure aborts execution.
        before=self.nav; fee=before*p['metrics']['estimated_rebalance_cost_fraction']; after=before-fee
        target=[p['weights'][k] for k in IDS]
        trades={k:after*target[i]-before*self.weights[i] for i,k in enumerate(IDS)}
        result={'status':'SIMULATED','proposal_id':proposal_id,'nav_before':before,'fee':fee,
                'nav_after':after,'weights_before':list(self.weights),'weights_after':target,
                'dollar_changes':trades,'revision':self.revision+1,
                'disclosure':'Fractional notional rebalance at unchanged prices, fee charged on pre-fee L1 turnover. No real orders.'}
        self.audit.append('SIMULATED_REBALANCE',result)
        self.nav=after; self.weights=target; self.revision+=1; self.tokens.clear()
        return result
