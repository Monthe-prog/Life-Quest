# Deployment Scripts

## Kubernetes VPS Smoke Check

Recommended safe deploy from the VPS repo checkout:

```bash
cd /opt/life-quest
bash scripts/deploy/k8s-vps-deploy.sh
```

Deploy with the optional Oracle microservice overlay:

```bash
APPLY_ORACLE=1 bash scripts/deploy/k8s-vps-deploy.sh
```

Run after applying the VPS-safe Kubernetes overlay:

```bash
cd /opt/life-quest
bash scripts/deploy/k8s-vps-smoke.sh
```

The script verifies the K3s app copy and confirms Docker Compose still responds.

Useful options:

```bash
CHECK_COMPOSE=0 bash scripts/deploy/k8s-vps-smoke.sh
CHECK_ORACLE=1 bash scripts/deploy/k8s-vps-smoke.sh
KUBECTL=kubectl bash scripts/deploy/k8s-vps-smoke.sh
```

If backend fails, it prints backend pod details and logs so the crash reason can be copied directly.

The deploy helper also supports:

```bash
SKIP_BUILD=1 bash scripts/deploy/k8s-vps-deploy.sh
SKIP_IMPORT=1 bash scripts/deploy/k8s-vps-deploy.sh
WAIT_FOR_MIGRATIONS=0 bash scripts/deploy/k8s-vps-deploy.sh
OVERLAY=infra/kubernetes/vps-safe bash scripts/deploy/k8s-vps-deploy.sh
```

By default the deploy helper waits for the `backend-migrate` Job. If migrations fail, it prints the migration Job details and logs before exiting.
