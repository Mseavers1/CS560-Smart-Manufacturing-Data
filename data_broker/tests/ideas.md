# Testing the software

## Unit Tests
Validate individual functions, classes, modules

Frameworks
- pytest

- unittest.mock || pytest-mock

#### Components to test

##### FastAPI backend
- routes
- logic
- validation
- helper functions

how to test
- TestClient from fastapi.testclient (simulates requests and asserts)

##### MQTT handlers
- message parsing
- publish/subscribe callbacks

how to test
- Mock the MQTT client (paho-mqtt) simulate massages
    - Mock data creation and client on separate machine in LAN

##### Database layer
- CRUD operations
- query correctness

how to test
- use temp DB and pytest fixtures

##### TCP server logic
- command parsing, message formatting

how to test
- mock socket connectinos using socket.socketpair() or pytest fixtures 

### CI/CD Flow

install python (pytest, facade-sdk, etc...)
create an identical compose for the test
run integration Tests
spin down container

create a workflow out of this (optional)

### Integratino Tests

##### Scenarios
- Client can publish to data broker using MQTT 
    - FastAPI data broker, MQTT facade
- Robot can publish to data broker with TCP
    - TCP Server on data broker, robot system
- Clients can use NTP Facade to request time
    - NTP container, ntp facade package
- Clients publish data into the broker and the data is saved
    - All the above but we include the database container here



