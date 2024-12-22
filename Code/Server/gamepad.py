import sys
import os
from evdev import InputDevice, ecodes
import subprocess
import time
import threading
from collections import deque
from queue import Queue
from loguru import logger

INPUT_FILE = "/dev/input/event2"


def run_cmd(command: str, verbose: bool = True):
    """Execute shell commands and return STDOUT"""
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    if verbose:
        logger.debug(stdout.decode("utf-8"))
        logger.debug(stderr.decode("utf-8"))

    return stdout.decode("utf-8")


class StadiaGamepad(threading.Thread):
    def __init__(
        self, mac_address: str = MAC_ADDRESS, input_file: str = INPUT_FILE
    ):
        super().__init__()
        self.mac_address = mac_address
        self.input_file = input_file # /dev/input/eventX
        self.device = None # an instance of InputDevice
        # self.events = deque([], maxlen=100) # holds the last 100 events
        self.events = Queue(maxsize=100)
        self.exit_requested = False # flag to exit the thread

        self.connect()

    def pair(self):
        run_cmd("bluetoothctl agent on")
        run_cmd("bluetoothctl default-agent")
        run_cmd("timeout 10s bluetoothctl scan on")
        run_cmd(f"bluetoothctl pair {self.mac_address}")

    def check_connected(self):
        logger.info(f"Checking if the device is connected: {self.mac_address}")
        return os.path.exists(self.input_file)

    def connect(self):
        if not self.check_connected():
            run_cmd("bluetoothctl agent on")
            run_cmd("bluetoothctl default-agent")
            run_cmd(f"bluetoothctl connect {self.mac_address}")
            run_cmd(f"bluetoothctl info {self.mac_address}")
            time.sleep(2)

        if self.check_connected():
            self.device = InputDevice(self.input_file)
            logger.info("Connected device ok")
        else:
            logger.error("Could not connect to the device")

    def disconnect(self):
        run_cmd(f"bluetoothctl disconnect {self.mac_address}")

    def run(self):
        for event in self.device.read_loop():

            if event.type == ecodes.EV_ABS:
                if event.code in [0, 1, 2, 5]:
                    print(f'{event.code}: {event.value}')
                    self.events.put(event)

            elif event.code == 315 or self.exit_requested:
                logger.info("Exit requested")
                self.exit_requested = True
                self.disconnect()
                break

def main() -> int:
    gamepad = StadiaGamepad()
    if gamepad.check_connected():
        gamepad.run()
    else:
        raise RuntimeError("There is no connected controller.")


if __name__ == "__main__":
    sys.exit(main())  # next section explains the use of sys.exit
