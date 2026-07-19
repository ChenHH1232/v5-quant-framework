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
