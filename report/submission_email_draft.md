# Draft submission email (not sent; send it yourselves)

**To:** monitirtha@isibang.ac.in, mohd.khalid.stats@gmail.com, curmisha2@gmail.com, ishan.sharma.stats@gmail.com
**Subject:** ASM II Group Project (Type I) report: Aayush Jha, Ankit Roy, Faaz Noushad
**Attach:** `ASM2_Group_Project_Report.pdf`. If you present before the end-semester
exam, also attach `ASM2_Group_Project_Slides.pdf` at least 24 hours before the
presentation.
**Deadline:** 11:59 PM on 25 November 2026, the ASM II end-semester exam date.

---

Dear Sir,

Please find attached the report for our ASM II Type I group project, "Does a
Pending-Sector Warning Predict Hard-Drive Failure? A Survival Analysis of Backblaze
Drive Stats, Q1 2026".

As proposed on 6 October, we studied whether a pre-specified SMART indicator (SMART 197,
the pending-sector count) is associated with subsequent drive failure. We used
Kaplan–Meier estimation and a Cox proportional-hazards model on a single drive model
(Seagate ST12000NM0008, 18,533 drives), with sensitivity analyses for drives that
disappear from the data. We also fitted a model adjusting for age, using powered-on
hours, because installation dates are not published.

In brief:

- Drives with a nonzero baseline SMART 197 had a hazard ratio of 43.2 (95% CI
  28.1–66.3) for a recorded failure, or 43.6 after adjusting for powered-on age, so we
  reject the null hypothesis.
- The excess risk is concentrated in the first month, and the proportional-hazards
  assumption is rejected.
- Backblaze counts SMART-triggered proactive replacements as failures, so we interpret
  the result as an association rather than a causal effect.

The code and analysis records are in our repository: [add link if you wish to share it].

Thanking you,
Yours sincerely,
Aayush Jha, Ankit Roy, Faaz Noushad
[Roll numbers]
