# https://github.com/Blizzard/s2client-proto/blob/bff45dae1fc685e6acbaae084670afb7d1c0832c/s2clientprotocol/common.proto
from enum import Enum
from google.protobuf.message import Message

class PointI(Message):
    x: int
    y: int
    def __init__(self, x: int = ..., y: int = ...) -> None: ...

class Point2D(Message):
    x: float
    y: float
    def __init__(self, x: float = ..., y: float = ...) -> None: ...

class Point(Message):
    x: float
    y: float
    z: float
    def __init__(self, x: float = ..., y: float = ..., z: float = ...) -> None: ...

class Race(Enum):
    NoRace: int
    Terran: int
    Zerg: int
    Protoss: int
    Random: int
