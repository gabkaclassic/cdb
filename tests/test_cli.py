import contextlib
import subprocess
import sys
from ipaddress import IPv4Network
from pathlib import Path

import pytest

from cdb import merge_cdbs, read_cdb, write_cdb
from cdb.__main__ import main

EXPECTED = "10.1.2.3\tCountry1\tCity1\n8.8.8.8\tUnknown\tUnknown\n"


@pytest.fixture
def cdb_file(tmp_path):
    path = tmp_path / "a.cdb"
    write_cdb([(167772160, 184549375, 0)], {0: ("Country1", "City1")}, str(path))
    return str(path)


def test_lookup(cdb_file, capsys):
    assert main(["lookup", cdb_file, "10.1.2.3", "8.8.8.8"]) == 0
    assert capsys.readouterr().out == EXPECTED


def test_merge(cdb_file, tmp_path, capsys):
    other = tmp_path / "b.cdb"
    write_cdb([(16777216, 16777471, 0)], {0: ("Country2", "City2")}, str(other))
    out = tmp_path / "out.cdb"
    assert main(["merge", str(out), cdb_file, str(other)]) == 0
    assert capsys.readouterr().out == ""
    assert read_cdb(str(out)) == merge_cdbs(cdb_file, str(other))


@pytest.mark.parametrize(
    "locale_args, country",
    [([], "Australia"), (["--locale", "de"], "Australien")],
)
def test_convert(monkeypatch, tmp_path, capsys, locale_args, country):
    records = [
        (
            IPv4Network("1.0.4.0/22"),
            {
                "country": {
                    "iso_code": "AU",
                    "names": {"de": "Australien", "en": "Australia"},
                }
            },
        )
    ]
    monkeypatch.setattr(
        sys.modules["cdb.cdb"].maxminddb,
        "open_database",
        lambda path: contextlib.nullcontext(records),
    )
    out = tmp_path / "out.cdb"
    assert main(["convert", "ignored.mmdb", str(out), *locale_args]) == 0
    assert capsys.readouterr().out == ""
    assert main(["lookup", str(out), "1.0.4.1"]) == 0
    assert capsys.readouterr().out.split("\t")[1] == country


def test_missing_file(tmp_path, capsys):
    assert main(["lookup", str(tmp_path / "missing.cdb"), "1.1.1.1"]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("cdb: ")
    assert captured.out == ""


def test_non_cdb_file(tmp_path, capsys):
    path = tmp_path / "bad.cdb"
    path.write_bytes(b"not a cdb file")
    assert main(["lookup", str(path), "1.1.1.1"]) == 1
    assert capsys.readouterr().err.startswith("cdb: ")


def test_invalid_ip(cdb_file, capsys):
    assert main(["lookup", cdb_file, "not-an-ip"]) == 1
    assert capsys.readouterr().err.startswith("cdb: ")


@pytest.mark.parametrize("bad", ["8.8.8.8/8", "::1"])
def test_lookup_rejects_non_ipv4(cdb_file, capsys, bad):
    assert main(["lookup", cdb_file, "10.1.2.3", bad]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("cdb: ")
    assert captured.out == ""


def test_merge_dangling_geo_id(cdb_file, tmp_path, capsys):
    dangling = tmp_path / "dangling.cdb"
    write_cdb([(1, 2, 9)], {0: ("A", "B")}, str(dangling))
    out = tmp_path / "out.cdb"
    assert main(["merge", str(out), cdb_file, str(dangling)]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("cdb: ")
    assert str(dangling) in captured.err
    assert not out.exists()


def test_no_subcommand():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_subprocess(cdb_file):
    result = subprocess.run(
        [sys.executable, "-m", "cdb", "lookup", cdb_file, "10.1.2.3"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout == "10.1.2.3\tCountry1\tCity1\n"
