import contextlib
import sys
import pytest
from ipaddress import IPv4Network, IPv6Network
from cdb import mmdb_file_to_cdb, mmdb_to_cdb, read_cdb, read_mmdb, search_geo


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


PRIVATE = (IPv4Network("0.0.0.0/8"), {"country": {"iso_code": "PRIVATE"}})
AU = (
    IPv4Network("1.0.4.0/22"),
    {
        "country": {
            "iso_code": "AU",
            "names": {"de": "Australien", "en": "Australia"},
        }
    },
)
JP6 = (
    IPv6Network("2001:200::/32"),
    {
        "continent": {"code": "AS"},
        "country": {"iso_code": "JP", "names": {"de": "Japan", "en": "Japan"}},
    },
)


def patch_open(monkeypatch, records):
    monkeypatch.setattr(
        sys.modules["cdb.cdb"].maxminddb,
        "open_database",
        lambda path: contextlib.nullcontext(records),
    )


def test_ipv6_skipped():
    data, mapping = mmdb_to_cdb([JP6, ("2001:db8::/32", AU[1]), AU])
    assert len(data) == 1
    assert mapping == {0: ("Australia", "")}


def test_iso_only_record():
    data, mapping = mmdb_to_cdb([PRIVATE])
    assert mapping == {0: ("PRIVATE", "")}
    assert data == [(0, 2**24 - 1, 0)]


def test_no_country_key():
    _, mapping = mmdb_to_cdb([("1.0.0.0/24", {})])
    assert mapping == {0: ("", "")}


def test_locale_de():
    _, mapping = mmdb_to_cdb([AU], locale="de")
    assert mapping == {0: ("Australien", "")}


def test_locale_falls_back_to_en():
    _, mapping = mmdb_to_cdb([AU], locale="fr")
    assert mapping == {0: ("Australia", "")}


def test_existing_mapping_preserved_and_not_mutated():
    existing = {("A", "B"): 5}
    data, mapping = mmdb_to_cdb([AU], existing)
    assert existing == {("A", "B"): 5}
    assert mapping[5] == ("A", "B")
    assert data[0][2] == 6
    assert mapping[6] == ("Australia", "")


def test_unsorted_input_sorted_output():
    data, _ = mmdb_to_cdb([AU, PRIVATE])
    assert data == sorted(data)
    assert data[0][0] == 0


def test_mmdb_file_to_cdb_streams(monkeypatch, tmp_path):
    patch_open(monkeypatch, [AU, JP6, PRIVATE])
    out = tmp_path / "o.cdb"
    mmdb_file_to_cdb("ignored", str(out), locale="de")
    data, mapping = read_cdb(str(out))
    assert data == sorted(data)
    assert search_geo(data, "1.0.4.1", mapping) == ("Australien", "")
    assert search_geo(data, "0.1.2.3", mapping) == ("PRIVATE", "")


def test_read_mmdb(monkeypatch):
    records = [AU, PRIVATE]
    patch_open(monkeypatch, records)
    assert read_mmdb("ignored") == records
