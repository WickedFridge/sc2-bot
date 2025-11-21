import enum

class BuildOrderName(enum.Enum):
    KOKA_BUILD = 'Reaper Expand 2/1/1 3cc'
    TWO_RAX_REAPERS = '2 Rax Reapers Macro'
    DUMMY_BUILD = 'Dummy Build'

for item in BuildOrderName:
    globals()[item.name] = item