from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


supply: dict = {}

# Terran Units
# creeps
supply[UnitTypeId.MULE] = 0
supply[UnitTypeId.AUTOTURRET] = 0
# Tier 1
supply[UnitTypeId.SCV] = 1
supply[UnitTypeId.MARINE] = 1
supply[UnitTypeId.REAPER] = 1
supply[UnitTypeId.MARAUDER] = 2
supply[UnitTypeId.HELLION] = 2
supply[UnitTypeId.WIDOWMINE] = 2
# Tier 2
supply[UnitTypeId.SIEGETANK] = 3
supply[UnitTypeId.CYCLONE] = 3
supply[UnitTypeId.MEDIVAC] = 2
supply[UnitTypeId.VIKING] = 2
supply[UnitTypeId.VIKINGASSAULT] = 2
supply[UnitTypeId.BANSHEE] = 3
supply[UnitTypeId.RAVEN] = 2
supply[UnitTypeId.LIBERATOR] = 3
# Tier 3
supply[UnitTypeId.GHOST] = 3
supply[UnitTypeId.THOR] = 6
supply[UnitTypeId.BATTLECRUISER] = 6


# Zerg units
# creeps
supply[UnitTypeId.EGG] = 0
supply[UnitTypeId.LARVA] = 0
supply[UnitTypeId.BROODLING] = 0
supply[UnitTypeId.SLAYNSWARMHOSTSPAWNFLYER] = 0
supply[UnitTypeId.LOCUSTMP] = 0
supply[UnitTypeId.CHANGELING] = 0
# Tier 1
supply[UnitTypeId.OVERLORD] = 0
supply[UnitTypeId.OVERSEER] = 0
supply[UnitTypeId.OVERLORDCOCOON] = 0
supply[UnitTypeId.DRONE] = 1
supply[UnitTypeId.ZERGLING] = 0.5
supply[UnitTypeId.ZERGLINGBURROWED] = 0.5
supply[UnitTypeId.BANELING] = 0.5
supply[UnitTypeId.BANELINGBURROWED] = 0.5
supply[UnitTypeId.BANELINGCOCOON] = 0.5
supply[UnitTypeId.QUEEN] = 2
supply[UnitTypeId.ROACH] = 2
supply[UnitTypeId.RAVAGER] = 3
# Tier 2
supply[UnitTypeId.HYDRALISK] = 2
supply[UnitTypeId.LURKER] = 3
supply[UnitTypeId.LURKERBURROWED] = 3
supply[UnitTypeId.LURKEREGG] = 3
supply[UnitTypeId.INFESTOR] = 2
supply[UnitTypeId.SWARMHOSTMP] = 3
supply[UnitTypeId.SWARMHOSTBURROWEDMP] = 3
supply[UnitTypeId.MUTALISK] = 2
supply[UnitTypeId.CORRUPTOR] = 2
# Tier 3
supply[UnitTypeId.BROODLORDEGG] = 4
supply[UnitTypeId.BROODLORD] = 4
supply[UnitTypeId.VIPER] = 3
supply[UnitTypeId.ULTRALISK] = 6


# Protoss Units
# Tier 1
supply[UnitTypeId.PROBE] = 1
supply[UnitTypeId.ZEALOT] = 2
supply[UnitTypeId.STALKER] = 2
supply[UnitTypeId.SENTRY] = 2
supply[UnitTypeId.ADEPT] = 2
# Tier 2
supply[UnitTypeId.HIGHTEMPLAR] = 2
supply[UnitTypeId.DARKTEMPLAR] = 2
supply[UnitTypeId.ARCHON] = 4
supply[UnitTypeId.OBSERVER] = 1
supply[UnitTypeId.WARPPRISM] = 2
supply[UnitTypeId.IMMORTAL] = 4
supply[UnitTypeId.PHOENIX] = 2
supply[UnitTypeId.ORACLE] = 3
supply[UnitTypeId.VOIDRAY] = 4
# Tier 3
supply[UnitTypeId.DISRUPTOR] = 4
supply[UnitTypeId.COLOSSUS] = 6
supply[UnitTypeId.TEMPEST] = 4
supply[UnitTypeId.CARRIER] = 6
supply[UnitTypeId.MOTHERSHIP] = 8

def units_supply(army: Units) -> float:
    army_supply: float = 0
    for unit in army:
        army_supply += supply[unit.type_id]
    return army_supply