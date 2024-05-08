import io
import picamera
import socket
import time
import time

server_ip = '127.0.0.1'
server_port = 9000

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, server_port))

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            self.buffer.truncate()
            client_socket.send(self.buffer.getvalue())
            self.buffer.seek(0)
        return self.buffer.write(buf)

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    output = StreamingOutput()
    camera.start_recording(output, format='mjpeg')
    while 1:
        time.sleep(100)
