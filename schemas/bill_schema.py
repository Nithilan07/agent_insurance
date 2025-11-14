from pydantic import BaseModel
from typing import Optional

class Diagnostics(BaseModel):
    lab_tests: Optional[str] = None
    radiology_tests: Optional[str] = None
    ct_scan: Optional[str] = None
    mri_scan: Optional[str] = None
    xray: Optional[str] = None
    ultrasound: Optional[str] = None

class PatientDetails(BaseModel):
    patient_name: Optional[str] = None
    patient_age: Optional[str] = None
    patient_gender: Optional[str] = None
    uhid_number: Optional[str] = None
    ip_number: Optional[str] = None
    insurance_id: Optional[str] = None
    policy_number: Optional[str] = None

class HospitalDetails(BaseModel):
    hospital_name: Optional[str] = None
    hospital_address: Optional[str] = None
    hospital_city: Optional[str] = None
    hospital_state: Optional[str] = None
    hospital_pincode: Optional[str] = None
    hospital_registration_number: Optional[str] = None
    tpa_name: Optional[str] = None

class AdmissionDetails(BaseModel):
    admission_date: Optional[str] = None
    admission_time: Optional[str] = None
    discharge_date: Optional[str] = None
    discharge_time: Optional[str] = None
    length_of_stay_days: Optional[str] = None
    admission_type: Optional[str] = None
    treatment_type: Optional[str] = None
    diagnosis: Optional[str] = None
    is_maternity_case: bool = False
    is_accident_case: bool = False
    is_surgical_case: bool = False
    is_pre_planned: bool = False

class LegalDocuments(BaseModel):
    mlc_required: bool = False
    mlc_number: Optional[str] = None
    police_fir_number: Optional[str] = None
    accident_date: Optional[str] = None
    accident_description: Optional[str] = None

class BillingBreakdown(BaseModel):
    room_rent_per_day: Optional[str] = None
    room_charges_total: Optional[str] = None
    icu_charges: Optional[str] = None
    nursing_charges: Optional[str] = None
    doctor_fees: Optional[str] = None
    consultation_fees: Optional[str] = None
    visiting_specialist_fees: Optional[str] = None
    surgeon_fees: Optional[str] = None
    anaesthetist_fees: Optional[str] = None
    ot_charges: Optional[str] = None
    ot_consumables: Optional[str] = None
    implant_costs: Optional[str] = None
    pharmacy: Optional[str] = None
    injection_charges: Optional[str] = None
    diagnostics: Diagnostics = Diagnostics()
    ventilator_charges: Optional[str] = None
    oxygen_charges: Optional[str] = None
    blood_charges: Optional[str] = None
    ambulance_charges: Optional[str] = None
    service_charges: Optional[str] = None
    registration_charges: Optional[str] = None
    misc_charges: Optional[str] = None
    discounts: Optional[str] = None
    non_payable_items_total: Optional[str] = None
    payable_items_total: Optional[str] = None
    total_amount: Optional[str] = None

class PaymentDetails(BaseModel):
    paid_by_user: Optional[str] = None
    paid_by_insurance: Optional[str] = None
    payment_status: Optional[str] = None
    payment_mode: Optional[str] = None
    receipt_number: Optional[str] = None

class DocumentStatus(BaseModel):
    has_discharge_summary: bool = False
    has_final_bill: bool = False
    has_payment_receipt: bool = False
    has_pharmacy_bills: bool = False
    has_diagnostic_reports: bool = False
    has_doctor_prescription: bool = False
    has_mlc: bool = False
    has_fir: bool = False

class FullBillData(BaseModel):
    patient_details: PatientDetails = PatientDetails()
    hospital_details: HospitalDetails = HospitalDetails()
    admission_details: AdmissionDetails = AdmissionDetails()
    legal_documents: LegalDocuments = LegalDocuments()
    billing_breakdown: BillingBreakdown = BillingBreakdown()
    payment_details: PaymentDetails = PaymentDetails()
    document_status: DocumentStatus = DocumentStatus()
