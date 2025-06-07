# Magic8Clone Development Plan – v 2.1 (7 Jun 2025)

*Merged lessons from v 1.2 and v 2.0; keeps the **speed‑to‑MVP** focus of v 1.2 while adopting the **robust micro‑service & monitoring** detail of v 2.0.*

---

## 0  Executive Snapshot

| Goal                   | Metric                                        |
| ---------------------- | --------------------------------------------- |
| **Paper‑trading live** | ≤ 14 trading days                             |
| **Latency**            | < 30 s snapshot→order (95‑th)                 |
| **Stability**          | 5 consecutive sessions w/ no crashes          |
| **PnL (4‑week)**       | ≥ 0 after fees                                |
| **Code simplicity**    | Phase‑0 single binary; Phase‑1 micro‑services |

Key refinements vs earlier drafts:

1. **Dual‑phase delivery** – start **Mono‑Service** for speed; auto‑evolve to **Micro‑Service** once perf triggers fire.
2. **Redis Streams** (replayable) instead of simple pub/sub.
3. **TimescaleDB** hypertables for cheap time‑series queries.
4. **Shadow‑Live Comparator** micro‑service for continuous benchmarking vs proprietary Magic8 feed.
5. **Circuit‑breakers & GPU cost gate** baked into config.
6. **Terraform / ECS sample** pushed to `/infra/` for one‑button prod deploy.

---

## 1  Architecture Overview

```mermaid
graph TD
  subgraph Phase‑0  (MVP ≤ Day 10)
    A[main.py Orchestrator] --> B[IB Data Collector]
    B --> C[Greeks + GEX Engine]
    C --> D[Combo Selector]
    D --> E[Execution Manager]
    D --> F[Stdout + JSON Log]
  end

  subgraph Phase‑1  (split when p95 > 20 s or TPS > 10)
    B -.->|Redis Stream| C
    C -.->|Redis Stream| D
    D -.->|REST| E
    B & C & D & E --> G[(TimescaleDB)]
    D --> H[Shadow Comparator]
    D --> I[Slack / Dashboard]
  end
```

\| Message bus | **Redis Streams** (`option_chain`, `greeks`, `recommendations`) – replayable, guaranteed ordering |
\| Persistence | **TimescaleDB** (1‑minute hypertables) + S3 backup |
\| Config | `pydantic‑settings` env‑override, hot‑reload via `SIGUSR2` |
\| Infra | Docker‑Compose  →  ECS Fargate (Terraform sample) |

---

## 2  Component Matrix

| Layer                | OSS Base                                            | Wrapper Module               | Notes                                       |
| -------------------- | --------------------------------------------------- | ---------------------------- | ------------------------------------------- |
| Broker + Market Data | `ib_async`                                          | `connectors/ib_connector.py` | Async ctx‑mgr, reconnect, heartbeat         |
| Greeks calc          | `py_vollib_vectorized` → optional `OptionGreeksGPU` | `services/greeks_engine`     | GPU auto‑switch when spot <\$0.50/hr        |
| Gamma Exposure       | `SPX‑Gamma‑Exposure`                                | `services/gex_calculator`    | Intraday loader patched to use IB chain     |
| Strategy logic       | fork `0dte‑trader`                                  | `services/combo_selector`    | 10‑15Δ IC, ±0.2 % B‑fly, ±0.4 % Vert.       |
| Execution            | `ib_async.bracketOrder`                             | `services/order_manager`     | Limit→market widen algorithm (2 ticks/30 s) |
| Monitoring           | Prometheus export in each svc                       | —                            | Histograms on latency, queue lag            |

---

## 3  Algorithm Rules (unchanged, explicit)

```yaml
quality_filters:
  max_spread: 5.0
  min_open_interest: 100
  min_volume: 1
strategy_matrix:
  iron_condor:
    range_pct_lt: 0.006
    short_delta: 0.10
    long_delta: 0.05
  butterfly:
    gex_distance_pct_lt: 0.01
    max_debit_pct: 0.002
  vertical:
    gex_distance_pct_gt: 0.004
order_rules:
  initial_edge_ticks: 2
  widen_every_s: 30
  max_attempts: 5
```

---

## 4  Performance & Risk Guardrails

| Guard              | Value   | Action                                            |
| ------------------ | ------- | ------------------------------------------------- |
| **Cycle time p95** | 30 s    | Page Ops + auto kill oldest cycle                 |
| **CPU container**  | 25 %    | Prometheus alert → scale‑out hint                 |
| **RAM container**  | 500 MB  | OOM kill restart                                  |
| **Daily drawdown** |  ‑\$5 k | All services signal `circuit_open`; no new orders |

---

## 5  Sprint Plan (trading days)

| Day   | Deliverable                                                         | Owner    |
| ----- | ------------------------------------------------------------------- | -------- |
| 1     | Dev‑container + docker‑compose infra (Redis, Timescale, Prometheus) | DevOps   |
| 2–3   | **IBConnector** finished; schema → Timescale                        | Quant    |
| 4–5   | **Greeks + GEX services**; cache to Redis; bench CPU vs GPU         | Quant    |
| 6–7   | **Combo Selector** rules; local unit tests                          | Algo Eng |
| 8     | **Execution Manager** (dry‑run)                                     | Algo Eng |
| 9     | **End‑to‑end smoke**; JSON logs; latency histogram                  | All      |
| 10    | Start continuous paper loop (Mono‑Svc)                              | —        |
| 11–12 | Split into micro‑services if p95 > 20 s                             | DevOps   |
| 13–14 | Shadow‑live comparator; Slack alerts; go/no‑go                      | All      |

---

## 6  Testing Strategy

* **Unit** – pytest on selector edge‑cases (wide spreads, missing Greeks).
* **Integration** – docker‑compose test harness spins fake IB GW & streams canned chain.
* **Shadow‑Live** – comparator logs divergence > 10 pts or 0.1 credit.
* **Load** – Locust script pushes 10 k ticks/s to Redis to measure lag.

---

## 7  Deployment Cheatsheet

```bash
# Local MVP
$ docker compose up -d redis postgres prometheus grafana
$ poetry run python magic8clone/main.py

# Promote to micro‑svc
$ docker compose up -d --scale greeks_engine=2 --scale combo_selector=2

# Prod via Terraform → ECS
$ cd infra && terraform apply
```

---

## 8  Next‑Step Checklist

* [ ] Fill in stub for `ShadowComparator` once proprietary Magic8 feed endpoint confirmed.
* [ ] Finalise Prometheus alert rules (`latency_p95 > 25s for 3 m`).
* [ ] Decide on GPU instance type (AWS g5.xlarge vs local RTX 3090).

---
