"""PHYS-0 experiment: check the integrator claims of the Ecosystem contract (section 9) before any physics code exists.

Claims checked, on the nonlinear pendulum H = p^2/2 - cos(q):
  1. The order of convergence of each method (Euler 1, leapfrog 2, RK4 4, Forest-Ruth 4, Yoshida triple jump 4).
  2. A symplectic method has a one-step map with Jacobian determinant exactly 1 (up to rounding); explicit RK4 does not.
  3. Over a long run a symplectic method keeps the energy error bounded, RK4's error drifts.
  4. Symplectic does not mean the energy is conserved exactly: the error oscillates, it does not vanish.

Run:  python docs/research/hcsphysics/integrator_check.py        (needs numpy)
This is a research check, not product code. Coefficients are the published ones (Forest and Ruth 1990, Yoshida 1990).
"""

from __future__ import annotations

import json
import math

import numpy as np

TWO13 = 2.0 ** (1.0 / 3.0)


def force(q):
    return -math.sin(q)  # H = p^2/2 - cos q  ->  dp/dt = -sin q


def energy(q, p):
    return 0.5 * p * p - math.cos(q)


def euler(q, p, h):  # explicit Euler: order 1, not symplectic
    return q + h * p, p + h * force(q)


def leapfrog(q, p, h):  # velocity Verlet: order 2, symplectic
    p = p + 0.5 * h * force(q)
    q = q + h * p
    p = p + 0.5 * h * force(q)
    return q, p


def rk4(q, p, h):  # classical explicit RK4: order 4, NOT symplectic
    def f(q, p):
        return p, force(q)

    k1 = f(q, p)
    k2 = f(q + 0.5 * h * k1[0], p + 0.5 * h * k1[1])
    k3 = f(q + 0.5 * h * k2[0], p + 0.5 * h * k2[1])
    k4 = f(q + h * k3[0], p + h * k3[1])
    return q + h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]), p + h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])


def forest_ruth(q, p, h):  # position-velocity splitting with the published coefficients, order 4, symplectic
    c1 = c4 = 1.0 / (2.0 * (2.0 - TWO13))
    c2 = c3 = (1.0 - TWO13) / (2.0 * (2.0 - TWO13))
    d1 = d3 = 1.0 / (2.0 - TWO13)
    d2 = -TWO13 / (2.0 - TWO13)
    for c, d in ((c1, d1), (c2, d2), (c3, d3), (c4, 0.0)):
        q = q + c * h * p
        p = p + d * h * force(q)
    return q, p


def yoshida(q, p, h):  # triple jump of leapfrog: S(w1 h) S(w0 h) S(w1 h), order 4, symplectic
    w1 = 1.0 / (2.0 - TWO13)
    w0 = -TWO13 / (2.0 - TWO13)
    for w in (w1, w0, w1):
        q, p = leapfrog(q, p, w * h)
    return q, p


METHODS = {"euler": (euler, 1, False), "leapfrog": (leapfrog, 2, True), "rk4": (rk4, 4, False),
           "forest_ruth": (forest_ruth, 4, True), "yoshida_triple_jump": (yoshida, 4, True)}


def run(step, q, p, t_end, n):
    h = t_end / n
    for _ in range(n):
        q, p = step(q, p, h)
    return q, p


def reference(q0, p0, t_end):
    """High accuracy reference: Yoshida with a very small step (error far below every tested step)."""
    return run(yoshida, q0, p0, t_end, 20000)


def order_of_convergence(step, q0, p0, t_end, ref):
    ns = [100, 200, 400, 800]
    errs = [math.hypot(*(np.array(run(step, q0, p0, t_end, n)) - np.array(ref))) for n in ns]
    slopes = [math.log(errs[i] / errs[i + 1]) / math.log(2.0) for i in range(len(ns) - 1)]
    return errs, slopes


def jacobian_determinant(step, q, p, h, eps=1e-6):
    """Central finite differences of the one-step map; exactly 1 for a symplectic map (up to rounding)."""
    def f(x):
        return np.array(step(x[0], x[1], h))

    x0 = np.array([q, p])
    jac = np.zeros((2, 2))
    for j in range(2):
        d = np.zeros(2)
        d[j] = eps
        jac[:, j] = (f(x0 + d) - f(x0 - d)) / (2 * eps)
    return float(np.linalg.det(jac))


def long_run_energy(step, q0, p0, h, steps, samples=10):
    q, p = q0, p0
    e0 = energy(q, p)
    out, every = [], steps // samples
    worst = 0.0
    for i in range(1, steps + 1):
        q, p = step(q, p, h)
        if i % 50 == 0 or i == steps:
            worst = max(worst, abs(energy(q, p) - e0))
        if i % every == 0:
            out.append(abs(energy(q, p) - e0))
    return out, worst


def main() -> None:
    q0, p0, t_end = 1.0, 0.0, 10.0
    ref = reference(q0, p0, t_end)
    report = {"problem": "pendulum H=p^2/2-cos q, q0=1, p0=0", "t_end": t_end, "methods": {}}
    for name, (step, expected_order, symplectic) in METHODS.items():
        errs, slopes = order_of_convergence(step, q0, p0, t_end, ref)
        dets = [jacobian_determinant(step, q, p, 0.2) for q, p in ((1.0, 0.0), (0.3, 0.9), (2.0, -0.5))]
        series, worst = long_run_energy(step, q0, p0, 0.1, 100000)
        report["methods"][name] = {
            "expected_order": expected_order,
            "measured_slopes": [round(s, 2) for s in slopes],
            "claimed_symplectic": symplectic,
            "max_abs_det_minus_1_at_h0.2": max(abs(d - 1.0) for d in dets),
            "energy_error_at_10_samples_over_100000_steps_h0.1": [float(f"{e:.3e}") for e in series],
            "max_energy_error": float(f"{worst:.3e}"),
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
