from Motor import DCMotor


right = DCMotor(in1=25, in2=18, pwm=23)
left = DCMotor(in1=16, in2=12, pwm=24)


try:
  while True:
    right.move(0.9)
    left.move(1.0)
except KeyboardInterrupt:
  pass
finally:
  right.stop()
  left.stop()