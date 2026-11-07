# HCSEASYMATH blockers and owner decisions

| ID | Item | Type | Effect | Next step |
|---|---|---|---|---|
| B1 | Creating `timfromhcs/hcseasymath` | owner | Not needed before milestone M12; the contract forbids creating it early | none until the extraction gate passes |
| B2 | Licence of the standalone repo | owner | In-tree code follows GPL-3.0-or-later; a later change needs an owner decision | keep GPL-3.0-or-later |
| B3 | Python 3.14 wheels on GitHub-hosted runners | unknown | CI must build the lock on 3.14; availability of `setup-python` 3.14 on `ubuntu-latest` was **not checked** | check when writing the workflow; fall back to a container-less `apt` python3.14 step |
| B4 | Exact Macaulay2 `Tor` call | research gap | blocks the M5 cross-check test | run M2 1.25.11 interactively in WSL at M5, record the transcript |
| B5 | Stoikov estimator details | research gap | blocks implementing the full micro-price (M4) | read the SSRN paper's estimator section; until then ship only the labelled proxy |
| B6 | SOT-MRAM convention | research gap | blocks the macrospin model (M4) | read arXiv 2207.12071, write the convention into `MATHEMATICAL_CONTRACTS.md` first |
| B7 | Lean/Mathlib size and licence re-check | research gap | blocks any Lean adapter promise | measure download with consent at M8+, never in the ISO |
| B8 | VM rendering of WebGL2 | unmeasured | decides whether the optional 3D view is usable in the ISO | measure in the QEMU guest at M10 |
