#!/usr/bin/env python3
"""Offline precompute for the B-spline fitting website demo.

This script faithfully replicates the iterative adaptive knot-insertion loop
used by ``common.trajectory_compression.ScipyBSplineCompression.compress`` and
exports every iteration to ``data.js`` so the static webpage can replay the
process without doing any spline math in the browser.

The numerical path is identical to the repo implementation:
    t = arange(len(data))
    for knots in generate_knots(t, data, s=s):
        spl = make_lsq_spline(t, data, knots)         # degree 3
        error = abs(spl(t) - data).max()
        if error < max_error: stop (converged)

We do NOT call ``compress`` directly because it breaks at the first converging
knot vector and only keeps the accepted result; to animate the *whole*
convergence we record each candidate iteration ourselves using the exact same
calls.
"""

import json
import os
import sys

import numpy as np
from scipy.interpolate import make_lsq_spline, generate_knots, BSpline

# Make the repo importable so we can validate against the real implementation.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ----------------------------------------------------------------------------
# Shared constants (mirrors ignore-when-release/.../bspline_compress_iterations.py)
# ----------------------------------------------------------------------------
SAMPLE_INTERVAL = 0.15
X_RANGE = (1.0, 9.0)
S_VALUE = 1e-12
DEGREE = 3
DENSE_SAMPLES = 320
FLOAT_DIGITS = 5
ERROR_DIGITS = 6

# Slider tiers (from coarse to fine). Each becomes a stop on the error slider.
MAX_ERROR_TIERS = [0.8, 0.5, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01]

OUT_JS_PATH = os.path.join(os.path.dirname(__file__), "data.js")


# ----------------------------------------------------------------------------
# Demo curve + helpers
# ----------------------------------------------------------------------------
def curve_func(x):
    """Fixed multi-sine demo signal (identical to the reference figure script)."""
    return (
        3.5
        + 1.0 * np.sin(1.0 * x)
        + 0.7 * np.sin(2.0 * x + 0.5)
        + 0.5 * np.sin(3.0 * x + 1.0)
        + 0.3 * np.sin(4.5 * x + 0.3)
    )


def build_demo_curve():
    x_samples = np.arange(X_RANGE[0], X_RANGE[1] + SAMPLE_INTERVAL, SAMPLE_INTERVAL)
    y_samples = curve_func(x_samples)
    return x_samples, y_samples


def greville(t_knots, k, n_control):
    """Greville abscissae used as control-point x positions (param space)."""
    return np.array(
        [np.sum(t_knots[i + 1 : i + 1 + k]) / k for i in range(n_control)]
    )


def param_to_x(param):
    """Map timestep-index parameter space back to the curve's x axis."""
    return np.asarray(param) * SAMPLE_INTERVAL + X_RANGE[0]


def rounded(value, digits=FLOAT_DIGITS):
    return round(float(value), digits)


def rounded_list(values, digits=FLOAT_DIGITS):
    return [rounded(v, digits) for v in values]


def record_iterations(y, max_error, s=S_VALUE, k=DEGREE):
    """Replicate the compress() loop and record EVERY candidate iteration.

    Returns a list of per-iteration dicts. The list is a prefix of the full
    generate_knots candidate sequence: it stops right after the first iteration
    whose max error drops below ``max_error`` (the converged frame), or runs the
    whole sequence if nothing converges.
    """
    t = np.arange(len(y), dtype=np.float64)
    t_dense = np.linspace(0, len(y) - 1, DENSE_SAMPLES)

    x_samples = param_to_x(t)

    iterations = []
    for knots in generate_knots(t, y, s=s):
        spl = make_lsq_spline(t, y, knots)
        pred = spl(t)
        residual = pred - y
        abs_res = np.abs(residual)
        error = float(abs_res.max())
        imax = int(np.argmax(abs_res))

        interior = knots[k:-k]
        interior_x = param_to_x(interior).tolist()
        c = spl.c
        ctrl_param = greville(spl.t, k, len(c))

        converged = error < max_error
        iterations.append(
            {
                "interior_knots_x": rounded_list(interior_x),
                "control_x": rounded_list(param_to_x(ctrl_param)),
                "control_y": rounded_list(c),
                "curve_y": rounded_list(spl(t_dense)),
                "pred_y": rounded_list(pred),
                "max_error_x": rounded(x_samples[imax]),
                "max_error_data_y": rounded(y[imax]),
                "max_error_pred_y": rounded(pred[imax]),
                "max_error_achieved": rounded(error, ERROR_DIGITS),
                "converged": converged,
            }
        )

        if converged:
            break

    return iterations


def validate_against_real_impl(y):
    """Sanity check: our replicated loop matches the real compress() result."""
    try:
        from common.trajectory_compression import ScipyBSplineCompression
    except Exception as exc:  # pragma: no cover - import diagnostics only
        print(f"[warn] could not import real implementation for validation: {exc}")
        return

    for me in (0.1, 0.05):
        comp = ScipyBSplineCompression(degree=DEGREE)
        real_knots = comp.compress(np.asarray(y, dtype=np.float64), max_error=me, s=S_VALUE)
        iters = record_iterations(np.asarray(y, dtype=np.float64), me)
        # Last recorded iteration should reproduce the real accepted knot count.
        mine_interior = len(iters[-1]["interior_knots_x"])
        real_interior = len(real_knots[DEGREE:-DEGREE])
        status = "OK" if mine_interior == real_interior else "MISMATCH"
        print(
            f"[validate] max_error={me}: real interior knots={real_interior}, "
            f"replicated={mine_interior} -> {status}"
        )


def main():
    x_samples, y_samples = build_demo_curve()
    print(f"Demo curve: {len(x_samples)} samples over x in {X_RANGE}")

    validate_against_real_impl(y_samples)

    tiers = []
    for me in MAX_ERROR_TIERS:
        iters = record_iterations(y_samples, me)
        final = iters[-1]
        tiers.append({"max_error": me, "iterations": iters})
        print(
            f"max_error={me:<5}: {len(iters)} iterations, "
            f"final knots={final['n_knots']}, "
            f"achieved={final['max_error_achieved']:.4f}, "
            f"converged={final['converged']}"
        )

    payload = {
        "sampling": {
            "x_range": list(X_RANGE),
            "sample_interval": SAMPLE_INTERVAL,
            "curve_sample_count": DENSE_SAMPLES,
            "degree": DEGREE,
            "s": S_VALUE,
        },
        "data_points": {"x": rounded_list(x_samples), "y": rounded_list(y_samples)},
        "tiers": tiers,
    }

    with open(OUT_JS_PATH, "w") as f:
        f.write(
            "// Generated by precompute.py so the fitting diagram can load "
            "from file:// and HTTP.\n"
        )
        f.write("window.__FIT_DATA__ = window.__FIT_DATA__ || ")
        json.dump(payload, f, separators=(",", ":"))
        f.write(";\n")
    print(f"Wrote {OUT_JS_PATH} ({os.path.getsize(OUT_JS_PATH) / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
