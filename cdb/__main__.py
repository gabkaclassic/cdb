import argparse
import sys
from ipaddress import IPv4Address

import maxminddb

from .cdb import merge_cdbs_and_save, mmdb_file_to_cdb, read_cdb, search_geo


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cdb")
    sub = parser.add_subparsers(dest="command", required=True)

    convert = sub.add_parser("convert")
    convert.add_argument("mmdb")
    convert.add_argument("cdb")
    convert.add_argument("--locale", default="en")

    lookup = sub.add_parser("lookup")
    lookup.add_argument("cdb")
    lookup.add_argument("ips", nargs="+", metavar="IP")

    merge = sub.add_parser("merge")
    merge.add_argument("output")
    merge.add_argument("inputs", nargs="+", metavar="INPUT")

    return parser


def _run(args: argparse.Namespace) -> None:
    if args.command == "convert":
        mmdb_file_to_cdb(args.mmdb, args.cdb, args.locale)
    elif args.command == "lookup":
        values = [(ip, int(IPv4Address(ip))) for ip in args.ips]
        networks, mapping = read_cdb(args.cdb)
        lines = []
        for ip, value in values:
            country, city = search_geo(networks, value, mapping)
            lines.append(f"{ip}\t{country}\t{city}\n")
        sys.stdout.write("".join(lines))
    else:
        merge_cdbs_and_save(args.output, *args.inputs)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        _run(args)
    except (OSError, ValueError, maxminddb.InvalidDatabaseError) as exc:
        print(f"cdb: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
