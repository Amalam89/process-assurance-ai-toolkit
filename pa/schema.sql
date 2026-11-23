-- Process Assurance toolkit schema (SQLite). All data is synthetic.
DROP TABLE IF EXISTS requirements;
DROP TABLE IF EXISTS tests;
DROP TABLE IF EXISTS trace_links;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS defects;
DROP TABLE IF EXISTS capas;

CREATE TABLE requirements (
    req_id    TEXT PRIMARY KEY,
    project   TEXT NOT NULL,
    title     TEXT NOT NULL,
    priority  TEXT NOT NULL,          -- High | Medium | Low
    status    TEXT NOT NULL           -- Approved
);

CREATE TABLE tests (
    test_id     TEXT PRIMARY KEY,
    project     TEXT NOT NULL,
    title       TEXT NOT NULL,
    last_result TEXT NOT NULL,        -- pass | fail | not_run
    last_run    TEXT                  -- ISO date, NULL when not_run
);

CREATE TABLE trace_links (
    req_id  TEXT NOT NULL REFERENCES requirements(req_id),
    test_id TEXT NOT NULL REFERENCES tests(test_id),
    PRIMARY KEY (req_id, test_id)
);

CREATE TABLE reviews (
    review_id     TEXT PRIMARY KEY,
    artifact_id   TEXT NOT NULL,      -- a req_id or test_id
    artifact_type TEXT NOT NULL,      -- requirement | test
    review_date   TEXT NOT NULL,
    reviewer      TEXT NOT NULL,
    signed_off    INTEGER NOT NULL    -- 1 = signed, 0 = missing sign-off
);

CREATE TABLE defects (
    defect_id     TEXT PRIMARY KEY,
    project       TEXT NOT NULL,
    component     TEXT NOT NULL,
    severity      TEXT NOT NULL,      -- Critical | Major | Minor
    opened        TEXT NOT NULL,
    closed        TEXT,
    description   TEXT NOT NULL,
    root_cause    TEXT NOT NULL,      -- ground-truth label (see docs/DESIGN.md)
    linked_req_id TEXT REFERENCES requirements(req_id)
);

CREATE TABLE capas (
    capa_id                TEXT PRIMARY KEY,
    defect_id              TEXT NOT NULL REFERENCES defects(defect_id),
    opened                 TEXT NOT NULL,
    due_date               TEXT NOT NULL,
    closed_date            TEXT,
    effectiveness_verified INTEGER NOT NULL  -- 1 = verified, 0 = not verified
);
