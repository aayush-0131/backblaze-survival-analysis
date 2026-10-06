# SMART 9: nominal powered hours, not physical installation age

## Documentation

VERIFIED FACT: the [WD Ultrastar HC570 SATA manual](https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/data-center-drives/ultrastar-dc-hc500-series/product-manual-ultrastar-dc-hc570-sata-oem-spec.pdf)
revision 1.3, February 26, 2024, identifies WUH722222ALE6L4 on its cover and
lists attribute 9 as Power-On Hours Count in section 12.55.2.2, printed page 310.
It describes raw attribute bytes as vendor-specific and normalized values as
converted measurements. This establishes the nominal attribute, not every
firmware's raw decoding or the exact snapshot timestamp.

VERIFIED FACT: the [Seagate Exos X14 manual](https://www.seagate.com/www-content/product-content/enterprise-hdd-fam/exos-x-14/en-us/docs/100835941e.pdf)
100835941 Rev. E, April 2020, includes ST12000NM0008 and power-on-hour device
statistics. A model-specific SMART-9 raw byte/unit definition was not established
from that document. [Seagate SeaChest guidance](https://www.seagate.com/old-support-files/seachest/SeaChest_Combo_UserGuides.html)
warns that SMART attributes/thresholds can be vendor-specific. Do not substitute
an SSD attribute definition or treat normalized SMART 9 as hours.

## Measured evidence: Q2 2023 only

All quantiles below are exact nearest-rank drive-day quantiles, not independent
drive samples. `smart9_consistency.csv` also provides p05/p25/p75/p95/p99.

| Quantity | Seagate | WDC |
|---|---:|---:|
| Reported / drive-days | 1,763,812 / 1,763,868 | 328 / 328 |
| Missing / zero reported rows | 56 / 30 | 0 / 0 |
| Min / median / max raw | 0 / 27,706 / 32,652 | 909 / 2,067 / 3,097 |
| Valid consecutive-observation pairs | 1,743,930 | 324 |
| Missing-endpoint pairs | 108 | 0 |
| Increasing / unchanged / decreasing | 1,741,282 / 2,648 / 0 | 324 / 0 / 0 |
| Reset candidates | 0 | 0 |
| Delta > calendar hours + 48 | 180 | 0 |
| Flagged drives | 180 | 0 |
| Adjacent-date median delta | 31 | 31 |
| Median pair delta / calendar hours | 1.29167 | 1.00000 |
| Endpoint drives with both counters | 19,827 | 4 |
| Endpoint ratio p05 / median / p95 | 0.99352 / 0.99907 / 1.00602 | 0.99900 / 0.99900 / 1.00301 |

VERIFIED FACT: adjacent Seagate deltas most often equal 16 (677,560 pairs),
32 (552,069), 31 (322,805) or 15 (144,655); WDC similarly has 32 (131),
16 (128), 31 (29), 15 (27). Only 1.47% / 2.16% of all valid pairs are within
two units of calendar hours. Daily equality to 24 is therefore an inappropriate
integrity requirement. Endpoint ratios use first-to-last observed raw change
divided by calendar hours; they are descriptive arithmetic, not fitted regressions.

INFERENCE: long-span ratios near one plus nominal documentation support hours
as the likely unit for these observed populations. Alternating 16/32-like daily
deltas could reflect collection timing or delayed updates; exact cause is unknown.
Zero decreases is reassuring within this window, not proof of lifetime continuity.
The four WDC drives are far too few to validate every drive/firmware in Q1 2026.

OPEN PROBLEM: 180 excess-change flags (0.0103% of Seagate valid pairs), firmware
details, zero counters, Q1 daily integrity and the source of synchronized
collection irregularities. Review flags do not establish a reset or impossible
physical change: date-only records lack measurement timestamps. The flagged
rows remain in all counts and in the ignored per-serial anomaly extract.

## Gaps and age use

Seagate has 30,631 gap pairs: 25,307 calendar-like, 21 unchanged, 2,838 with
partial powered-time change, zero decreasing, and 2,465 excess/ambiguous. WDC
has eight: seven calendar-like, one ambiguous. These classifications assume
nominal hours; they do not identify storage, replacement, powered-off state or
continued service. Whole-window ratios include gaps and do not erase them.

VERIFIED FACT: Q1 aggregate SMART-9 coverage is 1,664,551/1,664,558 Seagate
rows (seven missing, zero zero-values) and 3,992,942/3,992,942 WDC rows
(132 zero-values). Q1 distributions, resets, jumps and serial continuity are
unavailable from these aggregates.

PROPOSED METHOD: audit Q1 pairs and baseline counter quality before using
SMART 9 as a baseline powered-age descriptor. Keep missing/zero/anomalous states
explicit. Do not impute, silently remove drives or subtract powered hours from
calendar dates to invent installation dates. A drive can have powered hours
before its earliest Backblaze record; powered time omits powered-off life.
SMART-9-based delayed entry remains deferred. Calendar follow-up is preferred
for the proposed baseline-warning design.
