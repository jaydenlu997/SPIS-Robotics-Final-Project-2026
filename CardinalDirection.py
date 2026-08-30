from enum import Enum
from DirectionEnum import Direction

class CardDirs(Enum):
  NORTH = 0
  EAST = 1
  SOUTH = 2
  WEST = 3

  def __add__(self, other: int):
    if isinstance(other, int):
      next_value = (self.value + other) % len(CardDirs)
      return CardDirs(next_value)
  
    return NotImplemented


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

      