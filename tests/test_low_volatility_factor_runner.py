from __future__ import annotations

import csv
from pathlib import Path

from v5.low_volatility_factor_runner import add_low_volatility_factors


def test_low_volatility_factor_runner_uses_only_prior_closes(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    prices = tmp_path / "prices.csv"
    with panel.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["trade_date", "code"])
        writer.writeheader()
        writer.writerow({"trade_date": "2021-01-06", "code": "000001.XSHE"})
    with prices.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "code", "close"])
        writer.writeheader()
        for day, close in [
            ("2021-01-01", "10"),
            ("2021-01-02", "11"),
            ("2021-01-03", "12"),
            ("2021-01-04", "11"),
            ("2021-01-05", "10"),
            ("2021-01-06", "100"),
        ]:
            writer.writerow({"date": day, "code": "000001.XSHE", "close": close})

    result = add_low_volatility_factors(
        panel,
        prices,
        tmp_path / "out",
        strategy_id="test",
        windows=[3],
        min_observations=2,
    )

    rows = list(csv.DictReader(result.panel_path.open("r", encoding="utf-8-sig", newline="")))
    assert rows[0]["low_vol_factor_visible_date"] == "2021-01-05"
    assert rows[0]["low_vol_observation_count_3d"] == "3"
    assert rows[0]["volatility_3d"] not in {"", None}


def test_low_volatility_factor_runner_waits_for_min_observations(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    prices = tmp_path / "prices.csv"
    panel.write_text("trade_date,code\n2021-01-03,000001.XSHE\n", encoding="utf-8")
    prices.write_text(
        "date,code,close\n2021-01-01,000001.XSHE,10\n2021-01-02,000001.XSHE,11\n",
        encoding="utf-8",
    )

    result = add_low_volatility_factors(
        panel,
        prices,
        tmp_path / "out",
        strategy_id="test",
        windows=[3],
        min_observations=2,
    )

    rows = list(csv.DictReader(result.panel_path.open("r", encoding="utf-8-sig", newline="")))
    assert rows[0]["volatility_3d"] == ""
    assert rows[0]["low_vol_score"] == ""
