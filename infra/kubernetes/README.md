# OPERATOR Kubernetes Deployment

These manifests target a single-node K3s VPS with Traefik enabled.

## 1. Build and Push Images

Run from the repository root on your local machine. Replace the registry names if you use Docker Hub instead of GitHub Container Registry.

```bash
docker build -f infra/docker/backend.Dockerfile -t ghcr.io/monthe-prog/life-quest-backend:latest .
docker build -f infra/docker/frontend.Dockerfile \
  --build-arg NEXT_PUBLIC_API_BASE_URL=http://158.220.90.106 \
  --build-arg NEXT_PUBLIC_WS_BASE_URL=ws://158.220.90.106 \
  -t ghcr.io/monthe-prog/life-quest-frontend:latest .

docker push ghcr.io/monthe-prog/life-quest-backend:latest
docker push ghcr.io/monthe-prog/life-quest-frontend:latest
```

If the images are private, create an image pull secret on the VPS and add it to the backend/frontend pod specs.

## 2. Create the Secret File

On the VPS, copy this folder into the repo checkout, then create a real secret file:

```bash
cd /opt/life-quest/operator/infra/kubernetes
cp secret.example.yaml secret.yaml
nano secret.yaml
```

Change at least:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`, using the same Postgres password
- `JWT_SECRET_KEY`
- `OPENAI_API_KEY` if Oracle should call OpenAI

## 3. Deploy

```bash
sudo kubectl apply -k /opt/life-quest/operator/infra/kubernetes
```

Wait for workloads:

```bash
sudo kubectl get pods -n operator -w
```

Check services and ingress:

```bash
sudo kubectl get svc -n operator
sudo kubectl get ingress -n operator
```

## 4. Verify

```bash
curl http://158.220.90.106/health
curl http://158.220.90.106/api/openapi.json
```

Open:

```text
http://158.220.90.106
http://158.220.90.106/api/docs
```

## 5. Run Migrations Again

The `backend-migrate` Job runs on deploy. To rerun it after a new release:

```bash
sudo kubectl delete job backend-migrate -n operator
sudo kubectl apply -f /opt/life-quest/operator/infra/kubernetes/backend.yaml
```

## 6. Update After a New Image

```bash
sudo kubectl rollout restart deployment/backend -n operator
sudo kubectl rollout restart deployment/frontend -n operator
sudo kubectl rollout status deployment/backend -n operator
sudo kubectl rollout status deployment/frontend -n operator
```

## 7. Troubleshooting

```bash
sudo kubectl describe pod -n operator -l app=backend
sudo kubectl logs -n operator deployment/backend
sudo kubectl logs -n operator deployment/frontend
sudo kubectl get events -n operator --sort-by=.lastTimestamp
```

## 8. Remove OPERATOR From Kubernetes

```bash
sudo kubectl delete -k /opt/life-quest/operator/infra/kubernetes
```
