from __future__ import annotations

from v5.equal_weight_benchmark_runner import build_equal_weight_benchmark
from v5.io_utils import read_csv_rows, write_csv_rows


def test_build_equal_weight_benchmark_from_execution_prices(tmp_path) -> None:
    prices = tmp_path / "prices.csv"
    out = tmp_path / "benchmark.csv"
    write_csv_rows(
        prices,
        ["date", "code", "close"],
        [
            {"date": "2026-01-01", "code": "000001.XSHE", "close": "10"},
            {"date": "2026-01-01", "code": "000002.XSHE", "close": "20"},
            {"date": "2026-01-02", "code": "000001.XSHE", "close": "11"},
            {"date": "2026-01-02", "code": "000002.XSHE", "close": "18"},
        ],
    )

    build_equal_weight_benchmark(
        prices,
        out,
        benchmark_id="test_equal_weight",
        source_label="unit_test_equal_weight",
        start_date="2026-01-01",
        end_date="2026-01-02",
        base_close=1000.0,
    )

    rows = read_csv_rows(out)
    assert rows[0]["close"] == "1000"
    assert rows[1]["code"] == "test_equal_weight"
    assert rows[1]["close"] == "1000"
    assert rows[1]["return_member_count"] == "2"
