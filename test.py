from adafruit_servokit import ServoKit


servo_channel = 0

servo_kit = ServoKit(channels=16)

servo_kit.continuous_servo[servo_channel].set_pulse_width_range(1200, 1800)
try:
    while True:
        servo_kit.continuous_servo[servo_channel].throttle = 1.0
finally:
    servo_kit.continuous_servo[servo_channel].throttle = None