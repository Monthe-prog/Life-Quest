# Kubernetes On VPS Without Breaking Docker Compose

This runbook deploys OPERATOR to K3s on the VPS without taking over the working Docker Compose app, Nginx, Prometheus, Grafana, or Jenkins.

The safe approach is:

- Keep Docker Compose as the production demo on port `80`.
- Install K3s without Traefik and ServiceLB so Kubernetes does not hijack port `80`.
- Expose the Kubernetes copy on high ports:
  - Frontend: `http://158.220.90.106:31080`
  - Backend: `http://158.220.90.106:31000`
- Use local Docker-built images imported into K3s containerd, so no local Kubernetes installation is needed on your PC.

## 1. Confirm Docker Compose Is Healthy

Run on the VPS:

```bash
cd /opt/life-quest
docker compose ps
curl http://127.0.0.1:8000/health
curl -I http://127.0.0.1:3000
curl -I http://127.0.0.1:9090/-/ready
curl -I http://127.0.0.1:3001/login
```

Do not continue until the Docker Compose app and monitoring are healthy.

## 2. Remove Or Stop Any Old K3s That Hijacks Port 80

Check for Kubernetes port hijacking:

```bash
sudo iptables -t nat -S | grep -E 'KUBE|CNI|dport 80' || true
```

If old K3s is running and interfering with port `80`, stop it:

```bash
sudo systemctl stop k3s || true
sudo systemctl disable k3s || true
```

If you want a clean reinstall:

```bash
sudo /usr/local/bin/k3s-uninstall.sh
```

Only use the uninstall command if you do not need the old Kubernetes cluster state.

## 3. Install K3s Safely

Install K3s without Traefik and without ServiceLB:

```bash
curl -sfL https://get.k3s.io | sh -s - server --disable traefik --disable servicelb
```

Verify:

```bash
sudo kubectl get nodes
sudo kubectl get pods -A
sudo ss -ltnp | grep ':80'
```

Port `80` should still belong to Nginx, not Kubernetes.

## 4. Build Docker Images On The VPS

Build the same app images Docker Compose uses:

```bash
cd /opt/life-quest
docker compose build backend frontend
```

Export and import the images into K3s:

```bash
docker save -o /tmp/life-quest-backend.tar life-quest-backend:latest
docker save -o /tmp/life-quest-frontend.tar life-quest-frontend:latest

sudo k3s ctr images import /tmp/life-quest-backend.tar
sudo k3s ctr images import /tmp/life-quest-frontend.tar

sudo k3s ctr images ls | grep life-quest
```

## 5. Create Kubernetes Secrets

```bash
cd /opt/life-quest/infra/kubernetes
cp secret.example.yaml secret.yaml
nano secret.yaml
```

Set real values for:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `OPENAI_API_KEY`

Use the same OpenAI key as Docker Compose if you want Oracle AI to work in Kubernetes too.

## 6. Deploy The VPS-Safe Kubernetes Overlay

```bash
sudo kubectl kustomize --load-restrictor=LoadRestrictionsNone /opt/life-quest/infra/kubernetes/vps-safe \
  | sudo kubectl apply -f -
```

Wait:

```bash
sudo kubectl get pods -n operator -w
```

Check services:

```bash
sudo kubectl get svc -n operator
```

You should see:

- `frontend` as `NodePort` on `31080`
- `backend` as `NodePort` on `31000`

If `backend` shows `CrashLoopBackOff`, get the exact startup error before changing manifests:

```bash
sudo kubectl logs -n operator deployment/backend --previous --tail=120
sudo kubectl describe pod -n operator -l app=backend
```

Most backend Kubernetes failures come from a bad `operator-secrets` value, a database password mismatch, or an old image being loaded into K3s. After fixing the cause, restart only the backend:

```bash
sudo kubectl rollout restart deployment/backend -n operator
sudo kubectl rollout status deployment/backend -n operator --timeout=180s
```

## 7. Verify Kubernetes Without Touching Docker Compose

```bash
curl http://127.0.0.1:31000/health
curl -I http://127.0.0.1:31080
```

Browser:

```text
http://158.220.90.106:31080
```

Docker Compose should still work:

```bash
curl -I http://127.0.0.1:3000
curl http://127.0.0.1:8000/health
curl -I http://127.0.0.1:9090/-/ready
curl -I http://127.0.0.1:3001/login
```

## 8. Presentation Commands

Show Docker Compose production:

```bash
cd /opt/life-quest
docker compose ps
```

Show Kubernetes:

```bash
sudo kubectl get nodes
sudo kubectl get pods -n operator
sudo kubectl get svc -n operator
```

Show both are functional:

```bash
curl -I http://127.0.0.1:3000
curl -I http://127.0.0.1:31080
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:31000/health
```

## 9. Stop Kubernetes Without Affecting Docker Compose

Stop the Kubernetes copy:

```bash
sudo kubectl scale deployment/frontend -n operator --replicas=0
sudo kubectl scale deployment/backend -n operator --replicas=0
```

Start it again:

```bash
sudo kubectl scale deployment/backend -n operator --replicas=1
sudo kubectl scale deployment/frontend -n operator --replicas=1
```

Remove the Kubernetes copy:

```bash
sudo kubectl kustomize --load-restrictor=LoadRestrictionsNone /opt/life-quest/infra/kubernetes/vps-safe \
  | sudo kubectl delete -f -
```

This does not remove Docker Compose containers.
