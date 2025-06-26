import struct
import pytest
from cdb import serialize, deserialize


@pytest.mark.parametrize(
    "triples,mapping",
    [
        ([], {}),
        ([(1, 2, 3)], {1: ("a", "b")}),
        ([(1, 2, 3), (4, 5, 6)], {1: ("a", "b"), 2: ("c", "d")}),
        ([(2**63 - 1, -(2**63), 0)], {0: ("", ""), -1: ("long string", "x" * 1000)}),
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

    assert len(buf) > 4
    (n,) = struct.unpack_from("<I", buf, 0)
    assert n == len(triples)

    for i in range(n):
        offset = 4 + i * 24
        a, b, c = struct.unpack_from("<qqq", buf, offset)
        assert (a, b, c) == triples[i]

    mapping_offset = 4 + n * 24
    (m,) = struct.unpack_from("<I", buf, mapping_offset)
    assert m == len(mapping)


def test_deserialize_invalid_data():
    with pytest.raises(struct.error):
        deserialize(b"invalid")

    with pytest.raises(struct.error):
        deserialize(struct.pack("<I", 1))


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
