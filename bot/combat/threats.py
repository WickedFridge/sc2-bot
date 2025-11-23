import enum

class Threat(enum.Enum):
    NO_THREAT = 0
    ATTACK = 1
    WORKER_SCOUT = 2
    HARASS = 3
    CANON_RUSH = 4
    BUNKER_RUSH = 5
    UNKNOWN = 6
    OVERWHELMED = 7

    def __repr__(self) -> str:
        return f"{self.name.capitalize()}"

for item in Threat:
    globals()[item.name] = item