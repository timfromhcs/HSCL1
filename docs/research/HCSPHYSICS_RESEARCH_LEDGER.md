# HCS Physics research ledger (PHYS-0)

Status: **PHYS-0 = research and numerical contract only. No physics engine code exists and none may be written before the
CPU reference gate below.** Physics is not a new top-level priority: the Unified Master (`AGENTS_HCS_UNIFIED_SELF_HEALING_RESEARCH_MASTER_2026-11-08.md`,
sections 8-11 and 27) allows it only as a sub-track of the one live ledger, PHYS-0 under P0/P4 and PHYS-1 after the core gates. The ledger
(`docs/superpowers/plans/2026-11-08-selfheal-masterplan.md`) holds the order; this file holds facts and evidence.

Honesty note: the supplied PDF ("Suche von leicht bis schwer sota research ...", four physics levels) is **not in this repository and was not
available to this project**. Everything below about its content is taken from the contract's summary, and the contract itself calls it an
architecture outline, not a validated numerical specification.

## 1. Claims of the contract checked by experiment (2026-11-08)

Experiment: `docs/research/hcsphysics/integrator_check.py` (numpy, ~1 s). Problem: pendulum `H = p^2/2 - cos q`, `q0 = 1`, `p0 = 0`.
Reference solution: Yoshida triple jump with 20000 steps over T = 10. Coefficients are the published Forest-Ruth / Yoshida 1990 values
(c1=c4=1/(2(2-2^(1/3))), c2=c3=(1-2^(1/3))/(2(2-2^(1/3))), d1=d3=1/(2-2^(1/3)), d2=-2^(1/3)/(2-2^(1/3)), d4=0; source: Wikipedia
"Symplectic integrator" citing Forest and Ruth 1990, SLAC-PUB-5071; triple jump: arXiv 2106.06503).

| Method | Expected order | Measured slopes (N = 100,200,400,800 over T=10) | max abs(det J - 1) at h=0.2 | max abs energy error, T=10000, h=0.1 |
|---|---|---|---|---|
| explicit Euler | 1 | 1.13, 1.08, 1.04 | 3.8e-2 | 3.3e+2 |
| leapfrog (velocity Verlet) | 2 | 2.0, 2.0, 2.0 | 4.6e-11 | 1.1e-3 |
| classical RK4 | 4 | 3.96, 3.98, 3.99 | **8.5e-7** | 4.6e-4 |
| Forest-Ruth | 4 | 3.99, 4.0, 4.0 | 9.4e-11 | 7.4e-7 |
| Yoshida triple jump | 4 | 4.0, 4.0, 4.0 | 1.8e-10 | 3.9e-6 |

What this supports (contract section 9, each point with its evidence):

- **9.2 `symplectic_rk4` is not a thing.** Classical RK4 has order 4 but its one-step map is not area preserving: `|det J - 1|` is 8.5e-7, about four orders
  of magnitude above the three symplectic methods (rounding level, ~1e-10). A fourth-order symplectic method is a different composition with its own coefficients.
- **9.1 Symplectic does not mean exact energy conservation.** The symplectic methods' energy error oscillates and stays bounded (leapfrog 2e-5 to 1e-3;
  Forest-Ruth 3e-9 to 7e-7 over 100000 steps) and never becomes zero.
- **Drift versus bounded error.** RK4's energy error grows linearly (4.6e-5 at the first sample, 4.6e-4 at the tenth). Within this 10000-time-unit run its
  maximum (4.6e-4) is still smaller than leapfrog's bounded 1.1e-3, so "symplectic always gives the smaller error" is false on a short horizon; the point is
  the trend (growing versus bounded). Do not write a general advantage claim from this one run.
- Order claims for the method registry are now measured, not quoted.

Not tested here: adaptive step sizes (9.3), reproducibility levels R0-R4 (9.4), residual versus error bound (9.6), memory semantics (9.7), hashes (9.8). Those are
statements about definitions and must be enforced in the schema and in review, not by this experiment.

## 2. Method registry rules carried over from the contract (to be enforced when code exists)

- Exact identifiers only (`velocity_verlet`, `leapfrog`, `forest_ruth`, `yoshida_triple_jump`, `rk4`); no alias such as `symplectic_rk4`.
- Each entry declares: fixed or variable step, explicit or implicit, symplectic or not, order, constants and their source, citation, and the invariants that are
  measured (not assumed).
- Reproducibility level is recorded per run: R0 exact, R1 same-device bitwise replay, R2 same-platform bounded replay, R3 cross-platform tolerance, R4 independently reproduced.
  A state hash proves an exact trace, not a correct model.
- A residual is not an error bound. Report residual, discretisation error estimate, time-integration error, round-off estimate and model uncertainty separately;
  rigorous enclosures need interval or ball arithmetic (FLINT/Arb) or a checked certificate.

## 3. Gate before any physics code (PHYS-1 entry)

1. This ledger plus a numerical-method specification reviewed by the owner.
2. A scene/experiment schema and an evidence-record schema (extends `hcs.run.v2`; no second provenance format).
3. A CPU reference for a deterministic mechanics problem (pendulum, Kepler) with golden values, order-of-convergence tests and the invariant diagnostics above.
4. Only then a GPU path, with the CPU reference as oracle and the HCSUDA planner contract (no private Vulkan stack).

## 4. Literature named for later levels (status: NOT READ)

MPM and SPH (continuum, medium level), iPEPS/CTMRG with QR (quantum many body), GRACE numerical relativity, PINNs and neural operators as optional surrogates,
FLINT/Arb ball arithmetic and LeanCert certificates (rigorous numerics). The contract's own caveats apply: an H100 speed-up does not transfer to a Radeon 680M, a
surrogate does not replace a numerical solver, and no level claims physical accuracy for every material.
