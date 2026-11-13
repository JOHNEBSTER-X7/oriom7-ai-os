import uuid
import pytest
from pydantic import ValidationError


def test_quality_inspection_requires_valid_sample_and_defect_counts():
    from quality import InspectionCreate
    inspection = InspectionCreate(
        lot_id=uuid.uuid4(), inspection_type="Incoming visual inspection", outcome="pass",
        sample_size=10, defects_count=2, performed_by="Quality technician"
    )
    assert inspection.defects_count <= inspection.sample_size
    with pytest.raises(ValidationError):
        InspectionCreate(lot_id=uuid.uuid4(), inspection_type="Visual", outcome="pass",
                         sample_size=2, defects_count=3, performed_by="Technician")
    with pytest.raises(ValidationError):
        InspectionCreate(lot_id=uuid.uuid4(), inspection_type="Visual", outcome="unknown",
                         sample_size=2, performed_by="Technician")


def test_capa_status_and_action_types_are_constrained():
    from quality import CapaCreate, CapaStatusUpdate
    action = CapaCreate(nonconformance_id=uuid.uuid4(), action_type="preventive",
                        description="Update supplier acceptance procedure", assigned_to="Quality manager",
                        recorded_by="Quality manager")
    assert action.action_type == "preventive"
    assert CapaStatusUpdate(status="verified", recorded_by="Auditor").status == "verified"
    with pytest.raises(ValidationError):
        CapaStatusUpdate(status="approved", recorded_by="Auditor")
    with pytest.raises(ValidationError):
        CapaCreate(nonconformance_id=uuid.uuid4(), action_type="fix",
                   description="Correct problem", assigned_to="Quality manager", recorded_by="Quality manager")


def test_compliance_document_dates_and_review_values():
    from quality import ComplianceDocumentCreate, ComplianceReviewUpdate
    doc = ComplianceDocumentCreate(document_type="SDS", document_name="Safety data sheet",
                                   reference="DOC-001", issued_at="2026-01-01", expires_at="2027-01-01")
    assert doc.expires_at > doc.issued_at
    with pytest.raises(ValidationError):
        ComplianceDocumentCreate(document_type="SDS", document_name="Safety data sheet",
                                 reference="DOC-002", issued_at="2027-01-01", expires_at="2026-01-01")
    with pytest.raises(ValidationError):
        ComplianceReviewUpdate(review_status="verified", reviewed_by="Reviewer")

def test_inspection_outcomes_and_sample_defect_relationship():
    from quality import InspectionCreate
    common = {"lot_id":uuid.uuid4(),"inspection_type":"Incoming inspection","sample_size":5,"performed_by":"Quality technician"}
    assert InspectionCreate(**common,outcome="fail",defects_count=1).outcome == "fail"
    assert InspectionCreate(**common,outcome="conditional").outcome == "conditional"
    with pytest.raises(ValidationError):
        InspectionCreate(**common,outcome="pass",defects_count=6)


def test_capa_cannot_be_verified_without_completion_is_api_gate_not_payload_enum():
    from quality import CapaStatusUpdate
    # Payload enum permits the desired target; transition ordering is enforced in the API transaction.
    assert CapaStatusUpdate(status="verified",recorded_by="Quality manager").status == "verified"


def test_compliance_review_requires_a_decision_maker():
    from quality import ComplianceReviewUpdate
    with pytest.raises(ValidationError):
        ComplianceReviewUpdate(review_status="accepted",reviewed_by=" ")
