import os
import struct
import maxminddb
from ipaddress import IPv4Address, IPv4Network


def read_mmdb(
    file_path: str,
) -> list[tuple[str | IPv4Network, dict[str, dict[str, dict[str, str]]]]]:
    with maxminddb.open_database(file_path) as reader:
        return list(reader)

def cidr_to_int(cidr: str, with_broadcast: bool = True) -> int | tuple[int, int]:
    network = IPv4Network(cidr, strict=False)
    
    if with_broadcast:
        return int(IPv4Address(network.network_address)), int(IPv4Address(network.broadcast_address))
    else:
        return int(IPv4Address(network.network_address))

def mmdb_file_to_cdb(mmdb_path: str, cdb_path: str):
    mmdb_data = read_mmdb(mmdb_path)
    cdb_data, mapping = mmdb_to_cdb(mmdb_data)
    write_cdb(cdb_data, mapping, cdb_path)

def mmdb_to_cdb(
    ips: list[str | IPv4Network, dict[str, dict[str, dict[str, str]]]],
    mapping: dict[tuple[str, str], int] = None,
) -> tuple[list[tuple[int, int, int]], dict[int, tuple[str, str]]]:
    prepared = []
    mapping = mapping or {}

    for ip, data in ips:
        geo = (
            list(data.get("country", {}).get("names", {}).values())[0],
            list(data.get("city", {}).get("names", {}).values())[0],
        )

        if geo in mapping:
            geo_code = mapping.get(geo)
        else:
            geo_code = len(mapping)
            mapping[geo] = geo_code
        prepared.append(
            (
                *cidr_to_int(ip),
                geo_code,
            )
        )

    return prepared, {v: k for k, v in mapping.items()}


def serialize(
    triples: list[tuple[int, int, int]], mapping: dict[int, tuple[str, str]]
) -> bytes:
    parts = [struct.pack("<I", len(triples))]
    for a, b, c in triples:
        parts.append(struct.pack("<qqq", a, b, c))
    parts.append(struct.pack("<I", len(mapping)))
    for v, (s1, s2) in mapping.items():
        b1, b2 = s1.encode(), s2.encode()
        parts.append(struct.pack("<q", v))
        parts.append(struct.pack("<H", len(b1)) + b1)
        parts.append(struct.pack("<H", len(b2)) + b2)
    return b"".join(parts)


def deserialize(
    buf: bytes,
) -> tuple[list[tuple[int, int, int]], dict[int, tuple[str, str]]]:
    off = 0
    (n,) = struct.unpack_from("<I", buf, off)
    off += 4
    triples = []
    for _ in range(n):
        triples.append(tuple(struct.unpack_from("<qqq", buf, off)))
        off += 24
    (m,) = struct.unpack_from("<I", buf, off)
    off += 4
    mapping = {}
    for _ in range(m):
        (k,) = struct.unpack_from("<q", buf, off)
        off += 8
        (l1,) = struct.unpack_from("<H", buf, off)
        off += 2
        s1 = buf[off : off + l1].decode()
        off += l1
        (l2,) = struct.unpack_from("<H", buf, off)
        off += 2
        s2 = buf[off : off + l2].decode()
        off += l2
        mapping[k] = (s1, s2)

    return triples, mapping


def search_geo(
    info: list[tuple[int, int, int]], ip: str, mapping: dict[int, tuple[str, str]]
) -> tuple[str, str]:
    value = cidr_to_int(ip, with_broadcast=False)
    info = sorted(info, key=lambda x: (x[0], x[1]))
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


def merge_cdbs(
    *filepaths: str,
) -> tuple[list[tuple[int, int, int], dict[int, tuple[str, str]]]]:
    networks = set()
    mapping = {}

    for filepath in filepaths:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File {filepath} not exists")

        with open(filepath, "rb") as file:
            current_networks, current_mapping = deserialize(file.read())
            mapping.update(current_mapping)
            networks = networks.union(set(current_networks))
            del current_networks
            del current_mapping
    return networks, mapping


def merge_cdbs_and_save(
    output_path: str,
    *filepaths: str,
):
    networks = set()
    mapping = {}

    networks, mapping = merge_cdbs(*filepaths)
    
    write_cdb(networks, mapping, output_path)

def read_cdb(filepath: str) -> tuple[list[tuple[int, int, int], dict[int, tuple[str, str]]]]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File {filepath} not exists")

    with open(filepath, "rb") as file:
        return deserialize(file.read())
    
def write_cdb(ips: list[tuple[int, int, int]], mapping: dict[int, tuple[str, str]], filepath: str):
    with open(filepath, "wb") as file:
        file.write(serialize(ips, mapping))