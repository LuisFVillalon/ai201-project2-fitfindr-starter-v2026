# Capstone run log — after, criterion 5 (fresh clones)

Criterion 5: *In 3 of 3 fresh clones (new folder, new terminal, no .venv active), following only RUNNING.md, 0 undocumented steps are needed, and each ends with test.py passing, /health returning ok, one /ask returning 200, and logs/requests.jsonl holding exactly 1 line.*

Run on 2026-11-15, 17:04–17:13 PST, after the improvement (`a66e1f3`: `logs/` added to `.gitignore`, the committed run record moved to `results/run_record_capstone.jsonl`). The procedure is the same as the before run (`results/capstone_before_criterion5_20261115_1638.md`): each trial is a new `pwsh -NoProfile` process with no `.venv` active, cloned from GitHub into its own empty folder, following only RUNNING.md's "From a clean checkout", "The one command that starts it" and "Asking it something". Nothing changed between trials.

| Check | Trial 1 | Trial 2 | Trial 3 |
|---|---|---|---|
| No `.venv` active at start | yes | yes | yes |
| Commit cloned | `a66e1f3` | `a66e1f3` | `a66e1f3` |
| Undocumented steps needed | 0 | 0 | 0 |
| `python test.py` | 10 passed, 0 failed | 10 passed, 0 failed | 10 passed, 0 failed |
| `/health` | `{"status":"ok"}` | `{"status":"ok"}` | `{"status":"ok"}` |
| `/ask` | 200 (13,065 ms) | 200 (12,803 ms) | 200 (14,172 ms) |
| Lines in `logs/requests.jsonl` before `serve.py` | 0 (no file) | 0 (no file) | 0 (no file) |
| Lines in `logs/requests.jsonl` after one `/ask` | **1** | **1** | **1** |
| **Meets criterion 5** | **yes** | **yes** | **yes** |

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 5. Starting FitFindr from RUNNING.md alone | 3 of 3 | 1/1 | 1/1 | 1/1 | MET |

No output in any trial contained an error, warning or traceback. The only extra line was pip's `A new release of pip is available` notice.

## The one line in each clone's `logs/requests.jsonl` (`request_log.py::log_request`, called from `serve.py::ask`)

```json
{"timestamp": "2026-11-16T01:08:03.537+00:00", "event": "ask", "user_id": "clone_t1", "query": "vintage graphic tee under $30", "http_status": 200, "duration_ms": 13065, "parsed": {"description": "vintage graphic tee", "size": null, "max_price": 30.0}, "result_count": 10, "selected_item_id": "lst_002", "stopped_early": false, "error": null, "prompt_tokens": 865, "output_tokens": 258}
{"timestamp": "2026-11-16T01:10:38.777+00:00", "event": "ask", "user_id": "clone_t2", "query": "vintage graphic tee under $30", "http_status": 200, "duration_ms": 12803, "parsed": {"description": "vintage graphic tee", "size": null, "max_price": 30.0}, "result_count": 10, "selected_item_id": "lst_002", "stopped_early": false, "error": null, "prompt_tokens": 834, "output_tokens": 226}
{"timestamp": "2026-11-16T01:13:25.393+00:00", "event": "ask", "user_id": "clone_t3", "query": "vintage graphic tee under $30", "http_status": 200, "duration_ms": 14172, "parsed": {"description": "vintage graphic tee", "size": null, "max_price": 30.0}, "result_count": 10, "selected_item_id": "lst_002", "stopped_early": false, "error": null, "prompt_tokens": 835, "output_tokens": 214}
```
