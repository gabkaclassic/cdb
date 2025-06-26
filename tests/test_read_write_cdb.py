import pytest
import os
from tempfile import NamedTemporaryFile
from cdb import read_cdb, write_cdb
import struct


def test_read_cdb_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_cdb("non_existent_file.cdb")


def test_write_and_read_empty_cdb():
    with NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        write_cdb([], {}, tmp_path)
        result_networks, result_mapping = read_cdb(tmp_path)
        assert result_networks == []
        assert result_mapping == {}
    finally:
        os.unlink(tmp_path)


def test_write_and_read_simple_cdb():
    networks = [(10, 20, 0), (30, 40, 1)]
    mapping = {0: ("Country1", "City1"), 1: ("Country2", "City2")}

    with NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        write_cdb(networks, mapping, tmp_path)
        result_networks, result_mapping = read_cdb(tmp_path)
        assert result_networks == networks
        assert result_mapping == mapping
    finally:
        os.unlink(tmp_path)


def test_write_and_read_large_cdb():
    networks = [(i, i + 1, i % 10) for i in range(1000)]
    mapping = {i: (f"Country{i}", f"City{i}") for i in range(10)}

    with NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        write_cdb(networks, mapping, tmp_path)
        result_networks, result_mapping = read_cdb(tmp_path)
        assert len(result_networks) == 1000
        assert len(result_mapping) == 10
    finally:
        os.unlink(tmp_path)


def test_write_cdb_invalid_path():
    with pytest.raises(OSError):
        write_cdb([], {}, "/invalid/path/database.cdb")


def test_read_cdb_invalid_data():
    with NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        with open(tmp_path, "wb") as f:
            f.write(b"invalid_data")

    try:
        with pytest.raises(struct.error):
            read_cdb(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_write_cdb_special_characters():
    networks = [(1, 2, 0)]
    mapping = {0: ("Страна", "Город")}

    with NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        write_cdb(networks, mapping, tmp_path)
        _, result_mapping = read_cdb(tmp_path)
        assert result_mapping[0] == ("Страна", "Город")
    finally:
        os.unlink(tmp_path)
