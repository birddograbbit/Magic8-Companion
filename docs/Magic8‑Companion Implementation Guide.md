# Magic8‑Companion — Quick‑Ship Implementation Guide

*Version 1.0 – June 7 2025*

---

## 0  Purpose & Scope

This guide shows **exactly** how to stand up the first‑pass **Magic8‑Companion**: an orchestration layer that consumes the proprietary 5‑minute Magic8 feed, computes 0‑DTE option‑combo favourability at four scheduled checkpoints (10 :30, 11 :00, 12 :30, 14 :45 ET) and pushes *entry* or *exit* signals to your broker & Discord.  The design obeys three principles:

1. **Wrapper‑first** — We glue around proven open‑source repos; we never fork/core‑hack them unless unavoidable.
2. **Core‑only** — We implement just two flows: **combo‑type selection** and **exit‑signal generation**.
3. **Ship‑fast** — MVP is a mono‑service Docker target deliverable in ≤ 10 trading days; micro‑services are toggled later.

---

## 1  High‑Level Architecture

```mermaid
flowchart TD
  A[IB Gateway / Magic8 Feed] -->|option chain & predictions| B[Mono Service ‑ magic8_companion]
  B --> C[(Redis Streams)]
  B --> D[(TimescaleDB)]
  B --> E[Discord Alerts]
  B --> F[IB Order Manager]
```

**Why mono‑service?** Less network hop, faster delivery; we promote to the micro‑service topology already drafted in *dev‑plan v2.1* once p95 latency > 20 s or throughput > 10 ticks/s. fileciteturn2file0

---

## 2  Component Stack (no forks, only wrappers)

| Layer               | OSS repo (unmodified)            | Wrapper module (new)         | Notes                                        |
| ------------------- | -------------------------------- | ---------------------------- | -------------------------------------------- |
| Broker & data       | **ib\_async**                    | `connectors/ib_connector.py` | Async context manager + reconnect            |
| Greeks calculations | **py\_vollib\_vectorized** (CPU) | `services/greeks_engine`     | Vectorised Δ/Γ; GPU toggle later             |
| Gamma exposure      | **SPX‑Gamma‑Exposure**           | `services/gex_calculator`    | Real‑time GEX flip & walls                   |
| Strategy builder    | **0dte‑trader**                  | `services/combo_selector`    | We only call its contract helpers            |
| Order execution     | — (via ib\_async)                | `services/order_manager`     | Encapsulates limit‑ladder & circuit breakers |
| Persistence         | TimescaleDB                      | `utils/db_client.py`         | Async inserts & queries                      |
| Cache / bus         | Redis Streams                    | `utils/redis_client.py`      | Option‑chain & metrics topics                |
| Dashboards          | Streamlit + **opstrat**          | `services/dashboard`         | Pay‑off & live stats                         |

---

## 3  Algorithm Rules (frozen v2.1)

```yaml
quality_filters:
  max_spread: 5.0           # $
  min_open_interest: 100
  min_volume: 1
strategy_matrix:
  iron_condor:
    range_pct_lt: 0.006     # 0.6 %
    short_delta: 0.10
    long_delta: 0.05
  butterfly:
    gex_distance_pct_lt: 0.01
    max_debit_pct: 0.002
  vertical:
    gex_distance_pct_gt: 0.004
order_rules:
  initial_edge_ticks: 2      # mid ±2
  widen_every_s: 30          # seconds
  max_attempts: 5
```

These exact constants come from the peer‑reviewed matrix in *magic8‑dev‑plan 2.1* fileciteturn2file0 and **must not be edited** until after post‑launch re‑calibration.

---

## 4  Exit‑Signal Logic

An exit alert fires when **any** of the following triggers is true for an open combo:

1. |Spot − Combo center| / Width ≥ 0.75
2. Magic8’s new 5‑min prediction range no longer intersects current profit zone.
3. *gamma\_exposure.total\_gamma* crosses zero away from the combo center.
4. Daily loss > \$5 000 or position count > 10 (Circuit breakers) fileciteturn2file1.

Alerts publish to Redis `exit_signals` stream and Discord; the Order Manager consumes and closes any live positions.

---

## 5  Scheduling

In `main.py` we register four cron‑style async tasks:

```python
CHECKPOINTS = ["10:30", "11:00", "12:30", "14:45"]  # America/New_York
```

Each task calls `orchestrator.run_cycle()` which:

1. Pulls latest option chain (ib\_async) → filters by *quality\_filters*.
2. Recomputes Greeks & GEX snapshot.
3. Scores each strategy via *strategy\_matrix*.
4. Publishes top recommendation (score ≥ 70) to Discord.
   If a position is already open, step 3 is skipped and *exit‑signal logic* runs instead.

---

## 6  Project Layout

The mono‑service repo skeleton is pre‑generated (cookiecutter) and listed in dev‑plan v2.1 §1.1 fileciteturn2file9.  Key paths:

