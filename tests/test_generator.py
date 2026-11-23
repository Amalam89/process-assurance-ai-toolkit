import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from generate_synthetic import generate  # noqa: E402


def test_generator_writes_tables_and_answer_key(tmp_path):
    key = generate(seed=42, out_dir=tmp_path)
    for name in ["requirements", "tests", "trace_links", "reviews", "defects", "capas"]:
        assert (tmp_path / "raw" / f"{name}.csv").exists()
    assert json.loads((tmp_path / "planted_gaps.json").read_text())["seed"] == 42
    assert all(count > 0 for count in key["gap_counts"].values())


def test_generator_is_deterministic(tmp_path):
    assert generate(seed=42, out_dir=tmp_path / "a") == generate(seed=42, out_dir=tmp_path / "b")


def test_db_matches_planted_req_without_test(tmp_path):
    key = generate(seed=42, out_dir=tmp_path)
    con = sqlite3.connect(tmp_path / "pa.db")
    rows = con.execute(
        "SELECT r.req_id FROM requirements r "
        "LEFT JOIN trace_links t ON t.req_id = r.req_id WHERE t.test_id IS NULL"
    ).fetchall()
    con.close()
    assert sorted(r[0] for r in rows) == key["gaps"]["req_without_test"]
