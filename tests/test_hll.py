"""HyperLogLog: accuracy against known cardinalities, merge, and serialization.

Everything is deterministic (blake2b hashing), so these tolerances hold run-to-run.
"""

import unittest

from hyperloglog import HyperLogLog


def _rel_err(est, true):
    return abs(est - true) / true


class AccuracyTests(unittest.TestCase):
    def test_empty_is_zero(self):
        self.assertEqual(len(HyperLogLog(p=14)), 0)

    def test_small_cardinality_linear_counting(self):
        hll = HyperLogLog(p=14)
        for i in range(500):
            hll.add(f"item-{i}")
        self.assertLess(_rel_err(len(hll), 500), 0.05)

    def test_medium_cardinality(self):
        hll = HyperLogLog(p=14)
        for i in range(10_000):
            hll.add(f"item-{i}")
        self.assertLess(_rel_err(len(hll), 10_000), 0.03)

    def test_large_cardinality(self):
        hll = HyperLogLog(p=14)
        for i in range(200_000):
            hll.add(f"k-{i}")
        self.assertLess(_rel_err(len(hll), 200_000), 0.03)

    def test_low_precision_is_less_accurate_but_bounded(self):
        hll = HyperLogLog(p=8)  # m=256 -> ~6.5% std error
        for i in range(50_000):
            hll.add(i)
        self.assertLess(_rel_err(len(hll), 50_000), 0.20)


class BehaviourTests(unittest.TestCase):
    def test_idempotent_adds(self):
        hll = HyperLogLog(p=14)
        for _ in range(100):
            hll.add("same-item")
        self.assertEqual(len(hll), 1)

    def test_handles_mixed_types(self):
        hll = HyperLogLog(p=12)
        hll.add("a")
        hll.add(b"a")          # bytes "a" hashes the same as str "a"
        hll.add(42)
        self.assertGreaterEqual(len(hll), 1)

    def test_precision_validation(self):
        for bad in (3, 17, 0):
            with self.assertRaises(ValueError):
                HyperLogLog(p=bad)

    def test_error_rate_and_memory(self):
        hll = HyperLogLog(p=14)
        self.assertEqual(hll.memory_bytes, 1 << 14)
        self.assertAlmostEqual(hll.error_rate, 1.04 / (1 << 7), places=6)  # sqrt(2^14)=2^7


class MergeTests(unittest.TestCase):
    def test_union_matches_combined_stream(self):
        a, b = HyperLogLog(p=14), HyperLogLog(p=14)
        for i in range(60_000):
            a.add(f"x-{i}")
        for i in range(40_000, 100_000):  # 20k overlap with a
            b.add(f"x-{i}")
        union = a.union(b)
        self.assertLess(_rel_err(len(union), 100_000), 0.03)  # true union = 100k distinct

    def test_merge_is_in_place(self):
        a, b = HyperLogLog(p=12), HyperLogLog(p=12)
        a.add("one")
        b.add("two")
        a.merge(b)
        self.assertGreaterEqual(len(a), 2)

    def test_precision_mismatch_raises(self):
        with self.assertRaises(ValueError):
            HyperLogLog(p=12).merge(HyperLogLog(p=14))


class SerializationTests(unittest.TestCase):
    def test_roundtrip_preserves_estimate(self):
        hll = HyperLogLog(p=12)
        for i in range(5_000):
            hll.add(i)
        blob = hll.to_bytes()
        restored = HyperLogLog.from_bytes(blob)
        self.assertEqual(restored.p, hll.p)
        self.assertEqual(len(restored), len(hll))

    def test_corrupt_data_raises(self):
        with self.assertRaises(ValueError):
            HyperLogLog.from_bytes(bytes([14, 0, 0, 0]))  # wrong register count for p=14


if __name__ == "__main__":
    unittest.main()
