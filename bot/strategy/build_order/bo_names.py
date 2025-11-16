import enum

class BuildOrderName(enum.Enum):
    KOKA_BUILD = 0
    TWO_RAX_REAPERS = 1

    def __repr__(self) -> str:
        return f"{self.name.capitalize()}"

for item in BuildOrderName:
    globals()[item.name] = item