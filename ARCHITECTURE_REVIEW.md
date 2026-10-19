# Architecture decision record: AEGIS 2.0

Decision: replace the original runtime with a smaller, auditable advisory
simulator. Retain the AEGIS identity and the idea of distributional robustness.
Do not retain the original numerical API or performance claims.

## Concrete findings in the uploaded source

| Original location | Finding | Release decision |
|---|---|---|
| `aegis_agent.py`, `_run_bull_bear_epistemic_debate` | Fixed prose and constants selected by keywords. No LLM invocation or measured disagreement. | Remove debate and epistemic-confidence claims. Add optional real HTTP parser with strict validation and explicit untested-live status. |
| `aegis_agent.py`, `compile_client_mandate` | Generic liquidity language becomes a joint SHV/IEF/TLT/GLD floor, conflating cash with duration and gold risk. Defaults and trigger words insert constraints not explicitly requested. | Separate explicit profile policy from confirmed product-specific bounds. Unknown prose requires clarification. |
| `aegis_dro_engine.py`, `solve_wasserstein_dro` | Daily CVaR multiplied by sqrt(252), annual expected returns, and an unexplained 0.15 factor enter an asserted exact dual. No consistent definition justifies the stated exactness. | Define daily robust epigraph objective with l1 ground metric and derive its exact LP. No annual CVaR claims. |
| Same | User constraints always have penalized elastic slacks. A finite penalty of 50 is neither a computed exact-penalty threshold nor an IIS algorithm. | Hard bounds. Conflict produces NEEDS_REVISION. No automatic repair. |
| Same | Accepts any non-null solver weight, clips and normalizes it, and uses fallback market weights without checking every client constraint. | Require successful status, independently verify bounds and reconstruct objective. No unvalidated fallback portfolio. |
| Same, covariance and prior | Fixed 12-vector market prior is incompatible with arbitrary data dimensions. Unknown tickers in views/constraints are silently skipped. | Fixed documented six-sleeve universe, strict dimensions and product IDs. |
| `aegis_agent.py`, report | Zero slacks asserted to verify Slater; zero dual asserted nonbinding. Neither inference is valid. Finite dual changes advertised as exact counterfactuals. | Report primal slacks and local right-hand-side derivatives with sign convention and limitations. |
| `c_accelerator.py`, `_load_or_compile` | Looks for `src/c_extensions/aegis_c_core.c`; ZIP instead contains `c_extensions/aegis_c_core.c`. Expected source directory is empty. | Remove import-time compiler and native binding. |
| C `solve_wdro_socp_ipm_c` | Fixed 220-step smoothed accelerated-gradient loop, not a certified primal-dual IPM; no convergence certificate and no user constraints. | Remove custom C solver. Use the compiled HiGHS implementation distributed with SciPy. |
| C mmap logger | World-mode creation mask before umask, fixed-size overwrite ring, no locking/signature. Python fallback can differ from advertised native telemetry. | Session-local readable hash-chained JSONL, with unsigned/local limits explicitly disclosed. |
| `evaluate_all_benchmarks` and app | One train/test split called walk-forward. Generated regimes labeled as specific historical episodes. A manually selected portfolio labeled a naive LLM benchmark. | Actual trailing-window synthetic experiment; no invented LLM or historical performance comparator. |
| Same | CVaR uses percentile-tail averaging, with possible fractional-mass/tie errors; drawdown omits initial wealth. Baseline settings differ. | Exact empirical CVaR identity, initial NAV in drawdown, matched robust/empirical settings. |
| Original paper/PDF | Numeric performance, hallucination immunity and minimal unsatisfiable-core claims are not supported by delivered code. ZIP contains PDFs but no raw LaTeX sources. | Replace documents entirely with source-aligned raw LaTeX and compiled PDFs. |

## Why remove rather than preserve the model stack?

Gerber covariance and Black–Litterman are legitimate techniques in appropriate
models. The problem here is unsupported calibration, mismatched claims and too
many execution paths for the submission window. Neither is necessary for the
chosen scenario-based LP. Removing them shrinks the failure surface and makes
the assumptions reviewable. This is an engineering decision, not a claim those
methods are invalid.

The new model also has limitations: arbitrary illustrative ambiguity radius,
unrestricted mathematical stress support, noisy sample means, fictional
products, local-only permissions and no live semantic evaluation. They appear
in the technical document and risk register rather than being hidden.

## Preserved strengths

- Explicit portfolio constraints and mathematical optimization.
- Distributional uncertainty as an inspectable model component.
- Numerical explanations and reproducible simulation evidence.
- Team attribution from the original source (verify spelling/affiliations).

## Deliberately not shipped

Original stale PDFs, performance plots, compiled bytecode, mmap files, old test
claims and misleading C telemetry are excluded from the final package. The
uploaded original is untouched outside this new release directory.
