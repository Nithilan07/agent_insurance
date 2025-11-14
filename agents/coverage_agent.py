# agents/coverage_agent.py
import re
from datetime import datetime
from typing import Dict, Any
from schemas.bill_schema import FullBillData

# ----------------------------------------------------------------------
# SAFE NUMERIC UTILITIES
# ----------------------------------------------------------------------

def safe_int(x):
    """
    Convert any value (None, '', '12,345', float, string) safely into int.
    Returns 0 whenever conversion is not possible.
    """
    if x is None:
        return 0
    try:
        if isinstance(x, (int, float)):
            return int(x)
        if isinstance(x, str):
            cleaned = re.sub(r"[^\d.]", "", x).strip()
            if cleaned == "":
                return 0
            return int(float(cleaned))
        return int(x)
    except:
        return 0


def parse_date(s):
    """Try common date formats and return datetime.date or None."""
    if not s:
        return None
    s = s.strip()
    fmts = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y",
            "%d %b %Y", "%d %B %Y"]
    for f in fmts:
        try:
            return datetime.strptime(s, f).date()
        except:
            continue
    try:
        return datetime.fromisoformat(s).date()
    except:
        return None


def days_between(a, b):
    """Inclusive day count between two dates. Returns 1 if missing."""
    if not a or not b:
        return 1
    delta = (b - a).days
    return max(delta + 1, 1)


# ----------------------------------------------------------------------
# COVERAGE CALCULATOR (PATCHED + SAFE)
# ----------------------------------------------------------------------

