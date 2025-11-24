import socket

HOST = "192.168.1.76"  # or external IP of your fast_server
PORT = 5001

message = (
    "2025-10-28T12:00:00,1730116800,1.1,2.2,3.3,4.4,5.5,6.6,10.0,"
    "20.0,30.0,0.1,0.2,0.3\n"
)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(message.encode())
