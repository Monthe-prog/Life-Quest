# Continuous Monitoring With Prometheus And Grafana

This project monitors both the application and the VPS/container platform.

## What Is Monitored

Application metrics:

- FastAPI exposes `/metrics`.
- Prometheus scrapes backend request counts, status codes, and latency.

Platform metrics:

- `node-exporter` exposes VPS CPU, memory, disk, and host metrics.
- `cadvisor` exposes Docker/container CPU, memory, and runtime metrics.
- Prometheus also scrapes itself.

Visualization and alerts:

- Grafana is provisioned with Prometheus as the default data source.
- Grafana loads the `OPERATOR Monitoring Overview` dashboard automatically.
- Prometheus loads alert rules for backend downtime, backend 5xx errors, high CPU, and low disk space.

## Run Monitoring

From the VPS:

```bash
cd /opt/life-quest
git pull origin main
docker compose up -d --build
```

Open firewall ports if needed:

```bash
ufw allow 9090/tcp
ufw allow 3001/tcp
ufw status
```

## URLs

Application:

```text
http://158.220.90.106
```

Prometheus:

```text
http://158.220.90.106:9090
```

Grafana:

```text
http://158.220.90.106:3001
```

Default Grafana login comes from `.env`:

```bash
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=operator_grafana_password
```

Change the password on the VPS before production use.

## Verify Metrics

Backend metrics:

```bash
curl http://127.0.0.1:8000/metrics | head
```

Prometheus targets:

```text
http://158.220.90.106:9090/targets
```

Prometheus alerts:

```text
http://158.220.90.106:9090/alerts
```

Grafana dashboard:

```text
http://158.220.90.106:3001/d/operator-monitoring-overview/operator-monitoring-overview
```

## Screenshot Checklist

Capture these screens for the monitoring requirement:

1. Docker containers running:

```bash
docker compose ps
```

2. Backend `/metrics` endpoint showing `operator_http_requests_total`.
3. Prometheus `Targets` page showing `operator-backend`, `node-exporter`, and `cadvisor` as `UP`.
4. Prometheus `Alerts` page showing configured alert rules.
5. Grafana `OPERATOR Monitoring Overview` dashboard.

## Jenkins

The existing Jenkins pipeline builds the app with Docker Compose. After this monitoring change is pushed, run:

```text
life-quest -> Build Now
```

Then pull/redeploy on the VPS if the deployment stage is still disabled:

```bash
cd /opt/life-quest
git pull origin main
docker compose up -d --build
docker compose exec backend alembic upgrade head
```
