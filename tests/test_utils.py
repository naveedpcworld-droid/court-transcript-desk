from pipeline.utils import parse_duration, parse_views, parse_published


def test_duration():
    assert parse_duration("1:02:03") == 3723
    assert parse_duration("12:34") == 754
    assert parse_duration(90) == 90


def test_views():
    assert parse_views("1.2K") == 1200
    assert parse_views("3,400") == 3400


def test_published():
    assert parse_published("20261103").startswith("2026-11-03")
