# Football Season Simulator & Outcome Analytics

A stochastic tournament forecasting and probabilistic outcome analytics engine simulating European football competitions (UEFA Champions League, Europa League, Conference League) under the 36-team Swiss-system format.

Powered by **bivariate Dixon-Coles Poisson models**, **non-linear Elo-to-xG rating transitions**, and **10,000 Monte Carlo season runs**, served via **FastAPI**, **PostgreSQL**, and distributed **Celery/Redis** workers.

---

## 🚀 Key Features

- **Stochastic Match Engine:**
  - Non-linear `tanh` (Sigmoid) Elo-to-xG mapping accounting for home advantage (+75 Elo) and natural goal caps.
  - Bivariate Dixon-Coles correlation ($\rho = -0.11$) for realistic low-score dependency ($0-0, 1-0, 0-1, 1-1$).
  - Full score probability tensor and 1-X-2 match outcome distributions.
- **Dynamic Elo Ratings:** Tracks intraday/in-simulation Elo updates across parallel universe trajectories.
- **10,000 Monte Carlo Season Simulations:**
  - Simulates 900,000+ matches across parallel seasons while freezing played fixtures and scores.
  - Computes official UEFA Swiss-system tie-breaker rules (Points, Goal Difference, Goals For, etc.).
- **Analytical & Threshold Intelligence:**
  - Direct qualification (Top 8) and Play-off (Top 24) point threshold distributions at 90% and 99% confidence intervals.
  - Full finish rank probability distributions ($P(\text{rank} = k)$) and expected/median percentile intervals ($P_{25} - P_{75}$).
  - "Points-to-Rank" outcome probability matrix.
- **Distributed Microservice Stack:**
  - **FastAPI** REST API exposing tournament standings, simulation tasks, and odds analysis.
  - **PostgreSQL** relational database for competitions, teams, matches, and Monte Carlo threshold snapshots.
  - **Celery & Redis** task queue for asynchronous distributed simulation execution without blocking API threads.
  - **Docker Compose** containerization for seamless deployment.

---

## 🛠️ Tech Stack

- **Core & Data Science:** Python 3.11, NumPy, Pandas, SciPy, Math
- **API & Backend:** FastAPI, Uvicorn, Pydantic, SQLAlchemy, PostgreSQL, Psycopg2
- **Distributed Computing:** Celery, Redis
- **DevOps & Infrastructure:** Docker, Docker Compose, Windows Task Scheduler / Shell automation

---

## 📦 Project Structure

```text
├── data/
│   ├── leagues/         # Official tournament fixtures & results (CL, UEL, ECL)
│   ├── processed/       # Historical and latest Elo ratings & aliases
│   └── analysis/        # Pre-calculated 10,000-simulation statistical JSON outputs
├── scripts/             # CLI runners, exploration tools, test suites, and weekly pipelines
├── src/
│   ├── analyzer/        # Matrix statistical analysis (SimulationAnalyzer)
│   ├── api/             # FastAPI routers, endpoints, and Pydantic schemas
│   ├── core/            # Domain entities, tie-break algorithms, and storage handlers
│   ├── database/        # SQLAlchemy database engine and ORM models
│   ├── data_loader/     # API fetchers for fixtures and club Elo ratings
│   ├── models/          # MatchEngine (Dixon-Coles + Poisson) and EloUpdater
│   ├── simulator/       # Monte Carlo parallel season runner & Dynamic Elo tracker
│   └── worker/          # Celery worker application & asynchronous tasks
├── docker-compose.yml   # Multi-container orchestration (DB, Redis, API, Worker)
├── Dockerfile           # Backend application container definition
└── requirements.txt     # Python dependencies
```

---

## ⚡ Quickstart

### 1. Installation

Clone repository and set up a virtual environment:
```bash
git clone https://github.com/kagansoysal/football-simulator.git
cd football-simulator
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Run with Docker Compose (Recommended)
Start the complete infrastructure (PostgreSQL, Redis, FastAPI, Celery Worker):
```bash
docker compose up -d
```
- API Docs (Swagger UI): `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 📊 CLI & Analysis Usage

### Run 10,000 Monte Carlo Simulations
```bash
# Champions League (CL), Europa League (UEL), or Conference League (ECL)
python scripts/run_weekly_pipeline.py --competition CL
```

### Inspect Threshold & Probability Analytics
```bash
# View Top 8 / Top 24 qualification thresholds
python scripts/show_simulation_analysis.py -c CL --thresholds

# View Team-specific rank distribution (e.g. Galatasaray)
python scripts/show_simulation_analysis.py -c CL -t Galatasaray

# View Points-to-Rank probability matrix
python scripts/show_simulation_analysis.py -c CL --points-matrix
```

---

## 🗺️ Roadmap & In-Progress

- [x] Dixon-Coles Poisson Match Prediction Engine
- [x] Dynamic Elo rating transition tracker
- [x] 10,000 Monte Carlo simulation engine with Swiss-system tie-breaks
- [x] FastAPI, PostgreSQL, and Celery/Redis architecture
- [ ] **What-If Decisioning Engine:** Sensitivity analysis for counterfactual scenarios.
- [ ] **Event-Driven Architecture:** In-play match streaming with Apache Kafka for real-time odds updating.
- [ ] **Observability:** Custom Prometheus metrics (`simulation_duration_seconds`) and Grafana monitoring dashboard.
