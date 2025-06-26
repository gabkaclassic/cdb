import pytest
from cdb import cidr_to_int
from ipaddress import IPv4Address, IPv4Network


@pytest.mark.parametrize(
    "cidr,expected_start,expected_end",
    [
        ("192.168.1.0/24", 3232235776, 3232236031),
        ("10.0.0.0/8", 167772160, 184549375),
        ("172.16.0.0/12", 2886729728, 2887778303),
        ("0.0.0.0/0", 0, 4294967295),
        ("255.255.255.255/32", 4294967295, 4294967295),
        ("128.0.0.0/1", 2147483648, 4294967295),
    ],
)
def test_cidr_to_int_with_broadcast(cidr, expected_start, expected_end):
    result = cidr_to_int(cidr, with_broadcast=True)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result == (expected_start, expected_end)


@pytest.mark.parametrize(
    "cidr,expected",
    [
        ("192.168.1.0/24", 3232235776),
        ("10.0.0.0/8", 167772160),
        ("0.0.0.0/0", 0),
        ("255.255.255.255/32", 4294967295),
    ],
)
def test_cidr_to_int_without_broadcast(cidr, expected):
    result = cidr_to_int(cidr, with_broadcast=False)
    assert isinstance(result, int)
    assert result == expected


def test_invalid_cidr():
    with pytest.raises(ValueError):
        cidr_to_int("invalid_cidr", with_broadcast=True)


def test_network_address_calculation():
    cidr = "192.168.1.128/25"
    network = IPv4Network(cidr, strict=False)
    expected_start = int(IPv4Address(network.network_address))
    expected_end = int(IPv4Address(network.broadcast_address))

    result = cidr_to_int(cidr, with_broadcast=True)
    assert result == (expected_start, expected_end)

    result_single = cidr_to_int(cidr, with_broadcast=False)
    assert result_single == expected_start


def test_return_types():
    assert isinstance(cidr_to_int("10.0.0.0/8", True), tuple)
    assert isinstance(cidr_to_int("10.0.0.0/8", False), int)
