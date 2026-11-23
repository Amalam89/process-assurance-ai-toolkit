# Design

Synthetic data only. No real company names, products or records.

## Root-cause categories

| Category | Meaning |
| --- | --- |
| Requirements | Missing, ambiguous, conflicting or changed requirement |
| Design | Architecture or design did not handle a case |
| Code/Logic | Implementation bug |
| Test gap | Missing, wrong or too-narrow test let the defect escape |
| Configuration/Build | Wrong config, build or release setting |
| Integration/Interface | Two parts disagree on an interface or message |
| Process/Documentation | Process step skipped, or docs/instructions wrong |
| Supplier | Third-party part, firmware or library at fault |

## Tables

See `pa/schema.sql`: requirements, tests, trace_links, reviews, defects, capas.
"As of" date for overdue checks: 2026-11-22.

## Checks (pa/traceability.py)

| Check | Rule |
| --- | --- |
| req_without_test | Requirement with no row in trace_links |
| test_without_req | Test with no row in trace_links (orphan) |
| req_with_failed_or_unrun_test | Requirement linked to a test whose last_result is fail or not_run |
| review_unsigned | Review with signed_off = 0 |
| defect_without_req | Defect with linked_req_id NULL |
| capa_overdue | CAPA with no closed_date and due_date before the as-of date |
| capa_closed_without_effectiveness | Closed CAPA with effectiveness_verified = 0 |

`data/planted_gaps.json` lists the exact items planted for each check. The checks must find exactly those.

**Audit-readiness score per project** = 100 × the average, across checks, of (items passing ÷ items checked).

## Metrics (pa/metrics.py)

- Defect Pareto by root cause: count and cumulative %
- CAPA aging buckets: 0–30, 31–60, 61–90, 90+ days
- CAPA on-time closure rate by month
- Repeat defects: same component and root cause within 90 days (planted pairs are in `recurrence_pairs`)
- Monthly defect trend by severity

## AI triage (pa/classify.py, pa/llm.py)

- Baseline: TF-IDF (1–2 word n-grams) + logistic regression, 80/20 stratified split.
- LLM: fixed category list, JSON output validated with pydantic, temperature 0.
- Send to human review when: output invalid, confidence < 0.7, or LLM and baseline disagree.
- Log every decision to an `audit_log` table: time, item, model, prompt version, input hash, output, route.

## Task automation (pa/tasks.py)

- One task per gap; `correlation_id = "PA-" + sha1(check|item_id)[:12]` so a gap never becomes two tasks.
- `--dry-run` (default) writes `data/out/tasks_preview.json`; `--live` checks ServiceNow for the
  correlation_id first, then creates only missing tasks.
