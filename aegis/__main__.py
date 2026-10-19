import argparse
import json
from pathlib import Path
from .core import InputError
from .service import Advisor

def main():
    p=argparse.ArgumentParser(description='AEGIS local synthetic advisory simulator')
    p.add_argument('--profile',default='examples/profile.json')
    p.add_argument('--constraints',default='examples/constraints.json')
    p.add_argument('--simulate-approved',action='store_true',help='Explicitly approve one simulated rebalance; no real money')
    args=p.parse_args()
    try:
        a=Advisor(); result=a.propose(json.loads(Path(args.profile).read_text()),json.loads(Path(args.constraints).read_text()),role='PROPOSE',gamma=.02,epsilon=.00002,cost_bps=1)
        print(json.dumps(result,indent=2,allow_nan=False))
        if args.simulate_approved and result['status']=='PROPOSED':
            auth=a.approve(result['proposal_id'],confirmed=True,role='APPROVE_SIM')
            print(json.dumps(a.execute(result['proposal_id'],auth['approval_token'],role='APPROVE_SIM'),indent=2))
    except (InputError,OSError,ValueError) as e:
        print(json.dumps({'status':'INVALID_INPUT','message':str(e)}))
        return 2
    return 0

if __name__=='__main__':
    raise SystemExit(main())
