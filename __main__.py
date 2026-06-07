"""CLI: estimate distinct lines in a file or stdin.

Usage:
    python -m hyperloglog access.log                 # estimate distinct lines
    cat access.log | python -m hyperloglog -         # from stdin
    python -m hyperloglog ids.txt --precision 12     # smaller sketch, coarser
    python -m hyperloglog ids.txt --exact            # also show the exact count + error
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .hll import HyperLogLog


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="hyperloglog",
        description="Estimate the number of distinct lines using HyperLogLog "
                    "(Flajolet et al., 2007) — constant memory, ~1% error.",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("path", nargs="?", default="-",
                    help="Input file, or '-' for stdin (default).")
    ap.add_argument("--precision", "-p", type=int, default=14,
                    help="Register bits p (4-16); m=2^p registers (default: 14).")
    ap.add_argument("--exact", action="store_true",
                    help="Also compute the exact distinct count and the error (uses full memory).")
    args = ap.parse_args()

    hll = HyperLogLog(p=args.precision)
    exact: set | None = set() if args.exact else None

    stream = sys.stdin if args.path == "-" else open(args.path, encoding="utf-8", errors="replace")
    try:
        n = 0
        for line in stream:
            line = line.rstrip("\n")
            if not line:
                continue
            n += 1
            hll.add(line)
            if exact is not None:
                exact.add(line)
    finally:
        if stream is not sys.stdin:
            stream.close()

    est = len(hll)
    print(f"lines read:        {n}")
    print(f"estimated distinct: {est}")
    print(f"sketch memory:     {hll.memory_bytes} bytes (p={hll.p}, "
          f"std error ~{hll.error_rate * 100:.2f}%)")
    if exact is not None:
        true = len(exact)
        err = abs(est - true) / true * 100 if true else 0.0
        print(f"exact distinct:    {true}")
        print(f"actual error:      {err:.2f}%  (exact set used {true} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
