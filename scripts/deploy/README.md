# Deployment Scripts

## Kubernetes VPS Smoke Check

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
