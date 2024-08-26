import datetime
import logging
import os
import socket
import subprocess
import time
import numpy as np
import picamera
import picamera.array
import cv2
import get_diff
import config

LOG = logging.getLogger(__name__)


class CameraServer:
    MAX_TRY_CONNECT_TIME = 30
    MIN_DETECTION_TIME = 3.

    def __init__(self, address, video_resolution, buffer_len_sec, detection_period, tmp_dir, save_dir, detection_frame_size, begins_sec):
        self._address = address
        self._video_resolution = video_resolution
        self._buffer_len_sec = buffer_len_sec
        self._detection_period = detection_period
        self._tmp_dir = tmp_dir
        self._save_dir = save_dir
        self._detection_frame_size = detection_frame_size
        self._begins_sec = begins_sec

        self._client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        start_time = time.time()
        while True:
            try:
                self._client_socket.connect(self._address)
                break
            except ConnectionRefusedError as e:
                if time.time() - start_time >= self.MAX_TRY_CONNECT_TIME:
                    raise e
                else:
                    LOG.warning(e)
                    time.sleep(1)

        self._diff = get_diff.Diff()
        get_diff.ENABLE_DEBUG = False

        self._camera = picamera.PiCamera()
        self._camera.resolution = self._video_resolution
        self._stream = picamera.PiCameraCircularIO(
            self._camera, seconds=self._buffer_len_sec)

        self._image = np.empty(
            (self._detection_frame_size[1] *
             self._detection_frame_size[0] * 3,),
            dtype=np.uint8)
        self._resize_shape = (
            self._detection_frame_size[1], self._detection_frame_size[0], 3)

        os.makedirs(self._tmp_dir, exist_ok=True)
        os.makedirs(self._save_dir, exist_ok=True)

    @staticmethod
    def join_h264_and_covert_to_mp4(h264_paths, out_file):
        LOG.debug("join files:%s to:%s", h264_paths, out_file)

        concat_input = '|'.join(h264_paths)
        # Команда для запуска ffmpeg
        command = ['ffmpeg', '-i',
                   f"concat:{concat_input}", '-c:v', 'copy', out_file]
        try:
            subprocess.run(command, check=True)
            LOG.debug("files:%s contervet to:%s", h264_paths, out_file)
        except subprocess.CalledProcessError as e:
            LOG.exception(e)

    def detect_motion(self):
        # capture BGR frame
        self._camera.capture(
            self._image, 'bgr', use_video_port=True,
            resize=self._detection_frame_size)
        self._image = self._image.reshape(self._resize_shape)
        res = self._diff.process(self._image)
        _, encoded = cv2.imencode('.jpg', self._image)
        self._client_socket.send(encoded.tobytes())
        return res

    def process(self):
        self._camera.start_recording(self._stream, format='h264')
        try:
            while True:
                self._camera.wait_recording(self._detection_period)

                if self.detect_motion():
                    start_record_time = time.time()
                    LOG.debug('Motion detected!')
                    # As soon as we detect motion, split the recording to
                    # record the frames "after" motion
                    base_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    after_path = os.path.join(
                        self._tmp_dir, f'{base_name}_after.h264')
                    self._camera.split_recording(after_path)

                    # Write the 10 seconds "before" motion to disk as well
                    before_path = os.path.join(
                        self._tmp_dir, f'{base_name}_before.h264')
                    self._stream.copy_to(before_path, seconds=self._begins_sec)
                    self._stream.clear()

                    # detection of stop motion
                    start_time = time.time()
                    while True:
                        if self.detect_motion():
                            start_time = time.time()
                        self._camera.wait_recording(self._detection_period)

                        if (time.time() - start_time) > self.MIN_DETECTION_TIME:
                            LOG.debug('Motion stopped!')
                            break

                    self._camera.split_recording(self._stream)
                    duration = time.time() - start_record_time + self._begins_sec
                    # save all to mp4
                    out_path = os.path.join(
                        self._save_dir, f'{base_name}__{int(duration)}.mp4')
                    file_to_join = [before_path, after_path]
                    self.join_h264_and_covert_to_mp4(file_to_join, out_path)

                    # clean original files
                    for path in file_to_join:
                        os.remove(path)
        finally:
            self._camera.stop_recording()


def main():
    logging.basicConfig(level=logging.DEBUG)
    server = CameraServer(
        address=(config.SERVER_IP, config.SERVER_PORT),
        video_resolution=config.VIDEO_RESOLUTION,
        buffer_len_sec=config.CIRCULAR_BUFFER_LEN_SEC,
        detection_period=config.DETECTION_PERIOD_SEC,
        save_dir=config.VIDEO_FILES_DIR,
        tmp_dir=config.TEMP_DIR,
        detection_frame_size=config.DETECTION_FRAME_SIZE,
        begins_sec=config.BEGINS_SEC)
    server.process()


if __name__ == "__main__":
    main()
