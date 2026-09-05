from datetime import datetime, timedelta, timezone

from src.timeutil import (
    UTC,
    as_utc,
    format_iso_utc,
    format_mtime_utc,
    format_utc,
    parse_utc,
    utc_now,
    utc_today,
)


class TestUtcNow:
    def test_is_aware_utc(self):
        now = utc_now()
        assert now.tzinfo is not None
        assert now.utcoffset() == timedelta(0)

    def test_close_to_datetime_utcnow(self):
        delta = abs((utc_now() - datetime.now(timezone.utc)).total_seconds())
        assert delta < 1


class TestAsUtc:
    def test_naive_assumed_utc(self):
        naive = datetime(2024, 6, 1, 12, 30, 0)
        converted = as_utc(naive)
        assert converted == datetime(2024, 6, 1, 12, 30, 0, tzinfo=UTC)
        assert converted.utcoffset() == timedelta(0)

    def test_already_utc_unchanged(self):
        aware = datetime(2024, 6, 1, 12, 30, 0, tzinfo=UTC)
        assert as_utc(aware) == aware

    def test_other_timezone_converted(self):
        eastern = timezone(timedelta(hours=-5))
        local = datetime(2024, 6, 1, 7, 30, 0, tzinfo=eastern)
        converted = as_utc(local)
        assert converted == datetime(2024, 6, 1, 12, 30, 0, tzinfo=UTC)


class TestParseUtc:
    def test_iso_with_z(self):
        assert parse_utc("2024-01-15T14:30:00Z") == datetime(
            2024, 1, 15, 14, 30, 0, tzinfo=UTC
        )

    def test_iso_with_offset_converted(self):
        assert parse_utc("2024-01-15T09:30:00-05:00") == datetime(
            2024, 1, 15, 14, 30, 0, tzinfo=UTC
        )

    def test_iso_naive_assumed_utc(self):
        assert parse_utc("2024-01-15T14:30:00") == datetime(
            2024, 1, 15, 14, 30, 0, tzinfo=UTC
        )

    def test_space_separated(self):
        assert parse_utc("2024-01-15 14:30") == datetime(
            2024, 1, 15, 14, 30, 0, tzinfo=UTC
        )

    def test_empty_falls_back_to_now(self):
        got = parse_utc("")
        assert abs((got - utc_now()).total_seconds()) < 1

    def test_invalid_raises_without_fallback(self):
        import pytest

        with pytest.raises(ValueError):
            parse_utc("not-a-date", fallback_now=False)

    def test_empty_raises_without_fallback(self):
        import pytest

        with pytest.raises(ValueError):
            parse_utc(None, fallback_now=False)


class TestFormatUtc:
    def test_seconds_layout(self):
        dt = datetime(2024, 1, 15, 14, 30, 5, tzinfo=UTC)
        assert format_utc(dt) == "2024-01-15 14:30:05 UTC"

    def test_minutes_layout(self):
        dt = datetime(2024, 1, 15, 14, 30, 5, tzinfo=UTC)
        assert format_utc(dt, timespec="minutes") == "2024-01-15 14:30 UTC"

    def test_naive_formatted_as_utc(self):
        assert format_utc(datetime(2024, 1, 15, 14, 30, 0)) == "2024-01-15 14:30:00 UTC"

    def test_iso_z_suffix(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        assert format_iso_utc(dt) == "2024-01-15T14:30:00Z"

    def test_mtime_epoch(self):
        # 2024-01-15 14:30:00 UTC
        stamp = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC).timestamp()
        assert format_mtime_utc(stamp) == "2024-01-15 14:30:00 UTC"


class TestUtcToday:
    def test_matches_utc_now_date(self):
        assert utc_today() == utc_now().date()
