import enum

class Orders(enum.Enum):
    FIGHT = 0
    RETREAT = 1
    DEFEND = 2
    HARASS = 3
    KILL_BUILDINGS = 4
    CHASE_BUILDINGS = 5
    ATTACK_NEAREST_BASE = 6
    REGROUP = 7

    def __repr__(self) -> str:
        return f"{self.name.capitalize()}"

for item in Orders:
    globals()[item.name] = item