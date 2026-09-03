from Motor import DCMotor

right = DCMotor(in1=25, in2=18, pwm=23, scale=0.85)
left = DCMotor(in1=16, in2=12, pwm=24, scale=1.0)


while True:
  try:
    right.move(1.0)
    left.move(1.0)
  except KeyboardInterrupt:
    pass
  finally:
    right.stop()
    left.stop()