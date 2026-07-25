import math
from typing import Optional


CKD_EPI_2021_VERSION = "CKD-EPI-creatinine-2021"
CKD_EPI_2021_URI = "https://www.kidney.org/ckd-epi-creatinine-equation-2021-0"


def calculate_egfr_2021(creatinine_mg_dl: float, age: float, sex: str) -> Optional[float]:
    """Return race-free 2021 CKD-EPI eGFR in mL/min/1.73 m2."""
    try:
        creatinine = float(creatinine_mg_dl)
        years = float(age)
    except (TypeError, ValueError):
        return None
    normalized_sex = str(sex or "").strip().upper()
    if creatinine <= 0 or years < 18 or normalized_sex not in {"M", "MALE", "F", "FEMALE"}:
        return None

    female = normalized_sex in {"F", "FEMALE"}
    kappa = 0.7 if female else 0.9
    alpha = -0.241 if female else -0.302
    sex_factor = 1.012 if female else 1.0
    ratio = creatinine / kappa
    egfr = (
        142
        * math.pow(min(ratio, 1), alpha)
        * math.pow(max(ratio, 1), -1.2)
        * math.pow(0.9938, years)
        * sex_factor
    )
    return float(round(egfr))
