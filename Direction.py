from enum import Enum


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

    def __sub__(self, other: int):
        if isinstance(other, int):
            next_value = (self.value - other) % len(CardDirs)
            return CardDirs(next_value)
        return NotImplemented


class Direction(Enum):
    STRAIGHT = 1
    LEFT = 2
    RIGHT = 3
    NO_DETECTED = 4


class CardinalDirection:
    def __init__(self, initial_direction: CardDirs = CardDirs.NORTH) -> None:
        self.direction = initial_direction

    # right -> clockwise (+1)
    # left -> counter-clockwise (-1)
    def turn(self, direction: Direction) -> None:
        if direction == Direction.RIGHT:
            self.direction = self.direction + 1
        elif direction == Direction.LEFT:
            self.direction = self.direction - 1