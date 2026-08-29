from Motor import DCMotor

left = DCMotor(
  in1=23,
  in2=24,
  pwm=12,
)

right = DCMotor(
  in1=16,
  in2=20,
  pwm=19,
)


left.move(1)