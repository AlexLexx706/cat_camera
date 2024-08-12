from rpi_hardware_pwm import HardwarePWM


class ServoController:
    head_range = [5.5, 8]
    body_range = [5.5, 10.5]

    body_pwm = HardwarePWM(pwm_channel=1, hz=50, chip=0)
    head_pwm = HardwarePWM(pwm_channel=0, hz=50, chip=0)
    body_pwm.start(0)
    head_pwm.start(0)
    step = 0.05

    def __init__(self):
        self.head_pos = 0.5
        self.body_pos = 0.5

    def set_head_pos(self, pos):
        if pos > 1.:
            pos = 1.
        elif pos < 0.:
            pos = 0.
        self.head_pos = pos
        duty = (self.head_range[1] - self.head_range[0]
                ) * self.head_pos + self.head_range[0]
        self.head_pwm.change_duty_cycle(duty)

    def set_body_pos(self, pos):
        if pos > 1.:
            pos = 1.
        elif pos < 0.:
            pos = 0.
        self.body_pos = pos
        duty = (self.body_range[1] - self.body_range[0]
                ) * self.body_pos + self.body_range[0]
        self.body_pwm.change_duty_cycle(duty)

    def move_up(self):
        self.set_head_pos(self.head_pos + self.step)

    def move_down(self):
        self.set_head_pos(self.head_pos - self.step)

    def move_left(self):
        self.set_body_pos(self.body_pos + self.step)

    def move_right(self):
        self.set_body_pos(self.body_pos - self.step)
