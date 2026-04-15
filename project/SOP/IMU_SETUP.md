# IMU Setup Guide

This guide covers the Raspberry Pi host setup for the redesigned IMU deployment.

The new architecture has two parts:

1. A Pi-local hardware service started with `python -m imu_host`
2. A containerized edge service that talks to the host service over `/run/imu-hw/imu.sock`

The host service must be working before the Docker container can use the IMU.

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

## 5. Start The Container Layer

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

## 6. Install The Host Service With systemd

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

## 7. Stopping The System

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
