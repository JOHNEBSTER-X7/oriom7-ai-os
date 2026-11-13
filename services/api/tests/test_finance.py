import uuid
import pytest
from pydantic import ValidationError


def test_budget_currency_and_period_validation():
    from finance import BudgetCreate
    valid = BudgetCreate(name="AI materials", period_start="2026-01-01", period_end="2026-12-31",
                         currency="usd", approved_amount="12500.00")
    assert valid.currency == "USD"
    with pytest.raises(ValidationError):
        BudgetCreate(name="AI materials", period_start="2026-12-31", period_end="2026-01-01",
                     currency="USD", approved_amount="12500")
    with pytest.raises(ValidationError):
        BudgetCreate(name="AI materials", period_start="2026-01-01", period_end="2026-12-31",
                     currency="US dollars", approved_amount="12500")


def test_transaction_requires_project_for_experiment_and_positive_amount():
    from finance import TransactionCreate
    base = dict(category="consumables", description="Reagents for test series", amount="50",
                currency="GBP", transaction_date="2026-11-01", recorded_by="Lab manager")
    with pytest.raises(ValidationError):
        TransactionCreate(**base, experiment_id=uuid.uuid4())
    with pytest.raises(ValidationError):
        TransactionCreate(**{**base, "amount":"0"})
    tx = TransactionCreate(**base, project_id=uuid.uuid4(), transaction_type="expense")
    assert tx.currency == "GBP"


def test_grant_dates_and_currency_are_validated():
    from finance import GrantCreate
    with pytest.raises(ValidationError):
        GrantCreate(funder_name="Research fund", currency="GBP", awarded_amount="1000",
                    start_date="2026-12-01", end_date="2026-01-01")
    grant = GrantCreate(funder_name="Research fund", currency="eur", awarded_amount="1000")
    assert grant.currency == "EUR"


def test_depreciation_residual_cannot_exceed_cost():
    from finance import DepreciationCreate
    with pytest.raises(ValidationError):
        DepreciationCreate(equipment_id=uuid.uuid4(), acquisition_date="2026-01-01",
                           acquisition_cost="1000", currency="USD", useful_life_months=24,
                           residual_value="1001")
    item = DepreciationCreate(equipment_id=uuid.uuid4(), acquisition_date="2026-01-01",
                              acquisition_cost="1000", currency="USD", useful_life_months=24,
                              residual_value="100")
    assert item.useful_life_months == 24
