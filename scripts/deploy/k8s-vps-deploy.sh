#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

NAMESPACE="${NAMESPACE:-operator}"
APPLY_ORACLE="${APPLY_ORACLE:-0}"
SKIP_BUILD="${SKIP_BUILD:-0}"
SKIP_IMPORT="${SKIP_IMPORT:-0}"
WAIT_FOR_MIGRATIONS="${WAIT_FOR_MIGRATIONS:-1}"
MIGRATION_TIMEOUT="${MIGRATION_TIMEOUT:-180s}"
BACKEND_IMAGE="${BACKEND_IMAGE:-life-quest-backend:latest}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-life-quest-frontend:latest}"
BACKEND_TAR="${BACKEND_TAR:-/tmp/life-quest-backend.tar}"
FRONTEND_TAR="${FRONTEND_TAR:-/tmp/life-quest-frontend.tar}"

if [ "$APPLY_ORACLE" = "1" ]; then
  OVERLAY="${OVERLAY:-infra/kubernetes/vps-safe-oracle-service}"
  export CHECK_ORACLE="${CHECK_ORACLE:-1}"
else
  OVERLAY="${OVERLAY:-infra/kubernetes/vps-safe}"
  export CHECK_ORACLE="${CHECK_ORACLE:-0}"
fi

run_compose() {
  ${COMPOSE:-docker compose} "$@"
}

run_kubectl() {
  ${KUBECTL:-sudo kubectl} "$@"
}

run_ctr() {
  ${K3S_CTR:-sudo k3s ctr} "$@"
}

compose_image_id() {
  local service="$1"
  run_compose images -q "$service" | tail -n 1
}

tag_compose_image() {
  local service="$1"
  local target="$2"
  local image_id

  image_id="$(compose_image_id "$service")"
  if [ -z "$image_id" ]; then
    printf 'Unable to find built image for Compose service "%s".\n' "$service" >&2
    exit 1
  fi

  docker image tag "$image_id" "$target"
}

if [ ! -f infra/kubernetes/secret.yaml ]; then
  cat >&2 <<'EOF'
Missing infra/kubernetes/secret.yaml.

Create it from the example before deploying Kubernetes:

  cp infra/kubernetes/secret.example.yaml infra/kubernetes/secret.yaml
  nano infra/kubernetes/secret.yaml
EOF
  exit 1
fi

if [ "$SKIP_BUILD" != "1" ]; then
  run_compose build backend frontend
fi

tag_compose_image backend "$BACKEND_IMAGE"
tag_compose_image frontend "$FRONTEND_IMAGE"

if [ "$SKIP_IMPORT" != "1" ]; then
  docker save -o "$BACKEND_TAR" "$BACKEND_IMAGE"
  docker save -o "$FRONTEND_TAR" "$FRONTEND_IMAGE"

  run_ctr images import "$BACKEND_TAR"
  run_ctr images import "$FRONTEND_TAR"
fi

run_kubectl apply -f infra/kubernetes/base/namespace.yaml
run_kubectl apply -f infra/kubernetes/secret.yaml
run_kubectl delete job backend-migrate -n "$NAMESPACE" --ignore-not-found
run_kubectl apply -k "$OVERLAY"

if [ "$WAIT_FOR_MIGRATIONS" = "1" ]; then
  if ! run_kubectl wait --for=condition=complete job/backend-migrate -n "$NAMESPACE" --timeout="$MIGRATION_TIMEOUT"; then
    run_kubectl describe job backend-migrate -n "$NAMESPACE" || true
    run_kubectl logs job/backend-migrate -n "$NAMESPACE" --tail=160 || true
    exit 1
  fi
fi

run_kubectl rollout restart deployment/backend -n "$NAMESPACE"
run_kubectl rollout restart deployment/frontend -n "$NAMESPACE"
if [ "$APPLY_ORACLE" = "1" ]; then
  run_kubectl rollout restart deployment/oracle-service -n "$NAMESPACE"
fi

bash scripts/deploy/k8s-vps-smoke.sh
