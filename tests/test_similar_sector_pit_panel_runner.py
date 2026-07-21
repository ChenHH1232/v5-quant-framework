from __future__ import annotations

from v5.paths import DEFAULT_DATABASE_DIR
from v5.similar_sector_pit_panel_runner import SECTOR_CONFIGS


def test_default_database_dir_uses_unicode_escape_database_path() -> None:
    assert ascii(str(DEFAULT_DATABASE_DIR)) == "'\\u6570\\u636e\\u5e93'"


def test_airport_transport_operator_sector_config_is_registered() -> None:
    config = SECTOR_CONFIGS["airport_transport_operators"]

    assert config["industry_codes"]["HY03158"] == "airport"
    assert "600009.XSHG" in config["explicit_codes"]
    assert "Airlines" in " ".join(config["limitations"])


def test_oil_gas_pipeline_integrated_sector_config_is_registered() -> None:
    config = SECTOR_CONFIGS["oil_gas_pipeline_integrated"]

    assert config["industry_codes"]["HY01103"] == "integrated_oil_gas"
    assert config["industry_codes"]["HY01106"] == "oil_gas_distribution_other"
    assert "Oilfield services are intentionally excluded" in " ".join(config["limitations"])


def test_low_priority_observation_sector_configs_are_registered() -> None:
    assert SECTOR_CONFIGS["securities_brokerage"]["industry_codes"]["HY07107"] == "jq_securities_company"
    assert "801093" in SECTOR_CONFIGS["auto_and_parts"]["industry_codes"]
    assert "801077" in SECTOR_CONFIGS["machinery_equipment"]["industry_codes"]
    assert "HY03151" in SECTOR_CONFIGS["logistics_express"]["industry_codes"]
