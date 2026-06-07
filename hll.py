"""HyperLogLog — count distinct elements in tiny, fixed memory.

Reference: Flajolet, Fusy, Gandouet, Meunier (2007), "HyperLogLog: the analysis of
a near-optimal cardinality estimation algorithm."

Intuition: hash each element to a uniform bitstring. The first ``p`` bits choose one
of ``m = 2^p`` registers; in the remaining bits, record the position of the leftmost
1 (i.e. 1 + the run of leading zeros). Seeing a run of ``k`` zeros is evidence the
stream holds ~``2^k`` distinct items. Each register keeps the *maximum* run it has
seen; combining all registers with a bias-corrected harmonic mean yields a
cardinality estimate with standard error ≈ ``1.04/√m`` — independent of how many
elements you actually streamed, in just ``m`` bytes.
"""

from __future__ import annotations

import hashlib
import math

_TWO32 = 1 << 32


def _hash32(item) -> int:
    """A stable 32-bit hash of any item (reproducible across runs/processes)."""
    if isinstance(item, bytes):
        data = item
    elif isinstance(item, str):
        data = item.encode("utf-8")
    else:
        data = str(item).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(data, digest_size=4).digest(), "big")


def _alpha(m: int) -> float:
    """Bias-correction constant α_m from the paper."""
    if m == 16:
        return 0.673
    if m == 32:
        return 0.697
    if m == 64:
        return 0.709
    return 0.7213 / (1.0 + 1.079 / m)


class HyperLogLog:
    """A probabilistic distinct-count sketch.

    >>> hll = HyperLogLog(p=14)
    >>> for i in range(100_000):
    ...     hll.add(f"user-{i}")
    >>> abs(len(hll) - 100_000) / 100_000 < 0.02   # ~1% error in ~16 KB
    True
    """

    def __init__(self, p: int = 14):
        if not 4 <= p <= 16:
            raise ValueError("p (precision) must be between 4 and 16")
        self.p = p
        self.m = 1 << p
        self.alpha = _alpha(self.m)
        self.registers = bytearray(self.m)  # each holds a run-length 0..(32-p+1)

    def add(self, item) -> None:
        x = _hash32(item)
        idx = x >> (32 - self.p)                     # top p bits -> register
        bits = 32 - self.p
        w = x & ((1 << bits) - 1)                    # remaining bits
        rank = bits - w.bit_length() + 1            # 1 + leading zeros (32-p+1 if w==0)
        if rank > self.registers[idx]:
            self.registers[idx] = rank

    def update(self, items) -> "HyperLogLog":
        """Add every element of an iterable. Returns self, so calls can chain."""
        for item in items:
            self.add(item)
        return self

    def count(self) -> int:
        m = self.m
        s = 0.0
        zeros = 0
        for r in self.registers:
            s += 2.0 ** (-r)
            if r == 0:
                zeros += 1
        est = self.alpha * m * m / s

        if est <= 2.5 * m and zeros > 0:
            est = m * math.log(m / zeros)            # small range: linear counting
        elif est > _TWO32 / 30.0:
            est = -_TWO32 * math.log(1.0 - est / _TWO32)  # large range correction
        return int(round(est))

    __len__ = count

    def merge(self, other: "HyperLogLog") -> "HyperLogLog":
        """Fold ``other`` into this sketch in place (register-wise max = set union)."""
        if self.p != other.p:
            raise ValueError("cannot merge sketches with different precision")
        regs, oregs = self.registers, other.registers
        for i in range(self.m):
            if oregs[i] > regs[i]:
                regs[i] = oregs[i]
        return self

    def union(self, other: "HyperLogLog") -> "HyperLogLog":
        """A new sketch for the union of the two element sets."""
        new = HyperLogLog(self.p)
        new.registers = bytearray(self.registers)
        return new.merge(other)

    @property
    def error_rate(self) -> float:
        """Expected relative standard error, ≈ 1.04/√m."""
        return 1.04 / math.sqrt(self.m)

    @property
    def memory_bytes(self) -> int:
        return self.m

    def to_bytes(self) -> bytes:
        """Serialize (1-byte precision header + registers) — e.g. to merge across shards."""
        return bytes([self.p]) + bytes(self.registers)

    @classmethod
    def from_bytes(cls, data: bytes) -> "HyperLogLog":
        hll = cls(p=data[0])
        hll.registers = bytearray(data[1:])
        if len(hll.registers) != hll.m:
            raise ValueError("corrupt sketch: register count does not match precision")
        return hll


__all__ = ["HyperLogLog"]
