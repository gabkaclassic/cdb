import cdb

EXPECTED = {
    "CDBFormatError",
    "MAGIC",
    "cidr_to_int",
    "deserialize",
    "merge_cdbs",
    "merge_cdbs_and_save",
    "mmdb_file_to_cdb",
    "mmdb_to_cdb",
    "read_cdb",
    "read_mmdb",
    "search_geo",
    "serialize",
    "sort_data",
    "write_cdb",
}


def test_all():
    assert set(cdb.__all__) == EXPECTED


def test_no_leaked_names():
    for name in ("os", "struct", "maxminddb", "IPv4Network"):
        assert not hasattr(cdb, name)
