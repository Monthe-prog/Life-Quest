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

The Docker Compose stack includes `prometheus`, `grafana`, `node-exporter`, and `cadvisor`.

Prometheus and Grafana are also routed through Nginx on the main app port:

```text
http://158.220.90.106/prometheus/
http://158.220.90.106/grafana/
```

If Prometheus or Grafana are already installed directly on the VPS, check for port conflicts before starting Compose:

```bash
sudo ss -ltnp | grep -E ':9090|:3001'
docker compose ps
```

Either stop the existing host services or change `PROMETHEUS_PORT` / `GRAFANA_PORT` in `.env`.

If the containers are running but the URLs do not open from your browser, verify each layer from the VPS:

```bash
cd /opt/life-quest
docker compose ps prometheus grafana
docker compose logs --tail=80 prometheus
docker compose logs --tail=80 grafana
curl -I http://127.0.0.1:9090/-/ready
curl -I http://127.0.0.1:3001/login
sudo ufw status numbered
sudo ss -ltnp | grep -E ':9090|:3001'
```

Expected results:

- Prometheus and Grafana containers are `Up`.
- Prometheus returns `HTTP/1.1 200 OK` for `/-/ready`.
- Grafana returns a login redirect or `200` for `/login`.
- Nginx serves `http://158.220.90.106/prometheus/` and `http://158.220.90.106/grafana/` through the already-working app port `80`.
- UFW allows `9090/tcp` and `3001/tcp` only if you also want direct raw-port access.

Open firewall ports only if direct raw-port access is needed:

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
http://158.220.90.106/prometheus/
```

Grafana:

```text
http://158.220.90.106/grafana/
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
http://158.220.90.106/prometheus/targets
```

Prometheus alerts:

```text
http://158.220.90.106/prometheus/alerts
```

Grafana dashboard:

```text
http://158.220.90.106/grafana/d/operator-monitoring-overview/operator-monitoring-overview
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
