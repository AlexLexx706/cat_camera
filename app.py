import os
import types
from flask import render_template, Response, redirect, url_for
import gevent
from gevent import event
from gevent.server import StreamServer
from flask import Flask
from flask_socketio import SocketIO
import config
import servo_controller as sc

os.makedirs(config.VIDEO_FILES_DIR, exist_ok=True)

app = Flask(__name__)
socketio = SocketIO(app)
collector = types.SimpleNamespace(frame=None, condition=event.Event())
servo_controller = sc.ServoController()


def handle(socket, _address):
    while True:
        frame = socket.recv(131072)
        if not frame:
            print("client disconnected")
            break
        collector.frame = frame
        collector.condition.set()
        collector.condition.clear()


video_stream_server = StreamServer(
    (config.SERVER_IP, config.SERVER_PORT), handle)
gevent.spawn(video_stream_server.serve_forever)


def generate_frames():
    yield b'--frame\r\n'
    while True:
        collector.condition.wait()
        yield b'Content-Type: image/jpeg\r\n\r\n' + collector.frame + b'\r\n--frame\r\n'


@app.route('/')
def index():
    files = [os.path.join(config.VIDEO_FILES_DIR, name) for name in os.listdir(config.VIDEO_FILES_DIR)]
    videos = sorted(filter(os.path.isfile, files), key=os.path.getmtime)
    return render_template('index.html', videos=[os.path.split(path)[1] for path in videos])

    # videos = os.listdir(config.VIDEO_FILES_DIR)
    # videos = [video for video in videos if video.endswith('.mp4')]
    # return render_template('index.html', videos=videos)

@app.route('/index.html')
def index_2():
    redirect(url_for('index'))


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
    if button_id == 'up':
        servo_controller.move_up()
    elif button_id == 'down':
        servo_controller.move_down()
    elif button_id == 'left':
        servo_controller.move_left()
    elif button_id == 'right':
        servo_controller.move_right()
    # remove all video files
    elif button_id == 'remove':
        for name in os.listdir(config.VIDEO_FILES_DIR):
            os.remove(os.path.join(config.VIDEO_FILES_DIR, name))


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000)
