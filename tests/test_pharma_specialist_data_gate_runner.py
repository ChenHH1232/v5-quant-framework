from __future__ import annotations

import csv
from pathlib import Path

from v5.pharma_specialist_data_gate_runner import run_pharma_specialist_data_gate


def test_pharma_specialist_data_gate_blocks_missing_rd_policy_fields(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    daily = tmp_path / "daily.csv"
    dividends = tmp_path / "dividends.csv"
    reports = tmp_path / "reports.csv"

    fields = [
        "trade_date",
        "code",
        "sub_industry",
        "future_return",
        "total_return",
        "factor_visible_date",
        "operating_cash_flow_yield",
        "operating_cash_flow_to_net_profit",
        "gross_margin",
        "receivables_to_revenue",
        "inventory_to_revenue",
        "working_capital_pressure_to_revenue",
        "dividend_yield",
        "low_vol_score",
        "volatility_120d",
        "downside_volatility_120d",
        "max_drawdown_120d",
    ]
    with panel.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for month in range(1, 13):
            trade_date = f"2025-{month:02d}-01"
            for index in range(8):
                writer.writerow(
                    {
                        "trade_date": trade_date,
                        "code": f"00000{index}.XSHG",
                        "sub_industry": "sw_biologics",
                        "future_return": "0.01",
                        "total_return": "0.01",
                        "factor_visible_date": trade_date,
                        "operating_cash_flow_yield": "0.1",
                        "operating_cash_flow_to_net_profit": "1.2",
                        "gross_margin": "0.5",
                        "receivables_to_revenue": "0.2",
                        "inventory_to_revenue": "0.2",
                        "working_capital_pressure_to_revenue": "0.4",
                        "dividend_yield": "0.02",
                        "low_vol_score": "0.7",
                        "volatility_120d": "0.2",
                        "downside_volatility_120d": "0.1",
                        "max_drawdown_120d": "-0.15",
                    }
                )
    daily.write_text("date,code,open,close\n2025-01-01,000000.XSHG,1,1\n", encoding="utf-8")
    dividends.write_text("code,date,cash\n000000.XSHG,2025-06-01,0.1\n", encoding="utf-8")
    reports.write_text("report_id,title,view_url\n1,pharma,https://www.fxbaogao.com/view?id=1\n", encoding="utf-8")

    result = run_pharma_specialist_data_gate(panel, daily, dividends, reports, tmp_path / "out")

    assert result.status == "pharma_specialist_data_gate_blocked"
    summary = result.summary_json.read_text(encoding="utf-8")
    assert "rd_expense_to_revenue" in summary
    assert "policy_state" in summary
