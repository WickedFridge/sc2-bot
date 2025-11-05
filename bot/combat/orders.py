import enum

class Orders(enum.Enum):
    FIGHT_OFFENSE = 0
    FIGHT_DEFENSE = 1
    RETREAT = 2
    DEFEND = 3
    HARASS = 4
    KILL_BUILDINGS = 5
    CHASE_BUILDINGS = 6
    ATTACK_NEAREST_BASE = 7
    DEFEND_BUNKER_RUSH = 8
    DEFEND_CANON_RUSH = 9
    PICKUP_LEAVE = 10
    REGROUP = 11
    DROP = 12
    HEAL_UP = 13
    FIGHT_DISENGAGE = 14
    FIGHT_DROP = 15
    SCOUT = 16
    FIGHT_CHASE = 17

    def __repr__(self) -> str:
        return f"{self.name.capitalize()}"

for item in Orders:
    globals()[item.name] = item