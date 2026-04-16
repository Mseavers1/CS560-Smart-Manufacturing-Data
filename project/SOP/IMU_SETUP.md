# IMU Setup Guide

This guide covers the Raspberry Pi host setup for the redesigned IMU deployment and the Swarm steps needed to add each IMU node to the cluster.

The new architecture has two parts:

1. A Pi-local hardware service started with `python -m imu_host`
2. A containerized edge service that talks to the host service over `/run/imu-hw/imu.sock`

The host service must be working before the Docker container can use the IMU.

## Active IMU Nodes

Use the following service and node mapping when bringing nodes online:

| IMU | Host IP | Swarm Service | Session ID | CSV Output |
| --- | --- | --- | --- | --- |
| IMU 83 | `192.168.1.83` | `imu_83_joint1` | `imu-node-83` | `/app/data/imu-83-joint1.csv` |
| IMU 84 | `192.168.1.84` | `imu_84_joint1` | `imu-node-84` | `/app/data/imu-84-joint1.csv` |
| IMU 85 | `192.168.1.85` | `imu_85_joint1` | `imu-node-85` | `/app/data/imu-85-joint1.csv` |
| IMU 86 | `192.168.1.86` | `imu_86_joint1` | `imu-node-86` | `/app/data/imu-86-joint1.csv` |

The working reference node today is IMU 83 at `192.168.1.83`. IMUs `192.168.1.84`, `192.168.1.85`, and `192.168.1.86` should be configured the same way.

## 1. Prepare The Pi

Clone or copy this repo onto the Raspberry Pi and move into the project directory:

```bash
cd /home/admin/imu_node_smr
```

Create and activate a virtual environment if needed:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

If Docker is not installed on the Pi yet, install it before continuing:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker admin
newgrp docker
docker version
```

If the node is not already in the Swarm, join it from the Pi with the worker token from the manager:

```bash
docker swarm join --token <worker-token> 192.168.1.76:2377
```

From the manager, confirm the node appears:

```bash
docker node ls
```

Then label the node from the manager so Swarm can pin the correct IMU service to the correct host:

```bash
docker node update --label-add device_id=192.168.1.83 <node-name-for-83>
docker node update --label-add device_id=192.168.1.84 <node-name-for-84>
docker node update --label-add device_id=192.168.1.85 <node-name-for-85>
docker node update --label-add device_id=192.168.1.86 <node-name-for-86>
```

Check the labels after updating:

```bash
docker node inspect <node-name> --format '{{ .Spec.Labels }}'
```

## 2. Install Host Dependencies

Install the Pi-side Python requirements:

```bash
python3 -m pip install -r requirements-host.txt
```

The host requirements include:

- `Adafruit-Blinka`
- `adafruit-circuitpython-bno08x`
- `numpy`
- `lgpio`

If `board` import errors mention `lgpio`, reinstall the host requirements:

```bash
python3 -m pip install -r requirements-host.txt
```

## 3. Start The Hardware Service Manually

The host service creates and listens on the Unix socket at `/run/imu-hw/imu.sock`.

For a first manual test:

```bash
sudo mkdir -p /run/imu-hw
sudo chown admin:admin /run/imu-hw
IMU_SOCKET_PATH=/run/imu-hw/imu.sock python3 -m imu_host
```

Expected startup output includes:

```text
IMU connection successfully initialized
```

Leave this process running while testing.

## 4. Verify The Host Service

In a second terminal on the Pi, confirm the socket exists:

```bash
ls -l /run/imu-hw/imu.sock
```

Check readiness:

```bash
curl --unix-socket /run/imu-hw/imu.sock http://localhost/v1/readyz
```

Check current status:

```bash
curl --unix-socket /run/imu-hw/imu.sock http://localhost/v1/status
```

When the service is healthy, `readyz` should report `"ready": true`.

## 5. Install The Host Service With systemd

After manual testing succeeds, install the Pi-local service so it starts automatically.

The template unit file lives at [deploy/systemd/imu-hw.service](/home/user/imu_node_smr/deploy/systemd/imu-hw.service:1).

Before installing it on the Pi, make sure these fields match the actual machine:

- `User`
- `Group`
- `WorkingDirectory`
- `ExecStart`

For a repo located at `/home/admin/imu_node_smr`, a working service looks like:

```ini
[Unit]
Description=Smart Manufacturing IMU Hardware Service
After=network.target

