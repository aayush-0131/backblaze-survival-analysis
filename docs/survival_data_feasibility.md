# Survival-data feasibility — Backblaze Q1 2026

## VERIFIED FACT

- The audited window contains 30,597,484 drive-days for 351,095 unique serial numbers from 2026-01-01 through 2026-03-31.
- There are 1,030 failure rows and 1,030 unique drives with `failure == 1`.
- 345,638 drives have no failure row and are present on the final day; these are candidates for administrative right censoring at the quarter boundary.
- 4,427 drives disappear before quarter end without a failure row. They are **not** relabeled as failures.
- 17,043 drives have an observation gap and subsequently reappear.
- 338,760 drives are already present on the first day of Q1. First observed SMART 9 raw is available for 350,660 drives (99.9%).
- Daily SMART values are repeated longitudinal measurements; daily rows are not statistically independent drive outcomes.
- Backblaze documents that its end-of-day program uses prior presence, disappearance, and a lookback to assign or undo the failure flag. It also states that a drive failing before completing its first day cannot be defined by this program.

## INFERENCE

- Drives present at the left boundary are prevalent drives and likely include units installed before Q1. This makes a Q1-only analysis vulnerable to left truncation/delayed-entry problems if physical age is the target time scale.
- Because source event ascertainment requires prior-day presence, the observed event process conditions on surviving long enough to enter the daily snapshot system. Day-one failures create selection and under-ascertainment risk that Q1 CSVs cannot repair.
- A drive present through 2026-03-31 with no failure row has a defensible administrative censoring time for a quarter-window analysis. Earlier unexplained exits have a different, potentially informative censoring mechanism.
- SMART 9 raw may help approximate accumulated powered time for some models, but its unit and firmware interpretation require model/vendor validation. It is not automatically equivalent to physical drive age.

## OPEN PROBLEM

- Installation/birth dates are not present in the observed Q1 schema.
- The reason for non-failure disappearance is not encoded; retirement, migration, maintenance, missing snapshot, and other mechanisms remain distinguishable only with additional evidence.
- A broader historical scan is needed to determine first appearance in the published history and to assess how much that improves, but does not necessarily solve, the age-origin problem.
- Model-specific SMART semantics and counter resets/wraparound require documentation or empirical validation before SMART 9 is used as an age scale.
- Pooling drive models would mix capacities, firmware families, age distributions, and SMART reporting regimes unless the later design handles that heterogeneity explicitly.
- Raw model labels are not fully canonical: `WDC WUH721816ALE6L4` and `WUH721816ALE6L4` are separate values but jointly reconcile to one official report model. Any cohort using this hardware must apply and validate an explicit alias rule.

## PROPOSED METHOD

### Candidate time origins

1. **Quarter entry / calendar follow-up**: time zero is first observation within Q1. This estimates risk over observed Q1 follow-up, not lifetime-from-installation risk. It requires explicit prevalent-drive language and sensitivity analysis for early non-failure exits.
2. **First appearance in a broader Backblaze history**: time zero is first published appearance. This requires a historical streaming audit and still cannot prove installation coincided with first publication.
3. **Model-validated SMART 9 powered hours**: use a verified powered-time scale with delayed entry at the first observed counter. This requires stable units, monotonicity checks, reset/wrap detection, and adequate reporting for the selected model.
4. **Known installation date**: preferred physical-age origin, but it requires a field or external operational metadata not available in this Q1 audit.

### Event and censoring construction

- Event: first observed row with `failure == 1`; reconcile and flag any serial with repeated failure rows.
- Event interpretation: describe this as a source-defined observed failure, not complete physical-failure ascertainment from installation; day-one failures are outside the daily program's observable event process.
- Administrative right censoring: final Q1 observation for drives still present on 2026-03-31 without failure.
- Earlier non-failure exit: retain as a distinct censoring/exit class and perform mechanism-focused sensitivity work; never silently convert it to failure.
- Observation gaps: retain gap indicators and decide whether a contiguous-risk-interval representation is required.

### Time-varying SMART representation

If SMART attributes are considered later, construct start-stop intervals per drive (for example, one interval per observed day or per value-change interval), with covariates measured before the interval's event boundary. Preserve model-specific missingness indicators and avoid using post-failure information. A later model design must specify lagging, counter transformations, ties, and within-drive dependence. No Cox, Kaplan–Meier, regression, or predictive model is fit in this data gate.

## Gate conclusion

**READY WITH CONDITIONS** for selecting and extending a cohort design. Q1 is adequate to measure drive-day exposure, observed failures, schema/SMART coverage, and censoring patterns. It is not sufficient by itself for a lifetime-from-installation claim. The next action is to reconcile this computational audit with a SMART/literature review, choose one candidate model/cohort, and then run a bounded historical first-appearance plus SMART 9 semantics audit before freezing hypotheses.
