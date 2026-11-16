# Capstone run log — before, criterion 5 (fresh clones)

Criterion 5: *In 3 of 3 fresh clones (new folder, new terminal, no .venv active), following only RUNNING.md, 0 undocumented steps are needed, and each ends with test.py passing, /health returning ok, one /ask returning 200, and logs/requests.jsonl holding exactly 1 line.*

Run on 2026-11-15, 16:38–16:48 PST. Each trial is a new PowerShell process (`pwsh -NoProfile`) that cloned `https://github.com/LuisFVillalon/ai201-project2-fitfindr-starter-v2026.git` (commit `7a6aa51`) into its own empty folder and ran only the steps in RUNNING.md, in order:

1. **From a clean checkout:** `git clone` → `cd` → `python -m venv .venv` → `.venv\Scripts\Activate.ps1` → `pip install -r requirements.txt` → `copy .env.example .env` (then the `GEMINI_API_KEY` line pasted in) → `python test.py`
2. **The one command that starts it:** `python serve.py` (cache left on, the default)
3. **Asking it something:** `curl.exe -s http://localhost:5000/health`, then one `POST /ask` with `{"query": "vintage graphic tee under $30", "user_id": "clone_t<N>"}`
4. Counted the lines in `logs/requests.jsonl`

Nothing changed between trials. Python 3.12.3 on Windows 11.

| Check | Trial 1 | Trial 2 | Trial 3 |
|---|---|---|---|
| No `.venv` active at start | ⚠️ inherited Project 1's `.venv`* | yes | yes |
| Undocumented steps needed | 0 | 0 | 0 |
| `python test.py` | 10 passed, 0 failed | 10 passed, 0 failed | 10 passed, 0 failed |
| `/health` | `{"status":"ok"}` | `{"status":"ok"}` | `{"status":"ok"}` |
| `/ask` | 200 (10,954 ms) | 200 (12,302 ms) | 200 (13,736 ms) |
| Lines in `logs/requests.jsonl` before `serve.py` | 72 | 72 | 72 |
| Lines in `logs/requests.jsonl` after one `/ask` | **73** | **73** | **73** |
| **Meets criterion 5** | **no** | **no** | **no** |

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 5. Starting FitFindr from RUNNING.md alone | 3 of 3 | 0/1 | 0/1 | 0/1 | MISSED |

\* Trial 1 was launched from a shell where Project 1's `.venv` was still set (`VIRTUAL_ENV` pointed at `ai201-project1-.../.venv`). Activating the clone's `.venv` replaced it, so every command ran in the clone's own environment. Trials 2 and 3 cleared `VIRTUAL_ENV` and its `PATH` entry first and started with nothing active. Trial 1 missed on the log count either way.

The only extra output in any trial was pip's `A new release of pip is available` notice, which needs no action.

**Why it missed:** every check passed except the last one. `logs/requests.jsonl` is committed (72 lines, the run record from the cost measurement and the criteria 1–4 trials), and `request_log.py::log_request` appends to that same file. A fresh clone therefore starts with 72 lines and ends with 73. RUNNING.md's clean-checkout steps never say to clear it; that's only under "Resetting between runs".

## The `/ask` line each trial added (`request_log.py::log_request`, called from `serve.py::ask`)

```json
{"timestamp": "2026-11-16T00:41:17.265+00:00", "event": "ask", "user_id": "clone_t1", "query": "vintage graphic tee under $30", "http_status": 200, "duration_ms": 10954, "parsed": {"description": "vintage graphic tee", "size": null, "max_price": 30.0}, "result_count": 10, "selected_item_id": "lst_002", "stopped_early": false, "error": null, "prompt_tokens": 856, "output_tokens": 246}
{"timestamp": "2026-11-16T00:46:04.379+00:00", "event": "ask", "user_id": "clone_t2", "query": "vintage graphic tee under $30", "http_status": 200, "duration_ms": 12302, "parsed": {"description": "vintage graphic tee", "size": null, "max_price": 30.0}, "result_count": 10, "selected_item_id": "lst_002", "stopped_early": false, "error": null, "prompt_tokens": 837, "output_tokens": 229}
{"timestamp": "2026-11-16T00:48:32.863+00:00", "event": "ask", "user_id": "clone_t3", "query": "vintage graphic tee under $30", "http_status": 200, "duration_ms": 13736, "parsed": {"description": "vintage graphic tee", "size": null, "max_price": 30.0}, "result_count": 10, "selected_item_id": "lst_002", "stopped_early": false, "error": null, "prompt_tokens": 841, "output_tokens": 231}
```

## Trial 2, full output (trials 1 and 3 match it apart from timings and tokens)

```
== trial 2  2026-11-15T16:43:35.1568215-08:00
== VIRTUAL_ENV at start: ''
== git clone
Cloning into 'ai201-project2-fitfindr-starter-v2026'...
commit: 7a6aa51
== python -m venv .venv
== .venv\Scripts\Activate.ps1
VIRTUAL_ENV now: ...\clone_trial2\ai201-project2-fitfindr-starter-v2026\.venv
== pip install -r requirements.txt
[notice] A new release of pip is available: 24.0 -> 26.3
== copy .env.example .env  (then paste key)
key line present: True
== python test.py
10 passed, 0 failed, 0 to look at, 0 skipped
You're set. See you in class.
== log lines before serve.py: 72
== python serve.py (in a second process)
/health -> {"status":"ok"}
== POST /ask
/ask -> HTTP 200
selected: lst_002
== log lines after: 73
== serve.py stdout:
FitFindr is listening on http://localhost:5000
It runs one request at a time — a second one waits for the first.
```