[Service]
Type=simple
User=admin
Group=admin
SupplementaryGroups=i2c gpio
WorkingDirectory=/home/admin/imu_node_smr
Environment=IMU_SOCKET_PATH=/run/imu-hw/imu.sock
ExecStart=/home/admin/imu_node_smr/.venv/bin/python -m imu_host
Restart=always
RestartSec=3
RuntimeDirectory=imu-hw
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
```

Install and start it:

```bash
sudo cp deploy/systemd/imu-hw.service /etc/systemd/system/imu-hw.service
sudo systemctl daemon-reload
sudo systemctl enable --now imu-hw
sudo systemctl status imu-hw
```

Verify the socket again:

```bash
ls -l /run/imu-hw/imu.sock
curl --unix-socket /run/imu-hw/imu.sock http://localhost/v1/readyz
```

Repeat Sections 1 through 5 on every IMU Pi before deploying the full Swarm stack.

## 6. Start The Container Layer From The Manager

Once the host service is ready, the Docker container can connect through the socket mount.

Typical requirements for the container:

- mount `/run/imu-hw:/run/imu-hw`
- set `IMU_SOCKET_PATH=/run/imu-hw/imu.sock`
- provide MQTT settings
- run `python3 -m imu_edge`

If using Docker Swarm, load the repo `.env` file and deploy from the manager:

```bash
set -a
source ./.env
set +a
docker stack deploy --resolve-image never -c swarm.yml imu
```

Useful checks:

```bash
docker service ps imu_imu_83_joint1
docker service logs -f imu_imu_83_joint1
```

Check each IMU service after deployment:

```bash
docker service ps imu_imu_83_joint1
docker service ps imu_imu_84_joint1
docker service ps imu_imu_85_joint1
docker service ps imu_imu_86_joint1
```

Tail logs for any node that is not starting cleanly:

```bash
docker service logs -f imu_imu_83_joint1
docker service logs -f imu_imu_84_joint1
docker service logs -f imu_imu_85_joint1
docker service logs -f imu_imu_86_joint1
```

If a task stays in `Rejected`, `Pending`, or `Starting`, verify:

- the Pi joined the Swarm
- the node label matches the service placement constraint exactly
- the `imu-hw` systemd service is healthy on that Pi
- the image tag in `.env` exists locally or is reachable from that node

## 7. Bring Up A New IMU Node End-To-End

Use this checklist for `192.168.1.84`, `192.168.1.85`, and `192.168.1.86`:

1. Copy or clone the repo to `/home/admin/imu_node_smr`.
2. Create `.venv` and install `requirements-host.txt`.
3. Install Docker if it is not already present.
4. Join the Pi to the Swarm as a worker.
5. Label the Swarm node from the manager with `device_id=<node-ip>`.
6. Start `python3 -m imu_host` manually and confirm `/v1/readyz` is healthy.
7. Install and enable the `imu-hw` systemd service.
8. Deploy or refresh the stack from the manager with `docker stack deploy --resolve-image never -c swarm.yml imu`.
9. Confirm `docker service ps` schedules the correct service to the correct node.
10. Watch `docker service logs -f` until the container begins sampling and publishing.

## 8. Stopping The System

To stop the Swarm deployment:

```bash
docker stack rm imu
```

To stop the Pi-local hardware service:

If running manually:

```bash
Ctrl+C
```

If running under systemd:

```bash
sudo systemctl stop imu-hw
```

## Troubleshooting

`This node is not a swarm worker`

Join the node again with the current worker token from the manager:

```bash
docker swarm join --token <worker-token> 192.168.1.76:2377
```

`no suitable node (scheduling constraints not satisfied on N nodes)`

The node label does not match the Swarm placement constraint. Compare:

- `docker node inspect <node-name> --format '{{ .Spec.Labels }}'`
- the `node.labels.device_id == ...` line in `swarm.yml`

`ModuleNotFoundError: No module named 'lgpio'`

Install or reinstall the host requirements:

```bash
python3 -m pip install -r requirements-host.txt
```

`PermissionError: [Errno 13] Permission denied: '/run/imu-hw'`

Create the runtime directory manually for testing, or run the systemd service so `RuntimeDirectory=imu-hw` creates it automatically.

`No such image`

Make sure the image tag in `IMU_EDGE_IMAGE` matches an image that actually exists on the target node.

`Could not establish MQTT connection`

Check `MQTT_BROKER_IP`, `MQTT_BROKER_PORT`, and network reachability from the container.
