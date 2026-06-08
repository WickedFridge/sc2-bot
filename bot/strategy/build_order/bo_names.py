import enum

class BuildOrderName(enum.Enum):
    KOKA_BUILD = 'Reaper_Expand_2/1/1_3cc'
    TWO_RAX_REAPERS_KOKABUILD = '2_Rax_Reapers_3cc_2/1/1'
    TWO_RAX_REAPERS_HELLBATS = '2_Rax_Reapers_3cc_Hellbat_push'
    DEFENSIVE_TWO_RAX = 'Defensive_2_Rax_Reapers'
    CONSERVATIVE_RAX_EXPAND = 'Conservative_Rax_Expand'
    DEFENSIVE_MISTRAL_211 = 'Defensive_Mistral_2/1/1'
    CC_FIRST_TWO_RAX = 'CC_First_2_Rax_Macro'
    MACRO_CYCLONE = 'Macro_Cyclone'
    DEFENSIVE_CYCLONE = 'Defensive_Cyclone'
    DEFENSIVE_CYCLONE_TANK = 'Defensive_Cyclone_Tank'
    CYCLONE_TANK_3RAX = 'Cyclone_Tank_3_Rax'
    DUMMY_BUILD = 'Dummy_Build'
    GREEDY_2_2_TIMING = 'Greedy_3CC_2/2_Timing'
    CYCLONE_3_RAVEN = 'Cyclone_3_Ravens'
    BANSHEESEBURGER = 'Bansheeseburger'

for item in BuildOrderName:
    globals()[item.name] = item