# Magic8‑Companion

*Lean orchestration layer for 0‑DTE combo selection & exit alerts*

> **Status**: MVP – Paper‑trading ready (v1.0, June 7 2025)

![Python](https://img.shields.io/badge/Python-3.11-blue)
![CI](https://img.shields.io/github/actions/workflow/status/yourorg/magic8-companion/ci.yml?label=CI)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ What is Magic8‑Companion?

Magic8‑Companion wraps the proprietary **Magic8** 5‑minute prediction feed, chooses the *best* 0‑DTE option combo (Iron Condor 🦅, Butterfly 🦋, or Vertical 📈/📉) at four fixed checkpoints each trading day, pushes trade tickets to Interactive Brokers, and yanks positions the second conditions turn hostile.

* **Wrapper‑first** – leaves upstream OSS repos unchanged, adds thin adapters.
* **Core‑only** – does *combo selection* and *exit alerts*; extras ship later.
* **Ship‑fast** – deploys as a single Docker service in ≤ 10 trading days.

---

## 🚀 Features (MVP)

* 5‑min SPX chain ingest via `ib_async`
* Vectorised Δ/Γ with **py‑vollib‑vectorized** (CPU)
* Dealer‑gamma flip & walls from **SPX‑Gamma‑Exposure**
* Strategy matrix → picks Condor / Butterfly / Vertical
* Orders placed with **0dte‑trader** limit‑ladder
* Exit signals when spot drifts >75 % of profit width or Magic8 range moves
* Discord alerts + Prometheus metrics + Streamlit payoff dashboard

---

## 🏗️ Stack

| Layer                | Tech                                                     |
| -------------------- | -------------------------------------------------------- |
| Broker / Data        | **ib\_async**, `ibapi`                                   |
| Greeks               | **py‑vollib‑vectorized** (GPU toggle: *OptionGreeksGPU*) |
| Gamma                | **SPX‑Gamma‑Exposure**                                   |
| Strategy / Execution | **0dte‑trader**                                          |
| Back‑test            | **optopsy**                                              |
| Dashboard            | **opstrat** + Streamlit                                  |
| Persistence          | TimescaleDB 2.x                                          |
| Cache / Bus          | Redis Streams                                            |

Full dependency pins live in [`requirements.txt`](./requirements.txt).

---

## 🖥️ Folder Layout

```
magic8‑companion/
  main.py            # Orchestrator entry
  modules/
    data_collector/  # Option chain loader
    greeks_engine/   # Δ/Γ wrapper
    gex_calculator/  # Gamma exposure
    combo_selector/  # Strategy rules
    order_manager/   # IB execution adapter
  utils/
    redis_client.py
    db_client.py
  scripts/
    init_db.sql      # Timescale schema
  tests/
    ...
  docker-compose.yml
  .env.example
  README.md
```

---

## ⚙️ Prerequisites

* **Interactive Brokers:** TWS or IB Gateway running (`7497`, paper)
* **Magic8 API key / feed socket** reachable inside the container
* Docker ≥ 24, Docker Compose v2
* Python ≥ 3.11 if running outside Docker

---

## 🔧 Configuration

Copy `.env.example` → `.env` and fill:

```env
IB_HOST=host.docker.internal
IB_PORT=7497
MAGIC8_WS=wss://magic8.example.com/feed
REDIS_URL=redis://redis:6379
DATABASE_URL=postgresql://quant:secret@timescaledb/m8db
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
DRY_RUN=true           # flip false to send real orders
USE_GPU=false
TIMEZONE=America/New_York
```

---

## ⏱️ Scheduled Checkpoints

| Local ET | Cron expression |
| -------- | --------------- |
| 10:30    | `30 10 * * 1-5` |
| 11:00    | `0 11 * * 1-5`  |
| 12:30    | `30 12 * * 1-5` |
| 14:45    | `45 14 * * 1-5` |

These fire `orchestrator.run_cycle()` which either **enters** a new combo or **exits** an existing one.

---

## 🏃‍♂️ Quick Start (Docker)

```bash
# clone
$ git clone https://github.com/yourorg/magic8-companion.git
$ cd magic8-companion

# configure
$ cp .env.example .env && nano .env

# spin
$ docker compose up -d

# tail logs
$ docker compose logs -f magic8clone
```

Watch Discord for “ENTRY ➜ Iron Condor 5890/5910/5780/5770 credit 0.43” alerts.

---

## 📊 Monitoring

* Prometheus metrics at `http://localhost:8000/metrics`
* Grafana dashboard auto‑provisioned on `:3000` (default creds *admin/admin*)
* Key KPI: `cycle_total_time_seconds_p95` < 30 s

---

## 🧪 Testing

Run unit & smoke tests:

```bash
$ poetry install && pytest -q
```

CI on GitHub Actions boots docker‑compose with a fake IB Gateway replay file for deterministic integration tests.

---

## 🛣️ Roadmap

* GPU Δ/Γ when latency > 20 s p95
* ML‑based strike ranking (mmfill/iron-condor) A/B
* Multi‑broker adapter (E\*TRADE)
* Micro‑service split on ECS Fargate

---

## 🤝 Contributing

PRs & ISSUES welcome!  Please open a discussion for large changes; remember we maintain a **wrapper‑first** policy—no heavy edits inside upstream libraries.

---

## 📄 License

MIT © 2025 Magic8‑Companion contributors.
