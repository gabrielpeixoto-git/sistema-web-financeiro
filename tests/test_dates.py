from datetime import date

import pytest

from financas_app.app.common.dates import (
    ensure_period_valid,
    first_day_of_month,
    today_in_app,
    today_in_zone,
    validate_timezone,
)


def test_ensure_period_valid_ok():
    ensure_period_valid(date(2026, 1, 1), date(2026, 1, 31))


def test_ensure_period_valid_rejects():
    with pytest.raises(ValueError):
        ensure_period_valid(date(2026, 2, 1), date(2026, 1, 1))


def test_first_day_of_month():
    assert first_day_of_month(date(2026, 3, 15)) == date(2026, 3, 1)


def test_today_in_zone_utc():
    d = today_in_zone("UTC")
    assert d.year >= 2020


def test_today_in_app_override_timezone():
    assert today_in_app("UTC") == today_in_zone("UTC")


def test_validate_timezone_rejects_invalid():
    with pytest.raises(ValueError):
        validate_timezone("Invalid/Timezone")
