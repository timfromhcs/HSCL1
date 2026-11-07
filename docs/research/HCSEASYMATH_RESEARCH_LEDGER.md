# HCSEASYMATH research ledger

Companion to `AGENTS_HCSEASYMATH_HSCL1_FIRST.md` (owner file, untracked) and
`docs/superpowers/plans/2026-11-08-hcseasymath-plan.md`. Each row says what was
looked at, when, what it showed, and what it does **not** show. A link is not
evidence that a tool was installed or validated.

Review date: **2026-11-07/08**. Three consecutive research rounds, each more specific than the last.
Sources are web pages and registries read through the Firecrawl MCP, `pip` resolution on this
machine, and `apt-cache` in the WSL Ubuntu 26.04.1.

## Round 1 - platform and specification facts

| Question | Finding | Evidence | Limits |
|---|---|---|---|
| Does SymPy support parsing untrusted text? | No. `parse_expr` is built on `eval`; SymPy's own best-practice page says "avoid string inputs"; issue #10805 ("sympify shouldn't use eval") is the standing upstream record. | docs.sympy.org/latest/modules/parsing.html, .../explanation/best-practices.html (SymPy 1.14.0), github.com/sympy/sympy/issues/10805 | I did not run an exploit; the design decision (own AST parser) does not depend on one. |
| Which MCP revision is current, and what is the localhost guidance? | Spec revisions up to 2025-11-25 and a 2026-07-28 docs tree exist. Streamable HTTP servers must validate `Origin`, should bind to 127.0.0.1, and DNS rebinding is the named attack; stdio avoids it. The Python SDK had CVE-2025-66416 (DNS rebinding protection off by default for local servers), fixed in `mcp` 1.23.0. | modelcontextprotocol.io/specification/2025-11-25/basic/transports, .../docs/2026-07-28/tutorials/security/security_best_practices, NVD CVE-2025-66416 | I read search excerpts, not the full spec text. |
| What Python does the target OS have? | Ubuntu 26.04 LTS ships **Python 3.14** (resolute `python3.14-venv` 3.14.4-1); `python3-venv` is not in the pristine base. | linuxcapable.com guide, packages.ubuntu.com/resolute, **confirmed locally**: WSL Ubuntu 26.04.1 reports Python 3.14.4 and `python3.14-venv` 3.14.4-1ubuntu0.2 installed | The ISO's own package set was not inspected here. |
| Is Three.js `WebGPURenderer` usable? | Yes with fallback: it uses WebGPU when present and falls back to WebGL 2; three.js is at r187 (npm 0.187.0); Linux WebGPU support is described as partial. | threejs.org/docs/pages/WebGPURenderer.html, utsubo.com changelog article, npm registry | Third-party blog for the "partial Linux" statement. A VM without a GPU will likely render WebGL2 in software: **not measured**. |

## Round 2 - exact versions, wheels, licences

| Question | Finding | Evidence | Limits |
|---|---|---|---|
| Do the planned Python dependencies exist as **wheels for Python 3.14 on manylinux**? | Yes. `pip install --dry-run --only-binary=:all: --python-version 3.14 --abi cp314 --platform manylinux_2_28_x86_64 ...` resolved 34 packages with no source builds: numpy 2.5.4, scipy 1.18.1, sympy 1.14.0, fastapi 0.162.2, pydantic 2.14.3, pydantic_core 2.50.4, starlette 1.10.0, uvicorn 0.54.0, hypothesis 6.170.15, pytest 9.2.0, httpx 0.28.1. | resolve report kept in the session scratchpad; command in `HCSEASYMATH_DECISIONS.md` D2 | Resolved from a Windows host; nothing was installed or executed on Python 3.14. Versions move: re-resolve when the lock is written. |
| Licences of those packages | From the wheels' own metadata: MIT / BSD / Apache / PSF; `certifi` and `hypothesis` are MPL-2.0 (`hypothesis` is test-only, `certifi` arrives via the test-only `httpx`); numpy's expression adds 0BSD/Zlib/CC0; **scipy's field is only the head of a composite licence text** (read `LICENSE.txt` when locking). All are compatible with GPL-3.0-or-later for use; none is bundled yet. | wheel metadata in the resolve report | Not a legal review (owner item). |
| Frontend pins | mathlive 0.111.4 (MIT), katex 0.19.1 (MIT), three 0.187.0 (MIT), react 19.3.1 (MIT), vite 8.3.6 (MIT, needs Node ^20.19 or >=22.12). Host Node is 22.23.1. | npm registry records incl. integrity hashes | `package-lock.json` not generated yet. |
| MCP Python SDK | Now on a **2.x** major (2.3.0); 1.x continues to 1.30.0. A resolve error on Windows (`pywin32` marker) was an artefact of the Windows host, not a Linux problem. | pip index, resolver output | Not needed: see decision D3. |
| Optional tools on Ubuntu 26.04 | `macaulay2` is in resolute at **1.25.11+ds-4** (WSL `apt-cache policy`); upstream stable is 1.26.06 (2026-06-10). Lean 4 / Mathlib: install via elan and a Mathlib cache; **size not measured**. | packages.ubuntu.com, macaulay2.com repository page, `apt-cache policy` | Macaulay2 not installed or run here. Lean's and Mathlib's licences were not re-read in this session. |

## Round 3 - domain facts

| Question | Finding | Evidence | Limits |
|---|---|---|---|
| What is the Stoikov micro-price? | The limit of a sequence of expected mid-prices; a martingale by construction; expressible as `mid + g(imbalance, spread)` estimated from a finite-state Markov chain (adjustment `G*`); empirically better than mid or weighted mid. The size-weighted mid is therefore **not** the micro-price. | SSRN 2970694 abstract; arXiv 2411.13594 review section; sstoikov/microprice repo (notebook + data, last commit 2020-06) | The paper's estimator details (state discretisation, `G1`, `B*`) were not read in full. Only the labelling rule is settled; implementing the estimator needs the full text. |
| Exact Macaulay2 call for `Tor` over `k[x]` | **Not found.** Searches returned the BeginningMacaulay2 and DGAlgebras pages, not a verified one-liner. | macaulay2.com docs hits | Open: resolve by running M2 1.25.11 at milestone M5. Do not write the call from memory into a test. |
| SOT-MRAM / LLG conventions | The contract's own warning stands: sign and effective-field conventions differ between communities. The three cited papers were **not read** this session. | contract section 3.3 | Open: read arXiv 2207.12071 before fixing a convention (M4). |
| SymPy denial-of-service mitigations | The search returned nothing specific. Design relies on general practice: resource caps and a killable worker process. | - | Unverified practice, to be proven by a test that a hostile input is stopped (see plan, M1). |

## Negative results

- A single `pip` resolve including `mcp` failed on the Windows host because of a `sys_platform == "win32"` dependency; this was misread as a conflict until the cause line was shown.
- The first SymPy-DoS search found only unrelated `requests` timeout pages.
