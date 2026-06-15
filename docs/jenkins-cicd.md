# Jenkins CI/CD Pipeline

This project uses `Jenkinsfile` for CI/CD.

## Pipeline Stages

1. Checkout source from GitHub.
2. Install frontend dependencies with `npm ci`.
3. Run checks:
   - Frontend TypeScript check: `npm run typecheck`
   - Backend Python compile check: `python3 -m compileall apps/backend/app`
4. Build Docker images with Docker Compose.
5. Run backend tests with coverage inside the backend Docker image.
6. Deploy `main` to the VPS:
   - Pull latest code into `/opt/life-quest`
   - Rebuild/start containers
   - Run Alembic migrations
   - Import the FastAPI app inside the running backend container
   - Smoke-check backend and frontend HTTP endpoints
   - Print container status

## Jenkins Requirements

Install these on the Jenkins agent:

```bash
sudo apt update
sudo apt install -y curl git nodejs npm python3 docker.io docker-compose-plugin
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

Install Jenkins plugins:

- Git
- Pipeline
- SSH Agent
- GitHub

## Jenkins Credentials

Create an SSH private key credential:

- Kind: `SSH Username with private key`
- ID: `life-quest-vps-ssh`
- Username: `deploy`
- Private key: a key that can SSH into `deploy@158.220.90.106`

The VPS must already have the matching public key in:

```bash
/home/deploy/.ssh/authorized_keys
```

## GitHub Integration

Create a Jenkins Pipeline job or Multibranch Pipeline job pointing to:

```text
https://github.com/Monthe-prog/Life-Quest.git
```

For automatic builds, add a GitHub webhook:

```text
http://YOUR_JENKINS_HOST/github-webhook/
```

Events:

- Push
- Pull request, if using multibranch/PR builds

## VPS Deployment Notes

The deployment command expects the app at:

```bash
/opt/life-quest
```

The server `.env` file is not committed. Keep it on the VPS:

```bash
/opt/life-quest/.env
```

Required production values include:

```bash
OPENAI_API_KEY=your_real_key
OPENAI_MODEL=gpt-5.5
NEXT_PUBLIC_API_BASE_URL=http://158.220.90.106
NEXT_PUBLIC_WS_BASE_URL=ws://158.220.90.106
BACKEND_CORS_ORIGINS=http://158.220.90.106
```

Do not run `docker compose down -v` in Jenkins. It deletes database volumes.

## Kubernetes Smoke Check

Kubernetes is intentionally kept outside the default Jenkins deploy until the VPS-safe K3s path is fully stable.

After manually applying the Kubernetes overlay on the VPS, verify it with:

```bash
cd /opt/life-quest
bash scripts/deploy/k8s-vps-smoke.sh
```

For the optional Oracle microservice overlay:

```bash
CHECK_ORACLE=1 bash scripts/deploy/k8s-vps-smoke.sh
```
