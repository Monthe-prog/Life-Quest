# Infrastructure Provisioning With Ansible

This project includes Ansible playbooks for provisioning and deploying part of the OPERATOR infrastructure.

## Files

```text
infra/ansible/ansible.cfg
infra/ansible/inventory.ini
infra/ansible/playbooks/01-provision-vps.yml
infra/ansible/playbooks/02-deploy-operator.yml
infra/ansible/templates/life-quest.nginx.conf.j2
```

## Playbooks

`01-provision-vps.yml`

- Installs required packages.
- Installs Docker Engine and Docker Compose plugin.
- Starts/enables Docker, Nginx, Chrony, and Fail2ban.
- Opens required UFW ports for the app, Jenkins, Prometheus, and Grafana.

`02-deploy-operator.yml`

- Clones/updates the GitHub repository on the VPS.
- Creates the app `.env` only if it is missing, so existing VPS secrets such as `OPENAI_API_KEY` and `JWT_SECRET_KEY` are preserved.
- Builds and starts the Docker Compose stack.
- Runs database migrations.
- Configures Nginx reverse proxy for the app, API, WebSocket, Prometheus, and Grafana paths.
- Prints running container status.

## Install Ansible

Run from your local machine, WSL, or a Linux control host:

```bash
python3 -m pip install --user ansible
```

## Run

From the repo root:

```bash
cd infra/ansible
ansible all -m ping
ansible-playbook playbooks/01-provision-vps.yml
ansible-playbook playbooks/02-deploy-operator.yml
```

If using a specific SSH key:

```bash
ansible-playbook playbooks/01-provision-vps.yml --private-key ~/.ssh/id_rsa
ansible-playbook playbooks/02-deploy-operator.yml --private-key ~/.ssh/id_rsa
```

## Screenshot Checklist

Capture:

1. `ansible all -m ping` success.
2. `01-provision-vps.yml` completing package/service tasks.
3. `02-deploy-operator.yml` completing Docker/Nginx deployment tasks.
4. `docker compose ps` showing app and monitoring containers running.
