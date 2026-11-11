# cdb

[![CI](https://github.com/gabkaclassic/cdb/actions/workflows/ci.yml/badge.svg)](https://github.com/gabkaclassic/cdb/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A small Python library and CLI that converts a MaxMind GeoIP database (`.mmdb`) into a compact binary file mapping IPv4 ranges to a country and city name, and looks addresses up in it.

The `.cdb` file keeps only what an IP-to-location lookup needs: IPv4 ranges and one name per location in the language you choose. Everything else in the MaxMind record (IPv6, coordinates, subdivisions, the other seven languages) is dropped. The layout is simple enough to read in any language with a few dozen lines of code.

Measured on a GeoLite2-Country build:

| | Size | Records |
|---|---|---|
| source `.mmdb` | 8.5 MB | 1,078,848 networks (IPv4 + IPv6) |
| `.cdb` | 3.9 MB | 327,348 IPv4 ranges |

Loading that file takes about 0.1 s, a lookup about 12 µs (Python 3.14, binary search over a sorted list).

## Install

Requires Python 3.12+.

```bash
pip install git+https://github.com/gabkaclassic/cdb.git
```

## Command line

```bash
python -m cdb convert GeoLite2-City.mmdb geo.cdb             # English names
python -m cdb convert GeoLite2-City.mmdb geo.de.cdb --locale de
python -m cdb lookup geo.cdb 8.8.8.8 77.88.8.8
python -m cdb merge all.cdb part1.cdb part2.cdb
```

`lookup` prints one tab-separated line per address: the address, country, city. Addresses that aren't in the file print `Unknown` for both. Errors go to stderr as `cdb: <message>` with exit status 1.

## Python

```python
import cdb

cdb.mmdb_file_to_cdb("GeoLite2-City.mmdb", "geo.cdb", locale="en")

ranges, names = cdb.read_cdb("geo.cdb")
cdb.search_geo(ranges, "8.8.8.8", names)       # (country, city)
```

Lower-level functions:

```python
ranges, names = cdb.mmdb_to_cdb(records, locale="en")   # any iterable of (network, record)
data = cdb.serialize(ranges, names)                     # -> bytes
ranges, names = cdb.deserialize(data)                   # raises cdb.CDBFormatError on bad input
cdb.write_cdb(ranges, names, "geo.cdb")
ranges, names = cdb.merge_cdbs("a.cdb", "b.cdb")
cdb.merge_cdbs_and_save("out.cdb", "a.cdb", "b.cdb")
cdb.cidr_to_int("10.0.0.0/8")                           # (167772160, 184549375)
```

`ranges` is a sorted list of `(start, end, geo_id)` tuples with inclusive integer bounds; `names` maps `geo_id` to `(country, city)`.

## How conversion works

- IPv6 networks are skipped.
- A name is taken in the requested locale, then English, then the ISO country code; a missing city becomes an empty string.
- Records with neither a country nor a city (for example, ones carrying only a continent) are skipped.
- Locations are deduplicated, so each `(country, city)` pair is stored once and ranges point to it by id.
- Adjacent ranges that resolve to the same location are merged into one. Lookups return the same result for every address after the merge.

## File format (v2)

Little-endian, no padding.

| Offset | Size | Field |
|---|---|---|
| 0 | 3 | magic `CDB` |
| 3 | 1 | format version, `2` |
| 4 | 4 | `N`, number of ranges (uint32) |
| 8 | 12 × N | ranges: `start`, `end` (inclusive), `geo_id`, each uint32, sorted ascending |
| 8 + 12N | 4 | `M`, number of locations (uint32) |
| ... | M entries | `geo_id` uint32, country length uint16, country UTF-8, city length uint16, city UTF-8 |

Names may not contain control characters (U+0000 to U+001F, U+007F). Nothing may follow the last location. `deserialize` raises `CDBFormatError` (a `ValueError`) on a wrong magic, an unsupported version, truncated data, trailing bytes, invalid UTF-8 or a control character in a name.

## Limitations

- IPv4 only.
- `search_geo` expects ranges sorted and non-overlapping. Files written by this library are sorted; pass `is_sorted=False` for a list you built yourself. Merging files whose ranges overlap gives undefined lookup results.
- Names are limited to 65,535 bytes each.
- Files written by version 0.1 (no magic header) can't be read; convert again from the `.mmdb`.
- Conversion decodes every record of the `.mmdb`: about 11 s for GeoLite2-Country with the `maxminddb` C extension.

## Development

```bash
pip install -e ".[test]"
pytest --cov=cdb
```

GitHub Actions runs the tests on Python 3.12, 3.13 and 3.14.

## License

[MIT](LICENSE). GeoLite2 databases are distributed by MaxMind under their own license and are not included.
