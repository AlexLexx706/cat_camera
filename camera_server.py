import cv2
import socket
import time

server_ip = '127.0.0.1'
server_port = 9000

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, server_port))
camera = cv2.VideoCapture(0)

try:
    while True:
        ret, frame = camera.read()
        # frame = cv2.resize(frame, (6, 100))
        _, encoded = cv2.imencode('.jpg', frame)
        encoded = encoded.tobytes()
        client_socket.send(encoded)
finally:
    camera.release()
    client_socket.close()
