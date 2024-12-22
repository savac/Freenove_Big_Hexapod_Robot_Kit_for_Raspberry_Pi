from dataclasses import dataclass
import sys
import time
import math
import threading
from queue import Queue

from Control import Control
from gamepad import StadiaGamepad
from Command import COMMAND as cmd
from loguru import logger

import functools


@dataclass
@functools.total_ordering
class XYEvent:
    x: int
    y: int
    sec: int
    usec: int

    def get_amplitude(self):
        return (self.x**2 + self.y**2) ** 0.5

    def __eq__(self, other):
        return (self.x, self.y, self.sec, self.usec) == (
            other.x,
            other.y,
            other.sec,
            other.usec,
        )

    def __lt__(self, other):
        return self.get_amplitude() < other.get_amplitude()


def remap(value, fromLow, fromHigh, toLow, toHigh):
    return (toHigh - toLow) * (value - fromLow) / (fromHigh - fromLow) + toLow


def make_cmd_move(x, y, action_flag, move_speed, gait_flag):

    # self.action_flag = 1  # 1 or 2
    # self.move_speed = 8  # [2, 10]
    # self.gait_flag = 1  # 1 or 2

    x = remap(x, 1, 255, -35, 35)
    y = remap(y, 1, 255, -35, 35)

    if action_flag == 1:
        angle = 0
    else:
        if x != 0 or y != 0:
            angle = math.degrees(math.atan2(x, y))

            if angle < -90 and angle >= -180:
                angle = angle + 360
            if angle >= -90 and angle <= 90:
                angle = remap(angle, -90, 90, -10, 10)
            else:
                angle = remap(angle, 270, 90, 10, -10)
        else:
            angle = 0

    command = [
        cmd.CMD_MOVE,
        str(gait_flag),
        str(round(x)),
        str(round(y)),
        str(move_speed),
        str(round(angle)),
    ]

    return command

def make_cmd_camera(x, y):
    x = remap(x, 1, 255, 50, 180)
    y = remap(y, 1, 255, 0, 180)

    command = [cmd.CMD_CAMERA, str(round(x)), str(round(y))]
    return command

class HexapodController(threading.Thread):
    def __init__(self):
        super().__init__()
        self.control = Control()
        self.control.Thread_conditiona.start()

        self.command_queue = Queue(maxsize=100)

        # self.instruction = threading.Thread(target=self.receive_instruction)
        # self.instruction.start()

    def run(self):
        while True:
            # if there is no command, wait for one
            if self.command_queue.empty():
                time.sleep(0.01)
                continue

            # get the command
            data = self.command_queue.get()
            print(f"Command: {data}")

            if cmd.CMD_MOVE in data:
                self.control.order=data
                self.control.timeout=time.time()

            # if data==None or data[0]=='':
            #     continue
            # elif cmd.CMD_BUZZER in data:
            #     self.buzzer.run(data[1])
            # elif cmd.CMD_POWER in data:
            #     try:
            #         batteryVoltage=self.adc.batteryPower()
            #         command=cmd.CMD_POWER+"#"+str(batteryVoltage[0])+"#"+str(batteryVoltage[1])+"\n"
            #         #print(command)
            #         self.send_data(self.connection1,command)
            #         if batteryVoltage[0] < 5.5 or batteryVoltage[1]<6:
            #             for i in range(3):
            #             self.buzzer.run("1")
            #             time.sleep(0.15)
            #             self.buzzer.run("0")
            #             time.sleep(0.1)
            #     except:
            #         pass
            # elif cmd.CMD_LED in data:
            #     try:
            #         stop_thread(thread_led)
            #     except:
            #         pass
            #     thread_led=threading.Thread(target=self.led.light,args=(data,))
            #     thread_led.start()
            # elif cmd.CMD_LED_MOD in data:
            #     try:
            #         stop_thread(thread_led)
            #         #print("stop,yes")
            #     except:
            #         #print("stop,no")
            #         pass
            #     thread_led=threading.Thread(target=self.led.light,args=(data,))
            #     thread_led.start()
            # elif cmd.CMD_SONIC in data:
            #     command=cmd.CMD_SONIC+"#"+str(self.sonic.getDistance())+"\n"
            #     self.send_data(self.connection1,command)
            # elif cmd.CMD_HEAD in data:
            #     if len(data)==3:
            #         self.servo.setServoAngle(int(data[1]),int(data[2]))
            elif cmd.CMD_CAMERA in data:
                if len(data)==3:
                    x=self.control.restriction(int(data[1]),50,180)
                    y=self.control.restriction(int(data[2]),0,180)
                    self.servo.setServoAngle(0,x)
                    self.servo.setServoAngle(1,y)
            # elif cmd.CMD_RELAX in data:
            #     #print(data)
            #     if self.control.relax_flag==False:
            #         self.control.relax(True)
            #         self.control.relax_flag=True
            #     else:
            #         self.control.relax(False)
            #         self.control.relax_flag=False
            # elif cmd.CMD_SERVOPOWER in data:
            #     if data[1]=="0":
            #         GPIO.output(self.control.GPIO_4,True)
            #     else:
            #         GPIO.output(self.control.GPIO_4,False)

            else:
                pass


def main() -> int:
    controller = HexapodController()
    controller.daemon = True
    controller.start()

    gamepad = StadiaGamepad()
    if gamepad.check_connected():
        gamepad.daemon = True  # exit with the main thread
        gamepad.start()
    else:
        logger.warning("Could not connect to the controller")
        return 1

    # collect the events from the gamepad and turn them into commands
    move_xy = [0, 0]
    rotate_xy = [0, 0]
    while True:

        # the exit command is acted upen immediately
        if gamepad.exit_requested:
            break

        if gamepad.events.empty():
            time.sleep(0.01)
            continue

        event = gamepad.events.get()

        # CMD_MOVE

        # move
        if event.code == 0:
            move_xy[0] = event.value
        elif event.code == 1:
            move_xy[1] = event.value

        if None not in move_xy:
            print(move_xy)
            command = make_cmd_move(move_xy[0], move_xy[1], 
                                    action_flag=2, move_speed=8, gait_flag=1)
            controller.command_queue.put(command)
            move_xy = [None, None]

        # CMD_CAMERA
        if event.code == 2:
            command = make_cmd_camera(event.value, 1)
            controller.command_queue.put(command)
        elif event.code == 5:
            command = make_cmd_camera(1, event.value)
            controller.command_queue.put(command)

        if None not in rotate_xy:

            rotate_xy = [None, None]

    #  is this necessary?
    gamepad.join()
    controller.join()
    return 0


if __name__ == "__main__":
    sys.exit(main())  # next section explains the use of sys.exit
