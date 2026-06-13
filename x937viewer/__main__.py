"""Entry point.

    python -m x937viewer                       launch the GUI
    python -m x937viewer file.x937             open file in the GUI
    python -m x937viewer --to-json file.x937   convert to Moov-style JSON (stdout)
    python -m x937viewer --to-json file.x937 -o out.json
"""

from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="x937viewer",
        description="View X9.37 Image Cash Letter files or convert them to "
                    "Moov imagecashletter-compatible JSON.")
    ap.add_argument("file", nargs="?", help="X9.37 file to open")
    ap.add_argument("--to-json", action="store_true",
                    help="convert FILE to JSON instead of opening the GUI")
    ap.add_argument("-o", "--output", help="write JSON to this path instead of stdout")
    ap.add_argument("--indent", type=int, default=4, help="JSON indent (default 4)")
    args = ap.parse_args(argv)

    if args.to_json:
        if not args.file:
            ap.error("--to-json requires a FILE")
        from .parser import parse_file
        from .json_export import to_json, write_json
        f = parse_file(args.file)
        for warning in f.warnings:
            print(f"warning: {warning}", file=sys.stderr)
        if args.output:
            write_json(f, args.output, indent=args.indent)
            print(f"wrote {args.output}", file=sys.stderr)
        else:
            print(to_json(f, indent=args.indent))
        return 0

    from .gui.main_window import run
    return run(args.file)


if __name__ == "__main__":
    raise SystemExit(main())
