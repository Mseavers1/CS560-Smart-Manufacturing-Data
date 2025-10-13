#!/bin/bash

echo "Starting Containers..."

docker start postgres-db
docker start mqtt-broker
docker start fastapi-app

echo "All Containers Started Successfully!"