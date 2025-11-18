# Full Synthetic System Test

### Checklist
- All clients connect to broker
- All clients send their data
- Broker receive data
- Broker/DB stores data
- All traffic if handled gracefully, w/o issues

### Check requirement validity 

## Scenario 
System test code properly initializes instances of all devices with proper number of devices, data is generated accordingly. Connections are made between client devices and the broker and TCP server. Data is send at specified intervals and proper amount of data is sent. Broker will receive the data and process and store accordingly. Dashboard messages will properly display the data transfers during the live test.

### Types of system testing used

Stress Test
- create a multitude of devices, and create a large amount of samples to test what the upper bounds of the system are

Recoverability
- an advantage of a containerized approach we can easily deploy and rerun this system as needed. If a the system crashes or external events cause the system to fail, we can easily redeploy on the host machine, or other machines as needed. 