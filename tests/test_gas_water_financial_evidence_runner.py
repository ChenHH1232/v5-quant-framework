from v5.gas_water_financial_evidence_runner import _derive_direct_metrics


def test_derive_direct_metrics_receivables_and_debt_pressure():
    row = {
        "total_operating_revenue": 1000.0,
        "goods_sale_and_service_render_cash": 900.0,
        "account_receivable": 100.0,
        "bill_receivable": 20.0,
        "receivable_fin": 30.0,
        "contract_assets": 50.0,
        "longterm_receivable_account": 0.0,
        "total_assets": 2000.0,
        "shortterm_loan": 100.0,
        "longterm_loan": 200.0,
        "bonds_payable": 300.0,
        "non_current_liability_in_one_year": 50.0,
        "cash_equivalents": 150.0,
        "net_operate_cash_flow": 400.0,
    }

    metrics = _derive_direct_metrics(row, "2026-04-01")

    assert metrics["direct_receivables_total"] == "200"
    assert metrics["direct_receivables_to_revenue"] == "0.2"
    assert metrics["direct_collection_cash_to_revenue"] == "0.9"
    assert metrics["direct_interest_bearing_debt"] == "650"
    assert metrics["direct_interest_bearing_debt_to_assets"] == "0.325"
    assert metrics["direct_net_debt_to_assets"] == "0.25"
    assert metrics["direct_ocf_to_receivables"] == "2"
    assert metrics["gas_water_financial_evidence_visible_date"] == "2026-04-01"
