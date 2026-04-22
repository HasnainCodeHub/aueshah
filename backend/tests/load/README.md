# Load testing

## Prereqs
```bash
pip install locust
```
(Not added to pyproject — it's a dev-only tool, keep production deps lean.)

## Quick run (headless, 2-min smoke)
```bash
locust -f tests/load/locustfile.py \
  --host https://<your-koyeb-url> \
  --users 20 --spawn-rate 2 --run-time 2m --headless \
  --csv=load_report
```

## Interactive (browser UI at :8089)
```bash
locust -f tests/load/locustfile.py --host https://<your-koyeb-url>
```

## Pass criteria
| Metric | Target | Source |
|---|---|---|
| p95 latency | ≤ 3000 ms | spec NFR, SC-001 |
| Failure rate | < 1% | SC-008 |
| 429 Rate Limited | Expected under sustained load | by design |

## Traffic shape
The load file uses a weighted mix that matches expected production traffic:
- 40% product browsing
- 25% general (warranty, policies)
- 15% Noor inquiries
- 10% compare
- 10% bespoke

Each user keeps a stable `session_id` across their turns so the backend exercises
the full persistence + personalization path.
