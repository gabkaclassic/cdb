import pytest
from cdb import search_geo


@pytest.fixture
def sample_data():
    return [
        (10, 20, 1),
        (30, 40, 2),
        (50, 60, 3),
    ]


@pytest.fixture
def sample_mapping():
    return {
        1: ("Country1", "City1"),
        2: ("Country2", "City2"),
        3: ("Country3", "City3"),
    }


def test_exact_match(sample_data, sample_mapping):
    assert search_geo(sample_data, 15, sample_mapping) == ("Country1", "City1")
    assert search_geo(sample_data, 35, sample_mapping) == ("Country2", "City2")


def test_ip_string_input(sample_data, sample_mapping):
    assert search_geo(sample_data, "10.0.0.0/16", sample_mapping) == (
        "Unknown",
        "Unknown",
    )


def test_unsorted_data():
    data = [(30, 40, 2), (10, 20, 1), (50, 60, 3)]
    mapping = {1: ("A", "B"), 2: ("C", "D"), 3: ("E", "F")}
    assert search_geo(data, 15, mapping) == ("A", "B")


def test_sorted_data():
    data = [(10, 20, 1), (30, 40, 2), (50, 60, 3)]
    mapping = {1: ("A", "B"), 2: ("C", "D"), 3: ("E", "F")}
    assert search_geo(data, 35, mapping, is_sorted=True) == ("C", "D")


def test_no_match(sample_data, sample_mapping):
    assert search_geo(sample_data, 5, sample_mapping) == ("Unknown", "Unknown")
    assert search_geo(sample_data, 25, sample_mapping) == ("Unknown", "Unknown")
    assert search_geo(sample_data, 65, sample_mapping) == ("Unknown", "Unknown")


def test_boundary_values(sample_data, sample_mapping):
    assert search_geo(sample_data, 10, sample_mapping) == ("Country1", "City1")
    assert search_geo(sample_data, 20, sample_mapping) == ("Country1", "City1")
    assert search_geo(sample_data, 30, sample_mapping) == ("Country2", "City2")


def test_missing_mapping(sample_data):
    assert search_geo(sample_data, 15, {}) == ("Unknown", "Unknown")
    assert search_geo(sample_data, 35, {2: ("X", "Y")}) == ("X", "Y")


def test_large_input():
    data = [(i * 10, i * 10 + 9, i) for i in range(1000)]
    mapping = {i: (f"Country{i}", f"City{i}") for i in range(1000)}
    assert search_geo(data, 5005, mapping) == ("Country500", "City500")
