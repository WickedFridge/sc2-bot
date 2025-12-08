
import enum

class Priority(enum.Enum):
    ECONOMY = 0
    TECH = 1
    BUILD_ARMY = 2
    BUILD_DEFENSE = 3

    def __repr__(self) -> str:
        return f"{self.name.capitalize()}"

class Strategy(enum.Enum):
    MACRO_GREEDY = 0
    MACRO_SAFE = 1
    TURTLE_ECO = 2
    TURTLE_TECH = 3
    RUSH_TECH_GREEDY = 4
    RUSH_TECH_SAFE = 4

    def __repr__(self) -> str:
        return f"{self.name.capitalize()}"

class Situation(enum.Enum):
    STABLE = 0
    BEHIND = 1
    AHEAD = 2
    CANON_RUSH = 3
    BUNKER_RUSH = 4
    UNDER_ATTACK = 5
    CHEESE_LING_DRONE = 6

    def __repr__(self) -> str:
        return f"{self.name.capitalize()}"


for item in Priority:
    globals()[item.name] = item
for item in Strategy:
    globals()[item.name] = item
for item in Situation:
    globals()[item.name] = item