"""Generate synthetic Process Assurance data with deliberately planted gaps.

Everything here is fake. The script writes:
  data/raw/*.csv           one CSV per table
  data/pa.db               SQLite database (schema in pa/schema.sql)
  data/planted_gaps.json   the answer key: which items were planted as gaps

Usage:
  python data/generate_synthetic.py            # default seed 42
  python data/generate_synthetic.py --seed 7
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "pa" / "schema.sql"
AS_OF = date(2026, 11, 22)  # "today" for overdue checks

PROJECTS = ["IFE-Seatback", "Connectivity-Gateway", "Crew-Tablet"]
COMPONENTS = ["Media Player", "Seat Display", "Network Gateway",
              "Content Loader", "Moving Map", "Crew Panel"]
FEATURES = ["parental controls", "moving map", "Wi-Fi portal login",
            "seat pairing", "audio language selection", "crew announcements"]
CONDITIONS = ["low bandwidth", "a seat power cycle", "rapid channel switching",
              "a flight longer than 14 hours", "a mid-flight content update",
              "a language change"]
REVIEWERS = ["R. Chen", "M. Ortiz", "S. Patel", "J. Kim", "A. Novak"]

# Root-cause categories (keep in sync with docs/DESIGN.md)
TEMPLATES: dict[str, list[str]] = {
    "Requirements": [
        "Requirement for {feature} was ambiguous; build did not match the airline's expectation.",
        "Spec for {feature} had no acceptance criteria, so behavior during {condition} was undefined.",
        "Customer changed the {feature} requirement after baseline; software follows the old spec.",
        "Two requirements for {feature} conflict on timeout behavior.",
    ],
    "Design": [
        "{component} architecture does not handle {condition}.",
        "Design of {component} did not account for {condition}.",
        "State machine in {component} can reach an invalid state during {condition}.",
        "{component} design assumes a single user session; fails with {feature}.",
    ],
    "Code/Logic": [
        "Null reference in {component} when {condition} occurs.",
        "Off-by-one error in {component} list index skips the last item.",
        "Race condition in {component} threads during {condition}.",
        "Wrong unit conversion in {component} shows incorrect values.",
    ],
    "Test gap": [
        "Scenario with {condition} was not covered by the test suite and escaped to the field.",
        "No regression test for {component} after the last change.",
        "Test case for {feature} checked the wrong expected value and passed anyway.",
        "{feature} was only tested on one seat model.",
    ],
    "Configuration/Build": [
        "Wrong configuration file deployed to {component}.",
        "Build pulled an outdated library version for {component}.",
        "Feature flag for {feature} left disabled in the release config.",
        "{component} image built with debug settings enabled.",
    ],
    "Integration/Interface": [
        "{component} and {component2} disagree on the message format.",
        "API version mismatch between {component} and the ground server.",
        "Timeout calling the {component2} interface from {component}.",
        "{component} sends {feature} events that {component2} does not recognize.",
    ],
    "Process/Documentation": [
        "Peer review was skipped before merging the {component} change.",
        "Release notes omitted a known issue in {component}.",
        "Work instruction for loading {feature} content is out of date.",
        "Change to {component} was made without an approved change request.",
    ],
    "Supplier": [
        "Third-party codec in {component} crashes during {condition}.",
        "Supplier firmware for {component} delivered without a change log.",
        "Vendor library in {component} fails its license check at boot.",
        "Supplier part in {component} does not meet the agreed spec under {condition}.",
    ],
}
CATEGORIES = list(TEMPLATES)


def _rand_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _fill(rng: random.Random, template: str) -> str:
    c1, c2 = rng.sample(COMPONENTS, 2)
    return template.format(component=c1, component2=c2,
                           feature=rng.choice(FEATURES),
                           condition=rng.choice(CONDITIONS))


def _description(rng: random.Random, category: str) -> str:
    text = _fill(rng, rng.choice(TEMPLATES[category]))
    if rng.random() < 0.20:  # ~20% ambiguous: add a clue from another category
        other = rng.choice([c for c in CATEGORIES if c != category])
        text += " Also noted: " + _fill(rng, rng.choice(TEMPLATES[other])).lower()
    return text


def generate(seed: int = 42, out_dir: Path | None = None,
             n_reqs: int = 300, n_tests: int = 450, n_reviews: int = 200,
             n_defects: int = 250) -> dict:
    """Build all tables, write CSVs + SQLite + planted_gaps.json, return the answer key."""
    rng = random.Random(seed)
    out_dir = Path(out_dir) if out_dir else ROOT / "data"
    raw = out_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    gaps: dict[str, list] = {}

    # Requirements and tests, split across projects
    reqs = [{"req_id": f"REQ-{i:04d}", "project": PROJECTS[i % 3],
             "title": f"The system shall support {rng.choice(FEATURES)} ({i})",
             "priority": rng.choice(["High", "Medium", "Low"]), "status": "Approved"}
            for i in range(1, n_reqs + 1)]
    tests = []
    for i in range(1, n_tests + 1):
        r = rng.random()
        result = "not_run" if r < 0.05 else "fail" if r < 0.11 else "pass"
        last_run = None if result == "not_run" else \
            _rand_date(rng, date(2026, 6, 1), AS_OF).isoformat()
        tests.append({"test_id": f"TC-{i:04d}", "project": PROJECTS[i % 3],
                      "title": f"Verify {rng.choice(FEATURES)} ({i})",
                      "last_result": result, "last_run": last_run})

    # Trace links: ~10% of reqs get no test, ~5% of tests stay orphaned
    links: list[dict] = []
    gaps["req_without_test"], gaps["test_without_req"] = [], []
    for project in PROJECTS:
        p_reqs = [r["req_id"] for r in reqs if r["project"] == project]
        p_tests = [t["test_id"] for t in tests if t["project"] == project]
        no_test = set(rng.sample(p_reqs, round(len(p_reqs) * 0.10)))
        orphans = set(rng.sample(p_tests, round(len(p_tests) * 0.05)))
        gaps["req_without_test"] += sorted(no_test)
        gaps["test_without_req"] += sorted(orphans)
        covered = [r for r in p_reqs if r not in no_test]
        linkable = [t for t in p_tests if t not in orphans]
        rng.shuffle(linkable)
        for idx, test_id in enumerate(linkable):  # every linkable test gets one req
            links.append({"req_id": covered[idx % len(covered)], "test_id": test_id})
    gaps["req_without_test"].sort()
    gaps["test_without_req"].sort()
    result_of = {t["test_id"]: t["last_result"] for t in tests}
    gaps["req_with_failed_or_unrun_test"] = sorted(
        {link["req_id"] for link in links if result_of[link["test_id"]] != "pass"})

    # Reviews: ~10% missing sign-off
    reviews = []
    for i in range(1, n_reviews + 1):
        is_req = rng.random() < 0.6
        artifact = rng.choice(reqs)["req_id"] if is_req else rng.choice(tests)["test_id"]
        reviews.append({"review_id": f"RV-{i:04d}", "artifact_id": artifact,
                        "artifact_type": "requirement" if is_req else "test",
                        "review_date": _rand_date(rng, date(2026, 1, 1), AS_OF).isoformat(),
                        "reviewer": rng.choice(REVIEWERS),
                        "signed_off": 0 if rng.random() < 0.10 else 1})
    gaps["review_unsigned"] = [r["review_id"] for r in reviews if not r["signed_off"]]

    # Defects: ~15% with no linked requirement, plus planted repeat defects
    weights = [14, 12, 22, 14, 10, 12, 9, 7]  # uneven so the Pareto has a shape
    defects = []
    for i in range(1, n_defects + 1):
        cat = rng.choices(CATEGORIES, weights=weights)[0]
        project = rng.choice(PROJECTS)
        opened = _rand_date(rng, date(2025, 11, 1), date(2026, 10, 31))
        closed = opened + timedelta(days=rng.randint(3, 60)) if rng.random() < 0.8 else None
        if closed and closed > AS_OF:
            closed = None
        p_reqs = [r["req_id"] for r in reqs if r["project"] == project]
        defects.append({"defect_id": f"DEF-{i:04d}", "project": project,
                        "component": rng.choice(COMPONENTS),
                        "severity": rng.choices(["Critical", "Major", "Minor"], [1, 3, 6])[0],
                        "opened": opened.isoformat(),
                        "closed": closed.isoformat() if closed else None,
                        "description": _description(rng, cat), "root_cause": cat,
                        "linked_req_id": None if rng.random() < 0.15 else rng.choice(p_reqs)})
    # Repeat defects: copy component + root cause, 20-80 days after the original
    gaps["recurrence_pairs"] = []
    for k, original in enumerate(rng.sample(defects, 15)):
        opened = date.fromisoformat(original["opened"]) + timedelta(days=rng.randint(20, 80))
        if opened > AS_OF:
            continue
        repeat_id = f"DEF-{n_defects + k + 1:04d}"
        defects.append({**original, "defect_id": repeat_id, "opened": opened.isoformat(),
                        "closed": None,
                        "description": _description(rng, original["root_cause"])})
        gaps["recurrence_pairs"].append([original["defect_id"], repeat_id])
    gaps["defect_without_req"] = [d["defect_id"] for d in defects if d["linked_req_id"] is None]

    # CAPAs on Critical/Major defects: ~20% overdue, ~15% closed late,
    # ~15% of closed ones never checked for effectiveness
    capas = []
    serious = [d for d in defects if d["severity"] != "Minor"]
    for i, d in enumerate(rng.sample(serious, min(80, len(serious))), start=1):
        opened = date.fromisoformat(d["opened"]) + timedelta(days=rng.randint(1, 5))
        due = opened + timedelta(days=30)
        r = rng.random()
        if r < 0.20 and due < AS_OF:
            closed = None                                    # overdue
        elif r < 0.35:
            closed = due + timedelta(days=rng.randint(1, 25))  # closed late
        else:
            closed = opened + timedelta(days=rng.randint(5, 29))  # on time
        if closed and closed > AS_OF:
            closed = None
        verified = 0 if closed and rng.random() < 0.15 else (1 if closed else 0)
        capas.append({"capa_id": f"CAPA-{i:03d}", "defect_id": d["defect_id"],
                      "opened": opened.isoformat(), "due_date": due.isoformat(),
                      "closed_date": closed.isoformat() if closed else None,
                      "effectiveness_verified": verified})
    gaps["capa_overdue"] = [c["capa_id"] for c in capas
                            if c["closed_date"] is None and c["due_date"] < AS_OF.isoformat()]
    gaps["capa_closed_without_effectiveness"] = [
        c["capa_id"] for c in capas if c["closed_date"] and not c["effectiveness_verified"]]

    tables = {"requirements": reqs, "tests": tests, "trace_links": links,
              "reviews": reviews, "defects": defects, "capas": capas}
    _write_csvs(raw, tables)
    _write_db(out_dir / "pa.db", tables)
    key = {"seed": seed, "as_of": AS_OF.isoformat(),
           "counts": {name: len(rows) for name, rows in tables.items()},
           "gaps": gaps, "gap_counts": {k: len(v) for k, v in gaps.items()}}
    (out_dir / "planted_gaps.json").write_text(json.dumps(key, indent=2))
    return key


def _write_csvs(raw: Path, tables: dict[str, list[dict]]) -> None:
    for name, rows in tables.items():
        with open(raw / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def _write_db(path: Path, tables: dict[str, list[dict]]) -> None:
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA.read_text())
        for name, rows in tables.items():
            cols = list(rows[0])
            con.executemany(
                f"INSERT INTO {name} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                [tuple(r[c] for c in cols) for r in rows])
        con.commit()
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = generate(seed=args.seed)
    print("Rows:", result["counts"])
    print("Planted gaps:", result["gap_counts"])
