"""hyperloglog — count distinct elements in kilobytes, from scratch, zero deps.

Estimate the number of distinct items in a massive stream with ~1% error using a
few kilobytes — no growing set, no second pass.

Reference: Flajolet, Fusy, Gandouet, Meunier (2007), "HyperLogLog: the analysis of
a near-optimal cardinality estimation algorithm."

    from hyperloglog import HyperLogLog

    hll = HyperLogLog(p=14)          # ~16 KB, ~0.8% standard error
    for line in huge_stream:
        hll.add(line)
    print(len(hll))                  # estimated distinct count
"""

from __future__ import annotations

__version__ = "0.1.0"

from .hll import HyperLogLog

__all__ = ["__version__", "HyperLogLog"]
