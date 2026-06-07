# hyperloglog

[![tests](https://github.com/MONISMALIK1/hyperloglog/actions/workflows/test.yml/badge.svg)](https://github.com/MONISMALIK1/hyperloglog/actions/workflows/test.yml)

**Count distinct elements in kilobytes** — a from-scratch, dependency-free
implementation of **HyperLogLog**. Estimate how many *unique* items are in a massive
stream (unique visitors, distinct IPs, distinct keys) with ~1% error using a fixed
few kilobytes — no growing set, no second pass.

> Flajolet, Fusy, Gandouet, Meunier (2007), *HyperLogLog: the analysis of a
> near-optimal cardinality estimation algorithm.*
> [hal-00406166](https://hal.science/hal-00406166v1)

## The real problem

You want the number of **distinct** things in a huge stream — `COUNT(DISTINCT)` over
billions of rows, unique users across a day of logs, distinct keys before a shuffle.
The exact way is to keep every distinct value in a set: memory grows with the number
of distinct items, so it doesn't fit. HyperLogLog estimates the same number in
**constant** memory (e.g. 16 KB), which is why it backs Redis `PFCOUNT`, BigQuery
`APPROX_COUNT_DISTINCT`, Presto, and Druid.

## How it works

```
item ──hash──► 1011010…           uniform random bits
                │└──── remaining bits: count leading zeros ► a "run length"
                └── first p bits choose 1 of m = 2^p registers
register[idx] = max(register[idx], run_length)     keep the longest run seen
                │
estimate = α_m · m² / Σ 2^(−register[j])           bias-corrected harmonic mean
```

A run of `k` leading zeros is something you'd expect to see about once every `2ᵏ`
distinct items — so the longest run across `m` registers, combined carefully,
estimates the cardinality. Standard error is **≈ 1.04/√m**, independent of how many
elements you stream. Two corner cases from the paper are handled: **linear counting**
for small cardinalities and a **large-range correction** near 2³².

## Use

```bash
# estimate distinct lines in a file (or stdin)
python -m hyperloglog access.log
cat access.log | python -m hyperloglog -

# smaller/coarser sketch, or show the exact count + actual error
python -m hyperloglog ids.txt --precision 12
python -m hyperloglog ids.txt --exact
```

Example (`--exact` on ~50k distinct values out of 200k lines):

```
lines read:        200000
estimated distinct: 49819
sketch memory:     16384 bytes (p=14, std error ~0.81%)
exact distinct:    49082
actual error:      1.50%
```

As a library:

```python
from hyperloglog import HyperLogLog

hll = HyperLogLog(p=14)            # ~16 KB, ~0.8% standard error
for event in stream:
    hll.add(event.user_id)
print(len(hll))                    # estimated distinct users

# mergeable: combine per-shard sketches into a global count
total = shard_a.union(shard_b)
blob = hll.to_bytes()             # serialize to ship/store
```

## Why it's *mergeable* (and why that matters)

Each register holds a max, so the union of two sets is just the **register-wise max**
of their sketches — no re-scan. Count distinct per shard/day/server independently,
then `union` the tiny sketches for an exact-as-the-model-allows global distinct count.
That's what makes HyperLogLog a fit for distributed systems.

## Design

| Module | Responsibility |
| --- | --- |
| `hll.py` | the sketch: `add`, `count`/`len`, `merge`/`union`, `to_bytes`/`from_bytes`, both range corrections |
| `__main__.py` | CLI — estimate distinct lines from a file or stdin, optional `--exact` |

Hashing uses `blake2b` (stdlib), so estimates are **reproducible** run-to-run.

## Test

```bash
make test        # or: python -m unittest discover -s hyperloglog/tests -t . -v
```

14 tests checking estimates against **known cardinalities** (small/medium/large,
linear-counting and main regimes), idempotence, the merge/union law, the error-rate
formula, and serialization round-trips.

## Accuracy & limitations

- **Standard error ≈ 1.04/√m.** p=14 → m=16384 → ~0.8% in 16 KB; p=12 → ~1.6% in 4 KB.
- **Estimate, not exact.** Great for "how many distinct," not for "is *x* in the set"
  (that's a Bloom/Cuckoo filter) or for listing the items.
- **32-bit hashing.** The classic 2007 variant; the large-range correction handles the
  approach to 2³². For cardinalities past a few billion, 64-bit hashing (HyperLogLog++)
  is the next step.

## License

MIT
