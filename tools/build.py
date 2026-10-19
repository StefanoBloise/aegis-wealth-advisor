"""Validate, compile LaTeX twice, hash final files, and package a submission ZIP."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

EXCLUDE_PARTS={'__pycache__','.git','.venv','build','runs'}
EXCLUDE_SUFFIX={'.pyc','.aux','.nav','.out','.snm','.toc','.vrb','.fls','.fdb_latexmk'}

def included(p):
    rel=p.relative_to(ROOT)
    return not any(x in EXCLUDE_PARTS for x in rel.parts) and p.suffix not in EXCLUDE_SUFFIX and not (p.suffix=='.log' and p.parent.name=='docs') and not p.name.startswith('.env')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-url');ap.add_argument('--skip-latex',action='store_true',help='Retain included PDFs without rebuilding');args=ap.parse_args()
    if args.repo_url:
        if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?',args.repo_url):
            raise SystemExit('Provide a real https://github.com/owner/repository URL')
        p=ROOT/'SUBMISSION_STATUS.json';status=json.loads(p.read_text());status['github_repository_url']=args.repo_url
        status['team_action_required']=[x for x in status['team_action_required'] if not x.startswith('Add the actual GitHub')]
        p.write_text(json.dumps(status,indent=2)+'\n');(ROOT/'REPOSITORY_URL.txt').write_text(args.repo_url+'\n')
    with (ROOT/'evidence/tests.log').open('w') as log:
        subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    if not args.skip_latex:
        if not shutil.which('pdflatex'):raise SystemExit('Install a TeX distribution or use --skip-latex with the included PDFs')
        for name in ['01_technical','02_pitch','05_security']:
            for _ in range(2):
                run=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error',name+'.tex'],cwd=ROOT/'docs',capture_output=True,text=True)
                if run.returncode:raise SystemExit(run.stdout[-4000:])
    for name in ['docs/01_technical.pdf','docs/02_pitch.pdf','docs/05_security.pdf','evidence/03_06_demo_replay.mp4','evidence/session/sandbox_operations.jsonl']:
        if not (ROOT/name).is_file():raise SystemExit('Missing deliverable: '+name)
    sys.path.insert(0,str(ROOT))
    from aegis.service import Audit
    rows=[json.loads(x) for x in (ROOT/'evidence/session/sandbox_operations.jsonl').read_text().splitlines()]
    if not Audit.verify(rows):raise SystemExit('Audit chain failed validation')
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and included(p) and p.name!='MANIFEST.sha256')
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files)
    (ROOT/'MANIFEST.sha256').write_text(manifest)
    out=ROOT.parent/'AEGIS_Final_Submission.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files+[ROOT/'MANIFEST.sha256']:z.write(p,'AEGIS_Submission/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(out) as z:
        if z.testzip():raise SystemExit('ZIP integrity check failed')
    print(out)
    status=json.loads((ROOT/'SUBMISSION_STATUS.json').read_text())
    if not status['github_repository_url']:print('TEAM ACTION: add your actual GitHub repository URL before submission.')

if __name__=='__main__':main()