def calculate_coverage(full_bill: FullBillData, policy_features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes insurance payable amounts safely.
    Prevents ALL None + int crashes by using safe_int() everywhere.
    """

    b = full_bill.billing_breakdown

    # --------- SAFE DIAGNOSTIC TOTALS ---------
    diagnostics_total = 0
    for key in ["lab_tests", "radiology_tests", "ct_scan", "mri_scan", "xray", "ultrasound"]:
        diagnostics_total += safe_int(getattr(b.diagnostics, key, None))

    # --------- SAFE BILL FIELDS ---------
    room_total = safe_int(b.room_charges_total)
    icu_total = safe_int(b.icu_charges)
    doctor_fees = safe_int(b.doctor_fees)
    surgeon_fees = safe_int(b.surgeon_fees)
    anaesthesia = safe_int(b.anaesthetist_fees)
    ot = safe_int(b.ot_charges)
    pharmacy = safe_int(b.pharmacy)
    injections = safe_int(b.injection_charges)
    implant_costs = safe_int(b.implant_costs)
    misc = safe_int(b.misc_charges)
    registration = safe_int(b.registration_charges)
    ambulance = safe_int(b.ambulance_charges)
    ventilator = safe_int(b.ventilator_charges)
    oxygen = safe_int(b.oxygen_charges)
    blood = safe_int(b.blood_charges)
    total_amount = safe_int(b.total_amount)

    # If total is missing, build fallback total
    if total_amount == 0:
        total_amount = sum([
            room_total, icu_total, doctor_fees, surgeon_fees, anaesthesia,
            ot, pharmacy, injections, implant_costs, misc, registration,
            ambulance, ventilator, oxygen, blood, diagnostics_total
        ])

    # --------- LENGTH OF STAY ---------
    adm = parse_date(full_bill.admission_details.admission_date)
    dis = parse_date(full_bill.admission_details.discharge_date)
    stay_days = days_between(adm, dis)

    # --------- POLICY LIMITS ---------
    room_limit_per_day = safe_int(policy_features.get("room_rent_limit_per_day"))
    co_pay_percent = safe_int(policy_features.get("co_pay_percent"))
    diagnostics_sub_limit = safe_int(policy_features.get("diagnostics_sub_limit"))
    covers_daycare = bool(policy_features.get("covers_daycare"))
    covers_maternity = bool(policy_features.get("covers_maternity"))

    breakdown = {}
    reasons = []
    recommended = []

    # ------------------------------------------------------------------
    # ROOM CHARGES
    # ------------------------------------------------------------------
    if room_limit_per_day > 0:
        allowed_room_cap = room_limit_per_day * stay_days
        allowed_room = min(room_total, allowed_room_cap)
        not_allowed_room = max(room_total - allowed_room, 0)
        if not_allowed_room > 0:
            reasons.append(
                f"Room rent exceeds policy limit of ₹{room_limit_per_day}/day × {stay_days} days."
            )
            recommended.append("Choose room within policy limits to avoid deductions.")
    else:
        allowed_room = room_total
        not_allowed_room = 0

    breakdown["room"] = {
        "charged": room_total,
        "allowed": allowed_room,
        "not_allowed": not_allowed_room
    }

    # ------------------------------------------------------------------
    # ICU
    # ------------------------------------------------------------------
    breakdown["icu"] = {
        "charged": icu_total,
        "allowed": icu_total,
        "not_allowed": 0
    }

    # ------------------------------------------------------------------
    # DOCTOR + SURGEON + ANAESTHESIA
    # ------------------------------------------------------------------
    allowed_doctor = doctor_fees + surgeon_fees + anaesthesia
    breakdown["doctor_surgeon"] = {
        "charged": doctor_fees + surgeon_fees + anaesthesia,
        "allowed": allowed_doctor,
        "not_allowed": 0
    }

    # ------------------------------------------------------------------
    # OT + IMPLANTS
    # ------------------------------------------------------------------
    breakdown["ot_implant"] = {
        "charged": ot + implant_costs,
        "allowed": ot + implant_costs,
        "not_allowed": 0
    }

    # ------------------------------------------------------------------
    # DIAGNOSTICS
    # ------------------------------------------------------------------
    if diagnostics_total > diagnostics_sub_limit > 0:
        allowed_diag = diagnostics_sub_limit
        not_allowed_diag = diagnostics_total - diagnostics_sub_limit
        reasons.append(
            f"Diagnostics exceed sub-limit of ₹{diagnostics_sub_limit}."
        )
    else:
        allowed_diag = diagnostics_total
        not_allowed_diag = 0

    breakdown["diagnostics"] = {
        "charged": diagnostics_total,
        "allowed": allowed_diag,
        "not_allowed": not_allowed_diag
    }

    # ------------------------------------------------------------------
    # PHARMACY + OTHERS
    # ------------------------------------------------------------------
    breakdown["pharmacy"] = {"charged": pharmacy, "allowed": pharmacy, "not_allowed": 0}
    breakdown["blood"] = {"charged": blood, "allowed": blood, "not_allowed": 0}
    breakdown["oxygen"] = {"charged": oxygen, "allowed": oxygen, "not_allowed": 0}
    breakdown["ventilator"] = {"charged": ventilator, "allowed": ventilator, "not_allowed": 0}
    breakdown["ambulance"] = {"charged": ambulance, "allowed": ambulance, "not_allowed": 0}
    breakdown["misc"] = {"charged": misc, "allowed": misc, "not_allowed": 0}

    # ------------------------------------------------------------------
    # TOTAL BEFORE CO-PAY
    # ------------------------------------------------------------------
    total_allowed_before_copay = sum(v["allowed"] for v in breakdown.values())

    # ------------------------------------------------------------------
    # MATERNITY COVER CHECK
    # ------------------------------------------------------------------
    if full_bill.admission_details.is_maternity_case and not covers_maternity:
        reasons.append("This policy does NOT cover maternity.")
        recommended.append("Confirm maternity coverage or upload your policy document.")
        total_allowed_before_copay = 0

    # ------------------------------------------------------------------
    # APPLY CO-PAY
    # ------------------------------------------------------------------
    co_pay_amount = int(total_allowed_before_copay * (co_pay_percent / 100))
    insurance_payable = max(total_allowed_before_copay - co_pay_amount, 0)

    # ------------------------------------------------------------------
    # USER PAYABLE
    # ------------------------------------------------------------------
    user_paid = safe_int(full_bill.payment_details.paid_by_user)
    insurance_paid = safe_int(full_bill.payment_details.paid_by_insurance)

    user_payable_estimate = max(total_amount - insurance_payable, 0)

    # ------------------------------------------------------------------
    # BUILD RESULT
    # ------------------------------------------------------------------
    result = {
        "policy_features_used": {
            "room_rent_limit_per_day": room_limit_per_day,
            "co_pay_percent": co_pay_percent,
            "diagnostics_sub_limit": diagnostics_sub_limit,
            "covers_daycare": covers_daycare,
            "covers_maternity": covers_maternity
        },
        "totals": {
            "total_bill_amount": total_amount,
            "total_payable_before_copay": total_allowed_before_copay,
            "co_pay_amount": co_pay_amount,
            "final_insurance_payable": insurance_payable,
            "user_payable_estimate": user_payable_estimate,
        },
        "breakdown": breakdown,
        "reasons": reasons,
        "recommended_actions": recommended,
        "verdict": "Eligible"
    }

    # ------------------------------------------------------------------
    # MISSING CRITICAL FIELDS → downgrade verdict
    # ------------------------------------------------------------------
    if data_contains_missing_critical(full_bill):
        result["verdict"] = "Eligible - Missing Documents"
        result["reasons"].append("Critical documentation missing.")
        result["recommended_actions"].append(
            "Upload final bill, discharge summary, receipts."
        )

    if insurance_payable == 0 and reasons:
        result["verdict"] = "May be Rejected / Review Required"

    return result


def data_contains_missing_critical(full_bill: FullBillData) -> bool:
    """Check if critical fields are missing."""
    pd = full_bill.patient_details
    ad = full_bill.admission_details
    b = full_bill.billing_breakdown
    ds = full_bill.document_status

    return (
        not pd.patient_name
        or not ad.admission_date
        or not ad.discharge_date
        or safe_int(b.total_amount) == 0
        or not ad.diagnosis
        or not ds.has_final_bill
    )
