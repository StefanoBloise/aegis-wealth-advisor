"""Render a clearly labeled replay of real local execution outputs, 96 seconds."""
import json
import subprocess
import textwrap
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]

def main():
    session=ROOT/'evidence/session'
    frames=json.loads((session/'demo_frames.json').read_text())
    target=ROOT/'build/video_frames';target.mkdir(parents=True,exist_ok=True)
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    if not Path(font_path).exists():
        raise SystemExit('Install DejaVu fonts or edit font_path in tools/render_demo.py')
    font=ImageFont.truetype(font_path,22);title=ImageFont.truetype(font_path,34);small=ImageFont.truetype(font_path,18)
    for i,frame in enumerate(frames):
        body=frame['body']
        if i==0:
            lines=['FICTIONAL PRODUCT COMPARISON','']
            for p in body['products']:
                lines += [f"{p['id']:7} {p['name']} | fee {p['fee_bps']} bps/year",p['risk'],'']
        elif i==2:
            lines=['Actual proposal output: '+body['status'],'', 'Confirmed profile: '+body['profile']['risk']+', horizon 7 years','']
            lines += [f'{k:7} {100*v:7.2f}%' for k,v in body['weights'].items()]
            lines += ['',f"Daily empirical CVaR: {100*body['metrics']['daily_cvar']:.5f}%",f"Daily robust CVaR envelope: {100*body['metrics']['daily_robust_cvar']:.5f}%",'', 'The BOND floor is a client instruction.', 'Without it, this sample favors cash.']
        elif i==4:
            lines=['Actual execution receipt','', 'Status: '+body['status'],f"NAV before: USD {body['nav_before']:,.2f}",f"Fee: USD {body['fee']:,.2f}",f"NAV after: USD {body['nav_after']:,.2f}",'', 'Post-rebalance weights: '+str(body['weights_after']),'','Fractional notional account. No live broker or real orders.','Approval was explicit and tied to the stored proposal.']
        else:
            lines=json.dumps(body,indent=2).splitlines()
        wrapped=[]
        for line in lines:wrapped.extend(textwrap.wrap(line,width=91,replace_whitespace=False,drop_whitespace=False) or [''])
        if len(wrapped)>31:raise RuntimeError(f'Frame {i} overflows: {len(wrapped)} lines')
        im=Image.new('RGB',(1440,1080),'#101724');d=ImageDraw.Draw(im)
        d.text((60,35),'AEGIS / LOCAL EXECUTION REPLAY',font=small,fill='#73e1c1')
        d.text((60,85),frame['title'],font=title,fill='white')
        for j,line in enumerate(wrapped):d.text((60,160+j*26),line,font=font,fill='#c8d4e4')
        d.text((60,1000),'Actual run outputs | Synthetic data | Mock LLM tests only | No live orders',font=small,fill='#ffce8b')
        d.text((60,1035),f'{i+1}/8   Reproduce: python tools/generate_evidence.py --out evidence/new_session',font=small,fill='#c8d4e4')
        im.save(target/f'frame{i:02d}.png')
    subprocess.run(['ffmpeg','-y','-framerate','1/12','-i',str(target/'frame%02d.png'),'-c:v','libx264','-r','24','-pix_fmt','yuv420p','-movflags','+faststart',str(ROOT/'evidence/03_06_demo_replay.mp4')],check=True)

if __name__=='__main__':main()
