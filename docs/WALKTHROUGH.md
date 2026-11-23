# Walkthrough: key terms and how the starter code works

Read this with the code open side by side. Line numbers refer to `data/generate_synthetic.py`.

## Key terms

**Root cause.** The underlying reason a defect happened, not the symptom.
Symptom: "the map froze." Root cause: "the spec never said what to do when GPS drops out" (a Requirements cause).
Fix the root cause and the whole class of defect stops; fix only the symptom and it comes back.

**CAPA (Corrective and Preventive Action).** The formal fix after a serious problem.
- *Corrective* = fix this problem now.
- *Preventive* = change the process so it can't happen again.
- Lifecycle: opened → due date → closed → **effectiveness check** (did the fix actually work, or did the defect come back?).
- An auditor's red flags: CAPAs past their due date, and CAPAs closed without an effectiveness check.

**Defect Pareto.** The 80/20 rule applied to defects: a few root causes produce most of the defects.
A Pareto chart sorts causes from most to fewest, with a running cumulative %, so the team fixes the biggest causes first.
Example: Code/Logic 52, Test gap 39, Design 38… the top 3 causes cover about half of all defects.

**Baseline: TF-IDF (1–2 word n-grams).** The simple, non-AI model the LLM must beat.
- *TF-IDF* turns text into numbers: a word scores high if it appears often in this defect but rarely across all defects.
  "the" scores near zero; "firmware" scores high.
- *1–2 word n-grams* = it scores single words ("timeout") and word pairs ("peer review", "feature flag"). Pairs carry meaning single words miss.
- Logistic regression then learns which scored words point to which root cause.
- Why a baseline: if the LLM can't beat a 20-line classic model, it isn't worth its cost. And when the two disagree, a person reviews the defect.

## pa/schema.sql: the 6 tables

Think of it as the paper trail of a software project.

| Table | One row is | Links to |
| --- | --- | --- |
| requirements | Something the system must do ("shall support seat pairing") | trace_links |
| tests | A test case and its last result (pass / fail / not_run) | trace_links |
| trace_links | One "this test verifies this requirement" link | requirements + tests |
| reviews | A peer review of a requirement or test, signed off or not | a req or test id |
| defects | A bug: component, severity, description, root cause, linked requirement | requirements |
| capas | The formal fix for a serious defect, with dates and effectiveness check | defects |

`trace_links` is the heart of traceability: every requirement should have at least one test, and every test should trace to a requirement.
A missing link in either direction is an audit gap.

## data/generate_synthetic.py: section by section

**Lines 23–88: setup.**
- `AS_OF` fixes "today" at 2026-11-22, so "overdue" means the same thing every run.
- `PROJECTS`, `COMPONENTS`, `FEATURES`, `CONDITIONS` are the vocabulary for fake records.
- `TEMPLATES` holds 4 sentence templates per root-cause category. They are the ground truth: a defect built from a Supplier template *is* a Supplier defect.

**Lines 91–108: helpers.**
- `_rand_date` picks a random date in a range.
- `_fill` drops random components, features and conditions into a template.
- `_description` builds a defect description. 20% of the time it adds a clue from a *different* category ("Also noted: …"), so some defects are ambiguous, like real ones. Without this, any model would score 100% and the test would prove nothing.

**Line 110: `generate()` and the seed.**
`random.Random(seed)` makes every "random" choice repeatable. Seed 42 always gives the same data, so tests and results can be reproduced. That's why your accidental double-click changed nothing.

**Lines 120–133: requirements and tests.** 300 requirements and 450 tests spread over 3 projects. Each test gets a result: about 5% not_run, 6% fail, the rest pass.

**Lines 135–154: trace links (the planted traceability gaps).**
Per project, it deliberately picks about 10% of requirements to get *no* test, and about 5% of tests to stay orphaned.
It records those ids in `gaps[...]` *before* linking, then links every other test to a requirement.
This is the key idea: the generator knows the right answer, so your checks can be graded.

**Lines 156–166: reviews.** 200 reviews; about 10% have `signed_off = 0`, the missing sign-off gap.

**Lines 168–197: defects.**
- `weights` makes some causes more common (Code/Logic most), so the Pareto has a real shape instead of a flat line.
- About 15% of defects get no linked requirement, another traceability gap.
- Then it plants 15 repeat defects: a copy of an earlier defect's component and root cause, 20–80 days later. The metrics module must detect these.

**Lines 199–222: CAPAs.** One CAPA per serious (Critical or Major) defect, up to 80. Due date = opened + 30 days. Each is randomly set to overdue, closed late, or closed on time. About 15% of closed ones skip the effectiveness check.

**Lines 224–233: output.** Writes the 6 tables to CSV and SQLite, and saves `planted_gaps.json`: the answer key with every planted gap's ids and counts.

**Lines 236–256: writers.** `_write_csvs` writes one CSV per table. `_write_db` runs `schema.sql` to create empty tables, then inserts every row.

## How the tests prove it works (tests/test_generator.py)

1. All 6 CSVs and the answer key get written, and every gap type has at least one planted item.
2. Same seed, same output: determinism.
3. A real SQL check (requirements with no trace link) returns *exactly* the ids in the answer key.
Test 3 is the pattern for all of Monday's work: write a check, then prove it matches `planted_gaps.json`.

## Check yourself

You understand the starter code when you can answer these without looking:
1. Why plant gaps instead of using random data?
2. What would break if there were no seed?
3. Why are the cause weights uneven?
4. Why are 20% of descriptions ambiguous?
5. Which table makes traceability possible, and what are the two gap directions?
6. What does an effectiveness check prove?