```
magic8clone/
  main.py              # orchestrator entry‑point
  modules/
    data_collector/    # IB chain loader
    greeks_engine/     # tiny wrapper around py_vollib_vectorized
    gex_calculator/    # adapts SPX‑Gamma‑Exposure
    combo_selector/    # strategy scoring
    order_manager/     # execution & risk
  utils/
    redis_client.py
    db_client.py       # Timescale async pool
    monitoring.py      # Prometheus export
scripts/
  init_db.sql          # executed at container boot
```

---

## 7  Infrastructure as Code

### 7.1 Docker‑Compose (trimmed)

```yaml
services:
  redis:
    image: redis:7-alpine
  timescaledb:
    image: timescale/timescaledb:latest-pg15
  magic8clone:
    build: .
    environment:
      IB_HOST: host.docker.internal
      IB_PORT: 7497
      REDIS_URL: redis://redis:6379
      DATABASE_URL: postgresql://quant:${DB_PASSWORD}@timescaledb/magic8clone
      DRY_RUN: "true"
    depends_on:
      - redis
      - timescaledb
```

Full file with health‑checks and monitoring targets lives in the scaffold (see dev‑plan v2.1 §1.2). fileciteturn2file8

### 7.2 Database Schema

The `init_db.sql` script creates hypertables **option\_chain** and **gamma\_exposure** as per plan v2.1 §1.4 fileciteturn2file0.

```sql
CREATE TABLE option_chain (
  time TIMESTAMPTZ NOT NULL,
  symbol VARCHAR(10) NOT NULL,
  strike NUMERIC(10,2) NOT NULL,
  expiry DATE NOT NULL,
  option_type CHAR(1) NOT NULL,
  bid NUMERIC(10,2),
  ask NUMERIC(10,2),
  open_interest INTEGER,
  implied_vol NUMERIC(6,4),
  delta NUMERIC(6,4),
  gamma NUMERIC(8,6),
  spot_price NUMERIC(10,2)
);
SELECT create_hypertable('option_chain', 'time', chunk_time_interval => INTERVAL '1 hour');
```

---

## 8  Risk & Monitoring

* Circuit breakers: max\_daily\_loss, position\_size, concurrent\_orders, min\_account\_balance fileciteturn2file1
* Prometheus metrics exported at `:8000/metrics`; scrape config ready in `infra/prometheus.yml`. fileciteturn2file11
* Grafana dashboards auto‑provisioned; key KPI = `cycle_total_time_seconds` p95 < 30 s.

---

## 9  CI / Testing Strategy

* **Unit tests** on selector edge‑cases (pytest, fixtures inside `tests/`).
* **Integration smoke**: docker‑compose service with fake IB Gateway replays canned chain, executed in GitHub Actions.
* **Shadow‑live comparator** (Phase 2) logs credit/price divergence vs true Magic8 feed. fileciteturn2file10

---

## 10  Step‑by‑Step Timeline (T‑0 = first coding day)

| Day | Deliverable                                    | Owner    |
| --- | ---------------------------------------------- | -------- |
| 0   | Docker infra (redis, timescaledb, magic8clone) | DevOps   |
| 1‑2 | IBConnector + schema ingest                    | Quant    |
| 3‑4 | Greeks & GEX wrappers                          | Quant    |
| 5‑6 | Combo Selector logic & tests                   | Algo Eng |
| 7   | Order Manager (dry‑run only)                   | Algo Eng |
| 8   | End‑to‑end smoke + latency hist                | All      |
| 9   | Start continuous paper loop                    | —        |
| 10+ | Split to micro‑services *iff* p95 > 20 s       | DevOps   |

Timeline mirrors dev‑plan v1 but trims non‑MVP deliverables. fileciteturn2file10

---

## 11  Deployment Cheatsheet

```bash
# Local dev
$ docker compose up -d redis timescaledb
$ poetry install && poetry run python -m magic8clone.main

# Paper trading (mono‑service)
$ DRY_RUN=false docker compose up -d magic8clone

# View metrics
$ open http://localhost:3000  # Grafana
$ open http://localhost:9090  # Prometheus
```

---

## 12  Future Enhancements (not in MVP)

* **GPU Greeks** via OptionGreeksGPU once latency trig fires.
* **ML strike picker** (mmfill/iron‑condor) as A/B experiment.
* **Multi‑broker** abstraction with pyetrade.
* **Full micro‑service split** & autoscaling on ECS Fargate.

---

### Appendix A  Environment Variable Reference

| Variable       | Purpose                   | Example                                          |
| -------------- | ------------------------- | ------------------------------------------------ |
| `IB_HOST`      | TWS / IB Gateway hostname | `host.docker.internal`                           |
| `IB_PORT`      | Port (paper = 7497)       | `7497`                                           |
| `REDIS_URL`    | Redis connection URI      | `redis://redis:6379`                             |
| `DATABASE_URL` | Timescale connection      | `postgresql://quant:pwd@timescaledb/magic8clone` |
| `DRY_RUN`      | Skip real orders          | `true`                                           |
| `USE_GPU`      | Enable GPU Greeks         | `false`                                          |

---

**You now have a single markdown guide with every mandatory detail to get Magic8‑Companion from zero to live‑paper trading while changing *zero* lines inside the audited open‑source projects.**
