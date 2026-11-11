import pytest
import os
from tempfile import NamedTemporaryFile
from cdb import read_cdb, write_cdb, merge_cdbs, merge_cdbs_and_save


@pytest.fixture
def create_test_file():
    def _create(networks, mapping):
        with NamedTemporaryFile(delete=False, mode="wb") as f:
            write_cdb(networks, mapping, f.name)
            return f.name

    return _create


def test_merge_empty():
    result_networks, result_mapping = merge_cdbs()
    assert result_networks == []
    assert result_mapping == {}


def test_merge_single_file(create_test_file):
    networks = [(10, 20, 0), (30, 40, 1)]
    mapping = {0: ("Country1", "City1"), 1: ("Country2", "City2")}
    file1 = create_test_file(networks, mapping)

    result_networks, result_mapping = merge_cdbs(file1)
    assert len(result_networks) == 2
    assert len(result_mapping) == 2
    os.unlink(file1)


def test_merge_multiple_files(create_test_file):
    networks1 = [(10, 20, 0), (30, 40, 1)]
    mapping1 = {0: ("Country1", "City1"), 1: ("Country2", "City2")}
    file1 = create_test_file(networks1, mapping1)

    networks2 = [(50, 60, 0), (70, 80, 1)]
    mapping2 = {0: ("Country3", "City3"), 1: ("Country4", "City4")}
    file2 = create_test_file(networks2, mapping2)

    result_networks, result_mapping = merge_cdbs(file1, file2)
    assert len(result_networks) == 4
    assert len(result_mapping) == 4
    os.unlink(file1)
    os.unlink(file2)


def test_merge_duplicate_geo(create_test_file):
    networks1 = [(10, 20, 0)]
    mapping1 = {0: ("Country1", "City1")}
    file1 = create_test_file(networks1, mapping1)

    networks2 = [(30, 40, 0)]
    mapping2 = {0: ("Country1", "City1")}
    file2 = create_test_file(networks2, mapping2)

    result_networks, result_mapping = merge_cdbs(file1, file2)
    assert len(result_networks) == 2
    assert len(result_mapping) == 1
    os.unlink(file1)
    os.unlink(file2)


def test_merge_and_save(create_test_file):
    networks1 = [(10, 20, 0)]
    mapping1 = {0: ("Country1", "City1")}
    file1 = create_test_file(networks1, mapping1)

    networks2 = [(30, 40, 0)]
    mapping2 = {0: ("Country2", "City2")}
    file2 = create_test_file(networks2, mapping2)

    with NamedTemporaryFile(delete=False) as output_file:
        output_path = output_file.name

    try:
        merge_cdbs_and_save(output_path, file1, file2)
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0
    finally:
        os.unlink(file1)
        os.unlink(file2)
        os.unlink(output_path)


def test_merge_large_files(create_test_file):
    networks1 = [(i, i + 1, 0) for i in range(0, 1000, 2)]
    mapping1 = {0: ("Country1", "City1")}
    file1 = create_test_file(networks1, mapping1)

    networks2 = [(i, i + 1, 0) for i in range(1, 1000, 2)]
    mapping2 = {0: ("Country2", "City2")}
    file2 = create_test_file(networks2, mapping2)

    result_networks, result_mapping = merge_cdbs(file1, file2)
    assert len(result_networks) == 1000
    assert len(result_mapping) == 2
    os.unlink(file1)
    os.unlink(file2)


def test_merge_sorted_and_deduplicated(create_test_file):
    mapping = {0: ("Country1", "City1")}
    file1 = create_test_file([(30, 40, 0), (10, 20, 0)], mapping)
    file2 = create_test_file([(10, 20, 0), (50, 60, 0)], mapping)

    result_networks, result_mapping = merge_cdbs(file1, file2)
    assert result_networks == [(10, 20, 0), (30, 40, 0), (50, 60, 0)]
    assert result_mapping == {0: ("Country1", "City1")}
    os.unlink(file1)
    os.unlink(file2)


def test_merge_and_save_matches_merge_and_is_deterministic(create_test_file, tmp_path):
    file1 = create_test_file([(30, 40, 0)], {0: ("C2", "D2")})
    file2 = create_test_file([(10, 20, 0)], {0: ("C1", "D1")})
    out1, out2 = tmp_path / "a.cdb", tmp_path / "b.cdb"

    merge_cdbs_and_save(str(out1), file1, file2)
    merge_cdbs_and_save(str(out2), file1, file2)

    assert read_cdb(str(out1)) == merge_cdbs(file1, file2)
    assert out1.read_bytes() == out2.read_bytes()
    os.unlink(file1)
    os.unlink(file2)
