import struct
import pytest
from cdb import MAGIC, VERSION, CDBFormatError, serialize, deserialize

HEADER = MAGIC + bytes([VERSION])


@pytest.mark.parametrize(
    "triples,mapping",
    [
        ([], {}),
        ([(1, 2, 3)], {1: ("a", "b")}),
        ([(1, 2, 3), (4, 5, 6)], {1: ("a", "b"), 2: ("c", "d")}),
        ([(0, 2**32 - 1, 2**32 - 1)], {0: ("", ""), 2**32 - 1: ("long string", "x" * 1000)}),
    ],
)
def test_serialize_deserialize_roundtrip(triples, mapping):
    serialized = serialize(triples, mapping)
    deserialized_triples, deserialized_mapping = deserialize(serialized)

    assert deserialized_triples == triples
    assert deserialized_mapping == mapping


def test_serialize_format():
    triples = [(1, 2, 3)]
    mapping = {4: ("test", "data")}
    buf = serialize(triples, mapping)

    assert buf[:4] == HEADER
    (n,) = struct.unpack_from("<I", buf, 4)
    assert n == len(triples)

    for i in range(n):
        a, b, c = struct.unpack_from("<III", buf, 8 + 12 * i)
        assert (a, b, c) == triples[i]

    mapping_offset = 8 + 12 * n
    (m,) = struct.unpack_from("<I", buf, mapping_offset)
    assert m == len(mapping)


def test_deserialize_invalid_data():
    with pytest.raises(CDBFormatError):
        deserialize(b"invalid")

    with pytest.raises(CDBFormatError):
        deserialize(HEADER + struct.pack("<I", 1))


def test_empty_strings_in_mapping():
    triples = []
    mapping = {0: ("", ""), 1: ("x", "")}
    buf = serialize(triples, mapping)
    _, deserialized_mapping = deserialize(buf)
    assert deserialized_mapping == mapping


def test_large_data():
    triples = [(i, i + 1, i + 2) for i in range(1000)]
    mapping = {i: (f"key{i}", f"value{i}") for i in range(100)}
    buf = serialize(triples, mapping)
    deserialized_triples, deserialized_mapping = deserialize(buf)
    assert len(deserialized_triples) == 1000
    assert len(deserialized_mapping) == 100


VALID = serialize([(1, 2, 0), (3, 4, 1)], {0: ("Ä", "b"), 1: ("c", "d")})


@pytest.mark.parametrize("cut", range(len(VALID)))
def test_every_strict_prefix_raises(cut):
    with pytest.raises(CDBFormatError):
        deserialize(VALID[:cut])


def test_trailing_byte_raises():
    with pytest.raises(CDBFormatError):
        deserialize(VALID + b"\x00")


def test_invalid_utf8_raises():
    buf = HEADER + struct.pack("<I", 0) + struct.pack("<I", 1)
    buf += struct.pack("<I", 0) + struct.pack("<H", 1) + b"\xff" + struct.pack("<H", 0)
    with pytest.raises(CDBFormatError):
        deserialize(buf)


def test_v1_bytes_raise():
    with pytest.raises(CDBFormatError):
        deserialize(struct.pack("<I", 0) * 2)


def test_declared_string_length_past_end():
    buf = HEADER + struct.pack("<I", 0) + struct.pack("<I", 1)
    buf += struct.pack("<I", 0) + struct.pack("<H", 100) + b"ab"
    with pytest.raises(CDBFormatError):
        deserialize(buf)


@pytest.mark.parametrize(
    "triples,mapping",
    [
        ([(-1, 2, 0)], {}),
        ([(0, 2**32, 0)], {}),
        ([(0, 1, 0)], {2**32: ("a", "b")}),
        ([], {0: ("x" * 65536, "")}),
        ([], {0: ("", "x" * 65536)}),
    ],
)
def test_serialize_out_of_range_raises(triples, mapping):
    with pytest.raises(ValueError):
        serialize(triples, mapping)


def test_serialize_sorts_input():
    mapping = {1: ("c", "d"), 0: ("a", "b")}
    ordered = [(1, 2, 0), (1, 3, 1), (5, 6, 0)]
    expected = serialize(ordered, mapping)
    assert serialize(list(reversed(ordered)), mapping) == expected
    assert serialize(set(ordered), mapping) == expected
    assert serialize(ordered, dict(sorted(mapping.items()))) == expected
    triples, mapped = deserialize(expected)
    assert triples == ordered
    assert list(mapped) == [0, 1]


def test_bad_magic():
    with pytest.raises(CDBFormatError, match="bad magic"):
        deserialize(b"XYZ\x02" + b"\x00" * 8)


@pytest.mark.parametrize("version", [0, 1, 3, 255])
def test_unsupported_version(version):
    buf = MAGIC + bytes([version]) + b"\x00" * 8
    with pytest.raises(CDBFormatError, match=f"unsupported version {version}"):
        deserialize(buf)


@pytest.mark.parametrize("short", [b"", b"C", b"CDB"])
def test_truncated_header(short):
    with pytest.raises(CDBFormatError):
        deserialize(short)


@pytest.mark.parametrize("char", ["\n", "\t", "\x1b", "\x7f", "\x00"])
@pytest.mark.parametrize("position", [0, 1])
def test_serialize_control_char_raises(char, position):
    geo = ["ok", "ok"]
    geo[position] = f"a{char}b"
    with pytest.raises(ValueError):
        serialize([], {0: tuple(geo)})


@pytest.mark.parametrize("char", ["\n", "\t", "\x1b", "\x7f"])
@pytest.mark.parametrize("position", [0, 1])
def test_deserialize_control_char_raises(char, position):
    strings = [b"ok", b"ok"]
    strings[position] = f"a{char}b".encode()
    buf = HEADER + struct.pack("<I", 0) + struct.pack("<I", 1) + struct.pack("<I", 0)
    for raw in strings:
        buf += struct.pack("<H", len(raw)) + raw
    with pytest.raises(CDBFormatError):
        deserialize(buf)
