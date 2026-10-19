# AEGIS: inspectable wealth advisory simulator

**2026 Shenzhen International FinTech Competition — International Track, Topic B**

Stefano Bloise and Fahd Mounir, as attributed in the uploaded source.

AEGIS compares fictional model products, collects an explicit risk profile,
interprets and confirms portfolio bounds, solves a robust daily mean-CVaR LP,
and requires approval for a simulated rebalance. Conflicting mandates produce
`NEEDS_REVISION`; solver failure produces `UNAVAILABLE`. Neither authorizes a trade.

**Scope:** local single-user research demo. All returns and products are
synthetic. No broker, real order, return guarantee or regulatory certification.
The optional LLM adapter is implemented, but only injected responses and failure
cases were tested here. The original runtime has been replaced, not maintained
as a backward-compatible API. Read `ARCHITECTURE_REVIEW.md` for the reasons.

## Immediate start

Tested: Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, Linux. No C compiler is needed.
From the extracted `AEGIS_Submission` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python app.py
```

Open **http://127.0.0.1:8765** (use this exact address, not `localhost`).
On Windows use `py -3.12 -m venv .venv` and `.venv\Scripts\activate`.
If pinned binary wheels are unavailable for your Python version/platform,
use Python 3.12 or the separately provided `requirements-portable.txt`, then
rerun the tests. Results on an untested environment are not certified.

1. Compare product fees and principal risks.
2. Review the five profile fields; defaults form a fictional growth profile.
3. Click **Interpret mandate**. The offline example is
   `TECH <= 15%; BOND >= 20%; CASH >= 15%`.
4. Inspect the draft, check its confirmation box, then **Create proposal**.
5. Review allocation, daily risk, constraint audit and cost.
6. Check the simulation approval box, click **Approve simulation**, then
   **Execute approved simulation**. The generated account receipt is real
   execution evidence from the local simulator, not a broker fill.

Restarting starts a new account. Runtime logs go to `runs/`; do not publish real
client profiles. Bind only to the loopback address. This server is not intended
for public or multi-user deployment.

CLI alternative, with explicit approval of one **simulated** rebalance:

```bash
python -m aegis
python -m aegis --simulate-approved
```

## Optional LLM parser

Set `OPENAI_API_KEY` in your shell or secure local environment. Do not commit it.
Optionally set `AEGIS_LLM_MODEL` to a model available to your account that supports
the chat-completions JSON-object request format (default: `gpt-4.1-mini`).
Enable LLM mode and consent in the UI. Only the dialogue text is sent.

The adapter uses HTTPS, a fixed endpoint, a 12-second timeout, a response-size
limit and local strict validation. It does not have tool access or permissions.
Unknown or invalid output returns `UNAVAILABLE`; ambiguous output asks for
clarification. A valid interpretation still requires review. Test your actual
key/model before relying on this mode in a live presentation. The default
offline mode requires no API key, network connection or model download.

## Deliverable map

| Item | Included artifact |
|---|---|
| 01 Technical documentation | `docs/01_technical.tex` and compiled PDF |
| 02 Presentation, <=10 minutes | `docs/02_pitch.tex`, 10-slide PDF, `docs/02_speaker_notes.md` (9:30 script) |
| 03 Demo video | `evidence/03_06_demo_replay.mp4`, 96-second silent captioned replay of actual local run outputs |
| 04 Source, README, deployment, tests | `aegis/`, `app.py`, `ui.html`, `tests/`, requirements, Dockerfile, tools |
| 05 Security assessment | `docs/05_security.tex` and compiled PDF |
| 06 Execution evidence | `evidence/session/`, `evidence/tests.log`, benchmark JSON and the operation replay |

**Public source repository:** https://github.com/StefanoBloise/aegis-wealth-advisor

The repository contains the source, tests, deployment instructions and editable
LaTeX. The final submission ZIP contains the compiled PDFs, synthetic logs and
demo replay as well. `SUBMISSION_STATUS.json` records the repository and the
team tasks that remain outside this software package.

The video is explicitly an output replay from an executed local session, not a
screen recording of browser clicks, a live LLM session or an organizer-hosted
sandbox. If the organizer requests a screen recording, record the six-step UI
workflow above. The source checklist calls video optional under 03 but also
lists it under 06; the supplied video covers the more conservative reading.

## Evidence and model assumptions

- 51 passing test methods; the randomized method contains 40 optimizer cases.
- Seven asserted evidence scenarios and nine chained audit records.
- Example: 20% BOND, 80% CASH, USD 4 fee, final NAV USD 99,996.
- The explicit BOND floor drives that position; with negative sample means and
  no investment floor, retaining cash is a legitimate result.
- Data: seed 42, 252 observations, generated factor returns plus a designed
  stress segment. No dates or historical-crisis performance labels.
- UI parameters: gamma 0.02, epsilon 0.00002, alpha 0.95, transaction cost 1 bp
  on full L1 turnover. All objective terms use daily return fractions, with
  rebalance cost charged once for the one-day decision.
- Risky products have a 35% cap. Aggregate risk is determined by the profile;
  CASH may exceed 35%. Stated loss tolerance is a policy input, not a loss bound.
- Wasserstein ground norm is l1 on risky returns; the penalty uses infinity
  norm. The technical document specifies the unrestricted support and derives
  the robust epigraph LP. Radius and policy thresholds are illustrative.
- Local duals are objective sensitivity to the written RHS, not finite profit
  counterfactuals or a proof of strict feasibility.
- Hash chains detect changes relative to a retained head, but without an
  external trusted anchor they cannot prevent wholesale rewriting/truncation.

The synthetic walk-forward benchmark uses seed 73, matched robust/empirical
settings, trailing training windows, drift, and transaction costs. Its result
includes a case where the empirical model slightly outperforms the robust one.
There is no cherry-picked claim of dominance or historical performance.

## Reproduce evidence

```bash
python -m unittest discover -s tests -v
python tools/generate_evidence.py --out evidence/new_session
python tools/benchmark.py
```

Evidence generation refuses to overwrite an existing session directory. The
included snapshot remains intact. To regenerate the video from the included
session outputs, install Pillow, FFmpeg and DejaVu Sans Mono, then run:

```bash
python -m pip install Pillow
python tools/render_demo.py
```

This optional renderer is not required to run the agent. Its font path is
Linux-specific and clearly defined in the source. The packaged video is ready
to use. The 51 tests require only the main numerical dependencies and stdlib.

## Compile LaTeX and generate the final ZIP

Install a TeX distribution containing pdfLaTeX, Beamer, Latin Modern and the
standard packages used in the `.tex` files. The PDFs were successfully compiled
with pdfLaTeX and visually inspected in this build.

From the release root, run:

```bash
python tools/build.py --repo-url https://github.com/StefanoBloise/aegis-wealth-advisor
```

The command runs all tests,
compiles each document twice, verifies the audit chain, writes `MANIFEST.sha256`
and creates **`../AEGIS_Final_Submission.zip`**. It records the URL but does not
publish or verify the GitHub repository.

If you only need to package the included PDFs and cannot install LaTeX:

```bash
python tools/build.py --skip-latex --repo-url https://github.com/StefanoBloise/aegis-wealth-advisor
```

For a local review ZIP without the repository link:

```bash
python tools/build.py
```

The script will flag the remaining URL requirement. It excludes virtual
environments, generated build intermediates, personal runtime logs and bytecode.
Preserve the included synthetic evidence and third-party notices when publishing.

## Docker recipe (not executed in this build)

```bash
docker build -t aegis-demo .
docker run --rm aegis-demo
```

The default container command runs the approved **CLI simulation**. It does not
expose the web interface. Network package installation and Docker itself are
required to build this optional image. No container runtime is bundled.

## Submission checklist before sending

- Include the public repository URL above in the submission email.
- Review team identity, source ownership and competition independent-work terms.
  The release contains substantial AI-assisted refactoring; no unsupported
  declaration of independent authorship has been made for the team.
- Complete official registration and passport documents separately; never put
  personal identity documents or API keys in the source repository.
- Rehearse the 9:30 pitch and inspect the 96-second video.
- Deadline from the official Beijing timestamp: **20 October 2026, 23:59 UTC+8
  = 15:59 UTC = 17:59 Europe/Rome**.

Rules: https://drive.scmc.cmu.ac.th/s/2jKErkTJpFmcxYF
Official site: https://fintechathon.g-ican.com/#/en
The source screenshot and downloaded organizer PDF agree on the six categories.
No submission email has been sent by this build.
