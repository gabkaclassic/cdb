import struct
from collections.abc import Iterable
from ipaddress import IPv4Network, IPv6Network
from typing import Any

import maxminddb

__all__ = [
    "CDBFormatError",
    "MAGIC",
    "VERSION",
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
]

MAGIC = b"CDB"
VERSION = 2

Triple = tuple[int, int, int]
Mapping = dict[int, tuple[str, str]]
MmdbRecord = tuple[str | IPv4Network | IPv6Network, dict[str, Any]]


class CDBFormatError(ValueError):
    pass


def read_mmdb(file_path: str) -> list[MmdbRecord]:
    with maxminddb.open_database(file_path) as reader:
        return list(reader)


def cidr_to_int(cidr: str, with_broadcast: bool = True) -> int | tuple[int, int]:
    network = IPv4Network(cidr, strict=False)

    if with_broadcast:
        return int(network.network_address), int(network.broadcast_address)
    else:
        return int(network.network_address)


def mmdb_file_to_cdb(mmdb_path: str, cdb_path: str, locale: str = "en") -> None:
    with maxminddb.open_database(mmdb_path) as reader:
        cdb_data, mapping = mmdb_to_cdb(reader, locale=locale)
    write_cdb(cdb_data, mapping, cdb_path)


def _has_control(text: str) -> bool:
    return any(ord(c) < 0x20 or ord(c) == 0x7F for c in text)


def _name(section: dict[str, Any], locale: str) -> str:
    names = section.get("names", {})
    return names.get(locale) or names.get("en") or section.get("iso_code", "")


def _coalesce(ordered: list[Triple]) -> list[Triple]:
    merged: list[Triple] = []
    for start, end, geo in ordered:
        if merged and merged[-1][2] == geo and merged[-1][1] + 1 == start:
            merged[-1] = (merged[-1][0], end, geo)
        else:
            merged.append((start, end, geo))
    return merged


def mmdb_to_cdb(
    ips: Iterable[MmdbRecord],
    mapping: dict[tuple[str, str], int] | None = None,
    locale: str = "en",
) -> tuple[list[Triple], Mapping]:
    prepared = []
    mapping = dict(mapping or {})
    next_id = max(mapping.values(), default=-1) + 1

    for ip, data in ips:
        if isinstance(ip, IPv6Network) or (isinstance(ip, str) and ":" in ip):
            continue

        geo = (
            _name(data.get("country", {}), locale),
            _name(data.get("city", {}), locale),
        )

        if geo == ("", ""):
            continue

        if geo not in mapping:
            mapping[geo] = next_id
            next_id += 1
        if isinstance(ip, IPv4Network):
            bounds = int(ip.network_address), int(ip.broadcast_address)
        else:
            bounds = cidr_to_int(str(ip))
        prepared.append((*bounds, mapping[geo]))

    return _coalesce(sorted(prepared)), {v: k for k, v in mapping.items()}


def serialize(triples: Iterable[Triple], mapping: Mapping) -> bytes:
    ordered = sorted(triples)
    try:
        parts = [MAGIC, bytes([VERSION]), struct.pack("<I", len(ordered))]
        for a, b, c in ordered:
            parts.append(struct.pack("<III", a, b, c))
        parts.append(struct.pack("<I", len(mapping)))
        for geo_id, (country, city) in sorted(mapping.items()):
            if _has_control(country) or _has_control(city):
                raise ValueError("control character in name")
            b1, b2 = country.encode(), city.encode()
            parts.append(struct.pack("<I", geo_id))
            parts.append(struct.pack("<H", len(b1)) + b1)
            parts.append(struct.pack("<H", len(b2)) + b2)
    except struct.error as e:
        raise ValueError(str(e)) from e
    return b"".join(parts)


def _read_string(buf: bytes, off: int) -> tuple[str, int]:
    (length,) = struct.unpack_from("<H", buf, off)
    off += 2
    raw = buf[off : off + length]
    if len(raw) != length:
        raise CDBFormatError("truncated string")
    return raw.decode(), off + length


def deserialize(buf: bytes) -> tuple[list[Triple], Mapping]:
    if buf[:3] != MAGIC or len(buf) < 4:
        raise CDBFormatError("bad magic")
    if buf[3] != VERSION:
        raise CDBFormatError(f"unsupported version {buf[3]}")
    try:
        off = 4
        (n,) = struct.unpack_from("<I", buf, off)
        off += 4
        if off + 12 * n > len(buf):
            raise CDBFormatError("truncated ranges")
        triples = []
        for _ in range(n):
            triples.append(struct.unpack_from("<III", buf, off))
            off += 12
        (m,) = struct.unpack_from("<I", buf, off)
        off += 4
        mapping = {}
        for _ in range(m):
            (geo_id,) = struct.unpack_from("<I", buf, off)
            off += 4
            country, off = _read_string(buf, off)
            city, off = _read_string(buf, off)
            if _has_control(country) or _has_control(city):
                raise CDBFormatError("control character in name")
            mapping[geo_id] = (country, city)
    except struct.error as e:
        raise CDBFormatError("truncated data") from e
    except UnicodeDecodeError as e:
        raise CDBFormatError("invalid utf-8") from e
    if off != len(buf):
        raise CDBFormatError("trailing bytes")
    return triples, mapping


def sort_data(info: list[Triple]) -> list[Triple]:
    return sorted(info, key=lambda x: (x[0], x[1]))


def search_geo(
    info: list[Triple],
    ip: str | int,
    mapping: Mapping,
    is_sorted: bool = True,
) -> tuple[str, str]:
    value = ip if isinstance(ip, int) else cidr_to_int(ip, with_broadcast=False)
    info = info if is_sorted else sort_data(info)
    left, right = 0, len(info) - 1
    best_match = None

    while left <= right:
        mid = (left + right) // 2
        a, b, val = info[mid]

        if a <= value <= b:
            best_match = val
            right = mid - 1
        elif value < a:
            right = mid - 1
        else:
            left = mid + 1

    return mapping.get(best_match, ("Unknown", "Unknown"))


def merge_cdbs(*filepaths: str) -> tuple[list[Triple], Mapping]:
    networks = set()
    mapping = {}
    reverse_mapping = {}

    for filepath in filepaths:
        current_networks, current_mapping = read_cdb(filepath)
        for a, b, old_id in current_networks:
            geo = current_mapping.get(old_id)
            if geo is None:
                raise CDBFormatError(f"{filepath}: unknown geo id {old_id}")
            if geo in reverse_mapping:
                new_id = reverse_mapping[geo]
            else:
                new_id = len(mapping)
                mapping[new_id] = geo
                reverse_mapping[geo] = new_id

            networks.add((a, b, new_id))

    return sorted(networks), mapping


def merge_cdbs_and_save(output_path: str, *filepaths: str) -> None:
    networks, mapping = merge_cdbs(*filepaths)
    write_cdb(networks, mapping, output_path)


def read_cdb(filepath: str) -> tuple[list[Triple], Mapping]:
    with open(filepath, "rb") as file:
        return deserialize(file.read())


def write_cdb(ips: Iterable[Triple], mapping: Mapping, filepath: str) -> None:
    data = serialize(ips, mapping)
    with open(filepath, "wb") as file:
        file.write(data)
