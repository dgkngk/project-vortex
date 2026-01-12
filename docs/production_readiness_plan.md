# Production Readiness Plan for Project Vortex

This document outlines the step-by-step plan to transition **Project Vortex** from a development prototype to a robust, production-ready ETL and analysis system.

## Phase 1: Application Entrypoint & CLI
**Goal**: Create a standardized way to invoke ETL jobs and controllers.
- [ ] **Create `main.py`**: Implement a CLI entrypoint (using `argparse` or `click`) in the project root.
    - Commands:
        - `run-etl --assets "BTC,ETH" --mode daily`
        - `run-strategy --strategy "MACD" --assets "BTC"`
- [ ] **Standardize Execution**: Ensure all controllers can be instantiated and run via this CLI without modifying code.

## Phase 2: Configuration & Secrets Management
**Goal**: Secure and flexible configuration for different environments (Dev, Staging, Prod).
- [ ] **Enhance `AppConfig`**:
    - Ensure all secrets (API keys, DB URLs) are strictly read from environment variables in production (disable `.env` file loading in prod or make it optional).
    - Add validation for critical configuration (fail fast if DB URL is missing).
- [ ] **Secret Injection**:
    - Document how secrets should be passed (e.g., Kubernetes Secrets, AWS Secrets Manager mapped to env vars).

## Phase 3: Containerization
**Goal**: Consistent execution environment.
- [ ] **Create `Dockerfile`**:
    - Use a lightweight Python base image (e.g., `python:3.11-slim`).
    - Multi-stage build to keep image size down (separate build-deps from runtime-deps).
    - Install `poetry` and export dependencies to `requirements.txt` or install directly.
    - Set non-root user for security.
- [ ] **Create `docker-compose.yml`**:
    - Define services: `vortex-app`, `redis`, `postgres` (if needed).
    - Useful for local development and integration testing.

## Phase 4: Reliability & Observability
**Goal**: Visibility into system health and issues.
- [ ] **Structured Logging**:
    - Update `VortexLogger` to support JSON output in production (for ELK/Splunk/CloudWatch).
    - Configure log levels via environment variables (`LOG_LEVEL=INFO`).
- [ ] **Error Tracking**:
    - Integrate **Sentry** or similar for global exception catching and alerting.
- [ ] **Health Checks & Metrics**:
    - Add a mechanism to report job success/failure metrics (e.g., to Prometheus/InfluxDB via `pushgateway` or direct write).

## Phase 5: CI/CD Pipeline
**Goal**: Automated testing and delivery.
- [ ] **GitHub Actions Workflow**:
    - **CI**: Run `ruff` (linting), `mypy` (type checking), and `pytest` on every PR.
    - **CD**: Build and push Docker image to a registry (GHCR/ECR/Docker Hub) on merge to `main`.

## Phase 6: Deployment Strategy
**Goal**: Scalable and reliable scheduling.
- [ ] **Deployment Manifests**:
    - Since this is a job-based system, recommended deployment is **Kubernetes CronJobs** or **AWS Lambda/Fargate** triggered by EventBridge.
    - Create sample K8s `CronJob` manifest.

## Action Plan
1.  Implement **Phase 1** (`main.py`) to verify runnability.
2.  Implement **Phase 3** (Docker) to ensure environment isolation.
3.  Implement **Phase 5** (CI) to prevent regressions.
4.  Address **Phase 2 & 4** (Config/Logging) for operational maturity.
