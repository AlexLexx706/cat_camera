import time
import os
import types
from flask import render_template, Response
import gevent
from gevent import event
from gevent.server import StreamServer
from flask import Flask
from flask_socketio import SocketIO


app = Flask(__name__)
socketio = SocketIO(app)
collector = types.SimpleNamespace(frame=None, condition=event.Event())


def handle(socket, _address):
    while True:
        frame = socket.recv(131072)
        if not frame:
            print("client disconnected")
            break
        collector.frame = frame
        collector.condition.set()
        collector.condition.clear()


video_stream_server = StreamServer(('127.0.0.1', 9000), handle)
gevent.spawn(video_stream_server.serve_forever)


def generate_frames():
    yield b'--frame\r\n'
    while True:
        collector.condition.wait()
        yield b'Content-Type: image/jpeg\r\n\r\n' + collector.frame + b'\r\n--frame\r\n'


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/index.html')
def index_2():
    return render_template('index.html')


@app.route('/stream.mjpeg')
def video_feed():
    resp = Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame')
    resp.headers['Cache-Control'] = 'no-cache, private'
    resp.headers['Pragma'] = 'no-cache'
    return resp


@socketio.on('button_click')
def handle_button_click(data):
    button_id = data['button_id']
    print('Button clicked:', button_id)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000)
