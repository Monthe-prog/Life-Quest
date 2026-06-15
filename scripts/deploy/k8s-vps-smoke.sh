#!/usr/bin/env bash
set -uo pipefail

NAMESPACE="${NAMESPACE:-operator}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:31000/health}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:31080}"
COMPOSE_BACKEND_HEALTH_URL="${COMPOSE_BACKEND_HEALTH_URL:-http://127.0.0.1:8000/health}"
COMPOSE_FRONTEND_URL="${COMPOSE_FRONTEND_URL:-http://127.0.0.1:3000}"
CHECK_COMPOSE="${CHECK_COMPOSE:-1}"
CHECK_ORACLE="${CHECK_ORACLE:-auto}"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-120s}"

failures=0

section() {
  printf '\n== %s ==\n' "$1"
}

run_kubectl() {
  ${KUBECTL:-sudo kubectl} "$@"
}

run_check() {
  local label="$1"
  shift
  printf 'Checking %s... ' "$label"
  if "$@" >/tmp/operator-smoke-check.out 2>&1; then
    printf 'ok\n'
  else
    printf 'failed\n'
    sed 's/^/  /' /tmp/operator-smoke-check.out
    failures=$((failures + 1))
  fi
}

show_check() {
  local label="$1"
  shift
  printf '\n-- %s --\n' "$label"
  if ! "$@"; then
    failures=$((failures + 1))
  fi
}

curl_get() {
  curl -fsS --max-time 10 "$1"
}

curl_head() {
  curl -fsSI --max-time 10 "$1" >/dev/null
}

deployment_exists() {
  run_kubectl get deployment "$1" -n "$NAMESPACE" >/dev/null 2>&1
}

section "Cluster"
show_check "nodes" run_kubectl get nodes
show_check "pods" run_kubectl get pods -n "$NAMESPACE" -o wide
show_check "services" run_kubectl get svc -n "$NAMESPACE"

section "Kubernetes Rollouts"
run_check "backend rollout" run_kubectl rollout status deployment/backend -n "$NAMESPACE" --timeout="$ROLLOUT_TIMEOUT"
run_check "frontend rollout" run_kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout="$ROLLOUT_TIMEOUT"

if [ "$CHECK_ORACLE" = "1" ] || { [ "$CHECK_ORACLE" = "auto" ] && deployment_exists oracle-service; }; then
  run_check "oracle-service rollout" run_kubectl rollout status deployment/oracle-service -n "$NAMESPACE" --timeout="$ROLLOUT_TIMEOUT"
  run_check "backend ORACLE_SERVICE_URL" run_kubectl exec -n "$NAMESPACE" deployment/backend -- printenv ORACLE_SERVICE_URL
  run_check "oracle-service internal health" run_kubectl exec -n "$NAMESPACE" deployment/backend -- python -c "import urllib.request; print(urllib.request.urlopen('http://oracle-service:8010/health', timeout=5).read().decode())"
fi

section "Kubernetes HTTP"
run_check "backend NodePort health" curl_get "$BACKEND_HEALTH_URL"
run_check "frontend NodePort" curl_head "$FRONTEND_URL"

if [ "$CHECK_COMPOSE" = "1" ]; then
  section "Docker Compose Safety Check"
  run_check "docker compose ps" docker compose ps
  run_check "Compose backend health" curl_get "$COMPOSE_BACKEND_HEALTH_URL"
  run_check "Compose frontend" curl_head "$COMPOSE_FRONTEND_URL"
fi

if [ "$failures" -gt 0 ]; then
  section "Backend Diagnostics"
  run_kubectl describe pod -n "$NAMESPACE" -l app=backend || true
  run_kubectl logs -n "$NAMESPACE" deployment/backend --previous --tail=160 || true
  run_kubectl logs -n "$NAMESPACE" deployment/backend --tail=160 || true
  printf '\nSmoke check failed with %s failing check(s).\n' "$failures"
  exit 1
fi

printf '\nSmoke check passed. Kubernetes and Docker Compose checks are healthy.\n'
