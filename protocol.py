import re
import threading
from types import SimpleNamespace
import time
import serial
import logging
from collections.abc import Callable

LOG = logging.getLogger(__name__)


class Protocol:
    """implementation of the protocol of interaction between base and client
    """
    MAX_BUFFER_SIZE = 100
    RE_HEADER = re.compile(
        br'([A-Z]{2})([0-9A-F]{3})(?:%(\w*)%)?(.*)')

    def __init__(self):
        self._read_thread = None
        self._stop_event = threading.Event()
        self._serial = None
        self._cmd_index = 0
        self._cmd_condition = threading.Condition()
        self._last_re = SimpleNamespace(id='', prefix='', msg='')
        self._msg_handler = None
        self._line_handler = self._process_line

    def set_msg_handler(self, handler: Callable[[str, bytes], None]) -> None:
        """Send handel for messages

        Args:
            handler (Callable[[str,bytes], None]): handler with parameters: msg_id, message data
        """
        self._msg_handler = handler

    def start(self, port: str = '/dev/ttyS0', speed: int = 115200):
        """start protocol
        Args:
            port (str, optional): file path of port. Defaults to '/dev/ttyS0'.
            speed (int, optional): port speed, default: 115200
        """
        if self._read_thread is not None:
            raise RuntimeError('protocol already running')
        self._cmd_index = 0
        self._serial = serial.Serial(port, speed, timeout=1.0)
        self._read_thread = threading.Thread(target=self._read_proc)
        self._stop_event.clear()
        self._read_thread.start()
        time.sleep(3)

    def stop(self):
        """stop protocol
        """
        if self._read_thread is None:
            raise RuntimeError('Reading serial thread not exist')
        self._stop_event.set()
        self._read_thread.join()
        self._serial.close()
        self._read_thread = None

    def send_cmd(self, cmd: str) -> bytes:
        """send command and waiting response

        Args:
            cmd (str): command set/print,path, for example set,/controller/mode,1
        Returns:
            bytes: result data
        """
        cur_prefix = self._cmd_index
        self._cmd_index += 1
        full_cmd = f'%{cur_prefix}%{cmd}'
        # debug
        LOG.debug("cmd:%s", full_cmd)
        self._serial.write(f'{full_cmd}\n'.encode())
        res = self._wait_responce(cur_prefix)
        LOG.debug('res:%s', res)
        return res

    def _wait_responce(self, prefix: str, timeout: int = 0.5) -> bytes:
        """waiting of response

        Args:
            prefix (str): prefix of command
            timeout (int, optional): timeout of wait. Defaults to 0.5.

        Raises:
            RuntimeWarning: wrong prefix detected
            RuntimeError: some thin goes wrong

        Returns:
            bytes: data
        """
        with self._cmd_condition:
            self._cmd_condition.wait(timeout)
            if self._last_re.prefix != prefix:
                raise RuntimeWarning(
                    f"prefix:{prefix}!= {self._last_re.prefix} in:{self._last_re.id} msg:{self._last_re.msg}")

            if self._last_re.id == 'ER':
                raise RuntimeError(
                    f"error:{self._last_re.msg}")
            return self._last_re.msg

    def _process_line(self, line: bytes):
        """Default handler of line

        Args:
            line (bytes): line
        """
        # LOG.debug("line:%s", line)
        pass

    def _read_proc(self) -> None:
        """decode stream form serial port
        """
        while not self._stop_event.is_set():
            line = self._serial.readline()
            match = self.RE_HEADER.search(line)

            # header decoded
            if match:
                msg_id = match.group(1)
                msg_len = int(match.group(2), 16)
                start = match.end(2)
                cur_message_len = len(line) - start

                if cur_message_len >= msg_len:
                    end = start + msg_len
                    # commands responce
                    if msg_id in (b'RE', b'ER'):
                        start = match.start(4)
                        msg_prefix = match.group(3)
                        # riase contition for waiter
                        with self._cmd_condition:
                            msg = line[start:end]
                            self._last_re.id = msg_id.decode()
                            self._last_re.prefix = int(msg_prefix)
                            self._last_re.msg = msg.decode()
                            self._cmd_condition.notify()
                            # LOG.debug(line[match.start(0):end].decode())
                    # status message
                    elif self._msg_handler:
                        self._msg_handler(msg_id, line[start:end])
            # process lines
            elif line:
                self._line_handler(line)

def test():
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] %(funcName)20s() %(message)s")
    protocol = Protocol()
    protocol.start()
    time.sleep(5)
    protocol.send_cmd("set,/imu/debug_level,0")
    time.sleep(5)
    protocol.send_cmd("set,/imu/debug_level,1")
    time.sleep(5)
    protocol.send_cmd("set,/imu/debug_level,2")
    time.sleep(5)
    protocol.send_cmd("set,/imu/debug_level,3")
    time.sleep(5)
    protocol.send_cmd("set,/imu/debug_level,0")
    time.sleep(5)
    protocol.stop()


def test_move_camera():
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] %(funcName)20s() %(message)s")
    protocol = Protocol()
    protocol.start()
    central_pos = int(protocol.send_cmd(
        'print,/stepper_motor_controller/current_position'))
    protocol.send_cmd('set,/stepper_motor_controller/move,10')
    LOG.debug("move to 10")
    #waiting for complete running
    time.sleep(0.5)
    while int(protocol.send_cmd('print,/stepper_motor_controller/running')):
        time.sleep(0.5)

    pos = int(central_pos * 1.5)
    protocol.send_cmd(
        f'set,/stepper_motor_controller/move,{pos}')
    LOG.debug(f"move to {pos}")

    #waiting for complete running
    time.sleep(0.5)
    while int(protocol.send_cmd('print,/stepper_motor_controller/running')):
        time.sleep(0.5)

    protocol.send_cmd(
        f'set,/stepper_motor_controller/move,{central_pos}')
    LOG.debug(f"move to {central_pos}")
    #waiting for complete running
    time.sleep(10)
    while int(protocol.send_cmd('print,/stepper_motor_controller/running')):
        time.sleep(0.5)

    LOG.debug(f"stop")

    protocol.stop()

if __name__ == '__main__':
    # test()
    test_move_camera()
