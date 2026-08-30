from enum import Enum

class CardDirs(Enum):
  NORTH = 1
  EAST = 2
  SOUTH = 3
  WEST = 4

  def __add__(self, other: int):
    if isinstance(other, int):
      next_value = (self.value + other) % len(CardDirs)
      return CardDirs(next_value)
  
    return NotImplemented

class Direction(Enum):
    STRAIGHT = 1
    LEFT = 2
    RIGHT = 3
    NO_DETECTED = 4

    

class CardinalDirection:
  def __init__(self) -> None:
    self.direction = CardDirs.NORTH

  # right -> clockwise
  # left -> ccw
  def turn(self, direction) -> None:
    if direction == Direction.RIGHT:
      self.direction += 1
    else:
      self.direction += -1

      