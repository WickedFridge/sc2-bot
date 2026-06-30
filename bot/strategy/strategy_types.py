
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
    UNDER_ATTACK = 3
    PROXY_BUILDINGS = 4
    CHEESE_CANNON_RUSH = 5
    CHEESE_BUNKER_RUSH = 6
    CHEESE_LING_DRONE = 7
    CHEESE_LING_FLOOD = 8
    CHEESE_WORKER_RUSH = 9
    CHEESE_ROACH_RUSH = 10
    CHEESE_SKYTOSS = 11
    CHEESE_BATTLECRUISER = 12
    CHEESE_PROXY_RAX = 13
    CHEESE_IMMORTAL_BUST = 14
    CHEESE_UNKNOWN = 15

    @property
    def is_cheese(self) -> bool:
        return self in [
            Situation.PROXY_BUILDINGS,
            Situation.CHEESE_CANNON_RUSH,
            Situation.CHEESE_BUNKER_RUSH,
            Situation.CHEESE_LING_DRONE,
            Situation.CHEESE_LING_FLOOD,
            Situation.CHEESE_WORKER_RUSH,
            Situation.CHEESE_ROACH_RUSH,
            Situation.CHEESE_SKYTOSS,
            Situation.CHEESE_PROXY_RAX,
            Situation.CHEESE_IMMORTAL_BUST,
            Situation.CHEESE_BATTLECRUISER,
            Situation.CHEESE_UNKNOWN,
        ]

    @property
    def is_precarious(self) -> bool:
        return (
            self == Situation.UNDER_ATTACK
            or (
                self.is_cheese
                and self not in [
                    Situation.CHEESE_SKYTOSS,
                    Situation.CHEESE_BATTLECRUISER,
                ]
            )
        )

    def __repr__(self) -> str:
        return f"{self.name.capitalize()}"


for item in Priority:
    globals()[item.name] = item
for item in Strategy:
    globals()[item.name] = item
for item in Situation:
    globals()[item.name] = item