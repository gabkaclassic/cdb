import pytest
from ipaddress import IPv4Network
from cdb import mmdb_to_cdb


@pytest.fixture
def sample_mmdb_data():
    return [
        (
            "192.168.1.0/24",
            {
                "country": {"names": {"en": "Country1"}},
                "city": {"names": {"en": "City1"}},
            },
        ),
        (
            "10.0.0.0/8",
            {
                "country": {"names": {"en": "Country2"}},
                "city": {"names": {"en": "City2"}},
            },
        ),
    ]


@pytest.fixture
def sample_mmdb_file(sample_mmdb_data):
    def mock_read_mmdb(path):
        return sample_mmdb_data

    return mock_read_mmdb


def test_mmdb_to_cdb_basic(sample_mmdb_data):
    cdb_data, mapping = mmdb_to_cdb(sample_mmdb_data)
    assert len(cdb_data) == 2
    assert len(mapping) == 2
    assert all(len(item) == 3 for item in cdb_data)
    assert all(isinstance(v, tuple) for v in mapping.values())


def test_mmdb_to_cdb_with_mapping(sample_mmdb_data):
    existing_mapping = {("Country1", "City1"): 42}
    cdb_data, mapping = mmdb_to_cdb(sample_mmdb_data, existing_mapping)
    assert mapping[42] == ("Country1", "City1")
    assert len(mapping) == 2


def test_mmdb_to_cdb_empty_data():
    cdb_data, mapping = mmdb_to_cdb([])
    assert cdb_data == []
    assert mapping == {}


def test_mmdb_to_cdb_ipv4network_input():
    test_data = [
        (
            IPv4Network("192.168.1.0/24"),
            {
                "country": {"names": {"en": "Country1"}},
                "city": {"names": {"en": "City1"}},
            },
        )
    ]
    cdb_data, mapping = mmdb_to_cdb(test_data)
    assert len(cdb_data) == 1
    assert mapping[0] == ("Country1", "City1")


def test_mmdb_to_cdb_duplicate_geo():
    test_data = [
        (
            "192.168.1.0/24",
            {
                "country": {"names": {"en": "Country1"}},
                "city": {"names": {"en": "City1"}},
            },
        ),
        (
            "10.0.0.0/8",
            {
                "country": {"names": {"en": "Country1"}},
                "city": {"names": {"en": "City1"}},
            },
        ),
    ]
    cdb_data, mapping = mmdb_to_cdb(test_data)
    assert len(cdb_data) == 2
    assert len(mapping) == 1
