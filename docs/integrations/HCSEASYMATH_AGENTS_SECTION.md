# Proposed `AGENTS.md` section for HCSEASYMATH (proposal only)

This text is **not** applied to the root `AGENTS.md`; the owner decides. It follows the
pattern of `HCSWAVER_AGENTS_SECTION.md`.

> ### HCSEASYMATH (companion product, in-tree first)
>
> HCSEASYMATH is a local calculation, simulation and verification workbench. It is built
> inside this repository under `apps/hcseasymath/` and integrated through `hscl math`,
> typed `hscl mcp` tools, a Control Center card and a small Debian package. It is extracted
> into its own repository only after the in-tree acceptance gates and a clean-checkout test
> pass.
>
> Rules that bind every change to it:
>
> 1. No evaluation of user text with `eval`, `exec`, `sympify` or `parse_expr`; expressions go
>    through the allow-list parser.
> 2. A language model never decides mathematical truth.
> 3. The CPU path is the reference; acceleration (HCSUDA) is optional and used only when its
>    own evidence matches the device and operation.
> 4. The API listens on loopback only, only while the app runs, and validates `Host`, `Origin`
>    and a per-launch token.
> 5. No model weights, solvers or datasets are added to the ISO; optional downloads need
>    visible consent, size, source and hash.
> 6. Results are labelled with their exactness (`symbolic_exact`, numerical with precision,
>    `unresolved`, `unsupported`); proxies (for example a weighted mid) are never named after
>    the full estimator they approximate.
> 7. No live trading, no clinical or device-qualification claims.
