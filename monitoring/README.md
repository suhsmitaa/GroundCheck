# Monitoring

Every pipeline run appends structured JSON events to `metrics.jsonl` at the
project root (see `src/observability.py`). Each line is one event:
`pipeline_start`, `stage_start`/`stage_end` (with duration), `verification_result`
(groundedness score + which sentences were unsupported), `fallback_triggered`,
and `pipeline_end`.

This is a stand-in for a real telemetry sink. In production you'd point
`log_event()` at OpenTelemetry / Datadog / CloudWatch instead of a local
file, and build dashboards tracking over time:

- **Hallucination rate** — % of responses failing the groundedness threshold
  on first pass
- **Retry rate** — how often the agentic loop needs to self-correct
- **Fallback rate** — how often the system safely refuses instead of guessing
- **Latency per stage** — retrieve / generate / verify, to catch regressions
- **Groundedness score distribution** — drift over time signals model or
  data quality degradation

## Quick local view

```bash
python evaluate.py          # runs the eval set and prints a summary
cat metrics.jsonl | jq .    # inspect raw structured events
```
