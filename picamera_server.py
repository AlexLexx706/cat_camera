import io
import picamera
import socket
import time
import time

server_ip = '127.0.0.1'
server_port = 9000

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, server_port))

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    # with picamera.array.PiRGBArray(camera) as output:
    if True:
        buffer = io.BytesIO()
        for filename in camera.capture_continuous(buffer, format='jpeg'):
            buffer.truncate()
            client_socket.send(buffer.getvalue())
            buffer.seek(0)