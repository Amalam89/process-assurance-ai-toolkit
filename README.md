# Process Assurance AI Toolkit

Python tools that help a software Process Assurance team find traceability gaps, trend defect and CAPA data,
triage root causes with AI under human review, and open follow-up tasks automatically.
All data is synthetic.

> Work in progress. See `docs/DESIGN.md` for the plan.

## Quickstart (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python data\generate_synthetic.py
pytest -q
```
