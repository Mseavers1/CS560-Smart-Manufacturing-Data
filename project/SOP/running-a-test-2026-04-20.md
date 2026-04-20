# Running A Test Session - Apr 20, 2026

This SOP replaces the older per-device `docker compose --env-file ... up -d` workflow for IMU nodes.

The current process uses Docker Swarm from the manager to launch the three active IMU RPIs:

- IMU 83 on `192.168.1.83` as service `imu_83_joint1`
- IMU 84 on `192.168.1.84` as service `imu_84_joint2`
- IMU 85 on `192.168.1.85` as service `imu_85_joint3`

All operations listed here are assumed to be run on the Alienware PC or the Swarm manager unless otherwise stated.

## Test Session Overview

1. Initialize the middleware.
2. Confirm the IMU RPIs are powered on and their host services are healthy.
3. Start the camera nodes.
4. Deploy the IMU Swarm stack from the manager.
5. Confirm the dashboard is listening.
6. Start a session from the dashboard.
7. Confirm the IMU services are actively publishing.
8. Start the robot.
9. Stop the IMU services and session when the robot run ends.
10. Review the collected data.

## 1. Initialize The Middleware

The middleware runs on the MiniPC at `192.168.1.76`. In many cases it is already up. First check the dashboard:

- [Dashboard](http://192.168.1.76/data/dashboard)

If the dashboard is reachable and showing healthy listeners, continue to Step 2. If not, SSH into the middleware host:

```bash
ssh data-team@192.168.1.76
```

When prompted for a password:

```text
1234
```

Move into the project directory:

```bash
cd smart_manufacturing_research/project
```

Start the middleware containers:

```bash
docker compose up -d
```

What the flags mean:

- `up` creates and starts the services defined in `docker-compose.yml`
- `-d` runs the containers in detached mode so the terminal returns immediately instead of streaming logs

If image analysis is also required, start it on the image analysis machine:

```bash
ssh username@192.168.1.113
cd camera_sensor_fusion/pi-stream/
docker compose up -d
```

## 2. Confirm The IMU RPIs Are Ready

Before deploying the Swarm stack, make sure each IMU Pi is powered on and the host-side hardware service is healthy.

The active IMU RPIs are:

- `192.168.1.83`
- `192.168.1.84`
- `192.168.1.85`

On each Pi, the `imu-hw` systemd service should already be installed using the setup in [IMU_SETUP.md](/home/user/CS560-Smart-Manufacturing-Data/project/SOP/IMU_SETUP.md:1).

You can verify each Pi with:

```bash
ssh admin@192.168.1.83
sudo systemctl status imu-hw --no-pager
ls -l /run/imu-hw/imu.sock
curl --unix-socket /run/imu-hw/imu.sock http://localhost/v1/readyz
```

Repeat the same check for `.84` and `.85`.

Healthy signs:

- `imu-hw` is `active (running)`
- `/run/imu-hw/imu.sock` exists
- `readyz` returns `"ready": true`

## 3. Start The Camera Nodes

The cameras still follow their normal startup flow.

### Camera On `192.168.1.80`

```bash
ssh admin@192.168.1.80
cd camera_sensor_fusion/
docker compose up -d
```

### Camera On `192.168.1.92`

```bash
ssh admin@192.168.1.92
cd camera_sensor_fusion/middleware/
docker compose up -d
```

## 4. Deploy The IMU Swarm Stack

This is the biggest difference from the older SOP.

Do not SSH into each IMU Pi and run `docker compose --env-file ... up -d`. Instead, deploy the IMU services once from the Swarm manager.

SSH into the Swarm manager if needed:

```bash
ssh <manager-user>@192.168.1.76
```

Move into the project directory:

```bash
cd /home/user/CS560-Smart-Manufacturing-Data/project
```

Load the `.env` file into the current shell:

```bash
set -a
source ./.env
set +a
```

What these commands do:

- `set -a` tells the shell to automatically export variables created or loaded after this point
- `source ./.env` loads the variables from `.env` into the current shell session
- `set +a` turns automatic export back off so later shell variables are not all exported by default

Deploy the IMU stack:

```bash
docker stack deploy --resolve-image never -c swarm.yml imu
```

What the command means:

- `docker stack deploy` tells Docker Swarm to create or update a stack of services
- `--resolve-image never` tells Swarm not to query a registry to resolve image digests during deploy; this is helpful when the needed image is already present on the nodes or registry lookup is undesirable
- `-c swarm.yml` tells Swarm to use `swarm.yml` as the stack definition file
- `imu` is the stack name; Swarm prefixes created services with this stack name, which is why service names appear like `imu_imu_83_joint1`

The `swarm.yml` file currently defines these IMU services:

- `imu_83_joint1`
- `imu_84_joint2`
- `imu_85_joint3`

Each service is pinned to its matching Pi by the `node.labels.device_id` placement constraint and receives its device-specific environment values from `.env`.

## 5. Verify The Swarm Deployment

After deploying, confirm the services were scheduled correctly:

```bash
docker service ps imu_imu_83_joint1
docker service ps imu_imu_84_joint2
docker service ps imu_imu_85_joint3
```

If needed, inspect the resolved environment for a service:

```bash
docker service inspect imu_imu_85_joint3 --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}'
```

This is useful for verifying values such as:

- `DEVICE_ID=85`
- `MQTT_CLIENT_ID=85`
- `MQTT_TOPIC=imu/85`
- `IMU_SESSION_ID=imu-node-85`

You can also watch logs:

```bash
docker service logs -f imu_imu_83_joint1
docker service logs -f imu_imu_84_joint2
docker service logs -f imu_imu_85_joint3
```

Healthy signs:

- each service shows a running task on the correct node
- the logs do not show socket connection failures
- the services begin sampling and publishing

If a service does not start, check:

- the target Pi is online and part of the Swarm
- the node label matches the placement constraint in `swarm.yml`
- the `imu-hw` host service is healthy on that Pi
- the image tag in `.env` exists on or is reachable from the node

## 6. Ensure The Dashboard Shows Listening Status

The dashboard should show green listening indicators for the services that are waiting for incoming data.

If there are red messages about no active session yet, those are usually expected before a session is started, for example:

```text
[timestamp] CAMERA batch insert failed: No current active session. Run a GET to start a new session.
```

That message is not itself a blocker before the session begins.

## 7. Start A Session From The Dashboard

When the dashboard is healthy, the robot operator is ready, and the IMU services are already running in Swarm, start a session from the dashboard by clicking:

- `Start Session`

Because the IMU services are already running, they should begin associating data with the active session once the session is started.

## 8. Start The Robot

The robot is started manually by the human operator in the downstairs lab. Coordinate with the operator before starting the session and IMU services.

## 9. Stop The IMU Services And End The Session

When the robot run is complete, remove the IMU stack from the manager:

```bash
docker stack rm imu
```

What this does:

- `docker stack rm` removes the services that belong to the `imu` stack
- containers are stopped by Swarm as the services are removed

Give the system roughly 15 to 20 seconds to flush any remaining messages, then click:

- `Stop Session`

## 10. Review Data

After the session ends, review the stored data:

- [Database Browser](http://192.168.1.111:8080/browser/)
- [Dashboard](http://192.168.1.76/data/dashboard)

## Quick Reference

### Start middleware

```bash
docker compose up -d
```

### Deploy IMU Swarm services

```bash
cd /home/user/CS560-Smart-Manufacturing-Data/project
set -a
source ./.env
set +a
docker stack deploy --resolve-image never -c swarm.yml imu
```

### Check IMU services

```bash
docker service ps imu_imu_83_joint1
docker service ps imu_imu_84_joint2
docker service ps imu_imu_85_joint3
```

### Tail IMU logs

```bash
docker service logs -f imu_imu_83_joint1
docker service logs -f imu_imu_84_joint2
docker service logs -f imu_imu_85_joint3
```

### Stop IMU Swarm services

```bash
docker stack rm imu
```
