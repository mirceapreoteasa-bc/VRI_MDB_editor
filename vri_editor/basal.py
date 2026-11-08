"""Estimated stand basal area (m2/ha) for photo-interpreted layers.

Used by the editor's "Basal area calculator" (Tools menu) to pre-fill an empty
basal area after species, age, height and density are entered. The user may
accept or change the value; it is only a first estimate.

Coefficients are an empirical log-linear fit to the photo-interpreted (PI)
layers in the sample VRIMS maps (10,182 layers):

    ln(BA) = const + a*ln(height) + b*ln(age) + c*ln(density)
             [+ d*ln(crown closure)] + species offset

Accuracy on those layers (in-sample): 82% (no crown) to 87% (with crown)
fall within 0.5-1.5 times the recorded basal area; median ratio ~0.97.
This is an approximation for catching large errors, not the VRICap or VDYP7
algorithm.
"""

from __future__ import annotations

import math

TOP_SPECIES = ['FDC', 'HW', 'BA', 'HM', 'BL', 'CW', 'DR', 'YC', 'PLC', 'PL', 'ACT', 'MB']

MODEL_WITH_CC = {
        "const": -4.743275,
        "ht": 0.876621,
        "age": 0.271816,
        "dens": 0.213788,
        "cc": 0.779233,
        "sp_HW": -0.017634,
        "sp_BA": -0.047561,
        "sp_HM": 0.072649,
        "sp_BL": 0.011693,
        "sp_CW": -0.052570,
        "sp_DR": 0.019462,
        "sp_YC": 0.069799,
        "sp_PLC": 0.058624,
        "sp_PL": 0.075285,
        "sp_ACT": -0.144983,
        "sp_MB": 0.092073,
    }

MODEL_NO_CC = {
        "const": -7.100010,
        "ht": 1.302610,
        "age": 0.416487,
        "dens": 0.749768,
        "sp_HW": -0.074007,
        "sp_BA": -0.137736,
        "sp_HM": 0.012570,
        "sp_BL": -0.062887,
        "sp_CW": -0.076382,
        "sp_DR": 0.190941,
        "sp_YC": -0.025921,
        "sp_PLC": 0.156437,
        "sp_PL": 0.157992,
        "sp_ACT": -0.065474,
        "sp_MB": 0.310049,
    }

MIN_BA = 0.1
MAX_BA = 200.0


def estimate(species: str, age: float, height: float, density: float,
             crown_closure: float | None = None) -> float | None:
    """Return the estimated basal area (m2/ha), rounded to 0.1, or None.

    Returns None when an input is missing or outside a physical range.
    Crown closure is optional; when given the crown-closure model is used.
    """
    try:
        age = float(age)
        height = float(height)
        density = float(density)
    except (TypeError, ValueError):
        return None
    if age <= 0 or height <= 0 or density <= 0:
        return None
    if crown_closure is not None and crown_closure <= 0:
        crown_closure = None
    code = (species or "").strip().upper()
    if crown_closure is not None:
        coef = MODEL_WITH_CC
        logs = {"ht": math.log(height), "age": math.log(age),
                "dens": math.log(density), "cc": math.log(crown_closure)}
    else:
        coef = MODEL_NO_CC
        logs = {"ht": math.log(height), "age": math.log(age), "dens": math.log(density)}
    value = coef["const"] + sum(coef[k] * v for k, v in logs.items())
    value += coef.get("sp_" + code, 0.0) if code in TOP_SPECIES[1:] else 0.0
    ba = math.exp(value)
    return round(min(MAX_BA, max(MIN_BA, ba)), 1)
