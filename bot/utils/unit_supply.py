import math
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


supply: dict[UnitTypeId, int] = {}

# Terran Units
# creeps
supply[UnitTypeId.MULE] = 0
supply[UnitTypeId.AUTOTURRET] = 2
supply[UnitTypeId.MISSILETURRET] = 0
supply[UnitTypeId.BUNKER] = 8
supply[UnitTypeId.PLANETARYFORTRESS] = 20
supply[UnitTypeId.NUKE] = 50
# Tier 1
supply[UnitTypeId.SCV] = 1
supply[UnitTypeId.MARINE] = 1
supply[UnitTypeId.REAPER] = 1
supply[UnitTypeId.MARAUDER] = 2
supply[UnitTypeId.HELLION] = 2
supply[UnitTypeId.HELLIONTANK] = 2
supply[UnitTypeId.WIDOWMINE] = 2
supply[UnitTypeId.WIDOWMINEBURROWED] = 2
# Tier 2
supply[UnitTypeId.SIEGETANK] = 2
supply[UnitTypeId.SIEGETANKSIEGED] = 5
supply[UnitTypeId.CYCLONE] = 3
supply[UnitTypeId.MEDIVAC] = 2
supply[UnitTypeId.VIKING] = 2
supply[UnitTypeId.VIKINGFIGHTER] = 3
supply[UnitTypeId.VIKINGASSAULT] = 2
supply[UnitTypeId.BANSHEE] = 3
supply[UnitTypeId.RAVEN] = 2
supply[UnitTypeId.LIBERATOR] = 3
supply[UnitTypeId.LIBERATORAG] = 5
# Tier 3
supply[UnitTypeId.GHOST] = 3
supply[UnitTypeId.THOR] = 6
supply[UnitTypeId.THORAP] = 6
supply[UnitTypeId.BATTLECRUISER] = 6


# Zerg units
# creeps
supply[UnitTypeId.EGG] = 0
supply[UnitTypeId.LARVA] = 0
supply[UnitTypeId.BROODLING] = 0.5
supply[UnitTypeId.SLAYNSWARMHOSTSPAWNFLYER] = 0
supply[UnitTypeId.LOCUSTMPFLYING] = 0
supply[UnitTypeId.LOCUSTMP] = 2
supply[UnitTypeId.CHANGELING] = 0
supply[UnitTypeId.CHANGELINGMARINE] = 0
supply[UnitTypeId.CHANGELINGMARINESHIELD] = 0
supply[UnitTypeId.CHANGELINGZEALOT] = 0
supply[UnitTypeId.CHANGELINGZERGLING] = 0
supply[UnitTypeId.CHANGELINGZERGLINGWINGS] = 0
supply[UnitTypeId.SPORECRAWLER] = 0
supply[UnitTypeId.SPINECRAWLER] = 3
# Tier 1
supply[UnitTypeId.OVERLORD] = 0
supply[UnitTypeId.OVERSEER] = 0
supply[UnitTypeId.OVERLORDCOCOON] = 0
supply[UnitTypeId.OVERLORDTRANSPORT] = 0
supply[UnitTypeId.TRANSPORTOVERLORDCOCOON] = 0
supply[UnitTypeId.DRONE] = 1
supply[UnitTypeId.DRONEBURROWED] = 1
supply[UnitTypeId.ZERGLING] = 0.5
supply[UnitTypeId.ZERGLINGBURROWED] = 0.5
supply[UnitTypeId.BANELING] = 0.5
supply[UnitTypeId.BANELINGBURROWED] = 0.5
supply[UnitTypeId.BANELINGCOCOON] = 0
supply[UnitTypeId.QUEEN] = 2
supply[UnitTypeId.QUEENBURROWED] = 2
supply[UnitTypeId.ROACH] = 2
supply[UnitTypeId.ROACHBURROWED] = 2
supply[UnitTypeId.RAVAGER] = 3
supply[UnitTypeId.RAVAGERBURROWED] = 3
supply[UnitTypeId.RAVAGERCOCOON] = 0
# Tier 2
supply[UnitTypeId.HYDRALISK] = 2
supply[UnitTypeId.HYDRALISKBURROWED] = 2
supply[UnitTypeId.LURKER] = 3
supply[UnitTypeId.LURKERMP] = 3
supply[UnitTypeId.LURKERMPBURROWED] = 3
supply[UnitTypeId.LURKERBURROWED] = 3
supply[UnitTypeId.LURKEREGG] = 3
supply[UnitTypeId.LURKERMPEGG] = 0
supply[UnitTypeId.INFESTOR] = 2
supply[UnitTypeId.INFESTORBURROWED] = 2
supply[UnitTypeId.SWARMHOSTMP] = 3
supply[UnitTypeId.SWARMHOSTBURROWEDMP] = 3
supply[UnitTypeId.MUTALISK] = 2
supply[UnitTypeId.CORRUPTOR] = 2
# Tier 3
supply[UnitTypeId.BROODLORDEGG] = 0
supply[UnitTypeId.BROODLORD] = 4
supply[UnitTypeId.BROODLORDCOCOON] = 0
supply[UnitTypeId.VIPER] = 3
supply[UnitTypeId.ULTRALISK] = 6
supply[UnitTypeId.ULTRALISKBURROWED] = 6


# Protoss Units
# creeps
supply[UnitTypeId.ADEPTPHASESHIFT] = 0
supply[UnitTypeId.INTERCEPTOR] = 1
supply[UnitTypeId.PHOTONCANNON] = 3

# Tier 1
supply[UnitTypeId.PROBE] = 1
supply[UnitTypeId.ZEALOT] = 2
supply[UnitTypeId.STALKER] = 3
supply[UnitTypeId.SENTRY] = 2
supply[UnitTypeId.ADEPT] = 2
# Tier 2
supply[UnitTypeId.HIGHTEMPLAR] = 2
supply[UnitTypeId.DARKTEMPLAR] = 2
supply[UnitTypeId.ARCHON] = 4
supply[UnitTypeId.OBSERVER] = 0
supply[UnitTypeId.OBSERVERSIEGEMODE] = 0
supply[UnitTypeId.WARPPRISM] = 2
supply[UnitTypeId.WARPPRISMPHASING] = 2
supply[UnitTypeId.IMMORTAL] = 4
supply[UnitTypeId.PHOENIX] = 2
supply[UnitTypeId.ORACLE] = 3
supply[UnitTypeId.VOIDRAY] = 4
# Tier 3
supply[UnitTypeId.DISRUPTOR] = 4
supply[UnitTypeId.DISRUPTORPHASED] = 4
supply[UnitTypeId.COLOSSUS] = 6
supply[UnitTypeId.TEMPEST] = 4
supply[UnitTypeId.CARRIER] = 6
supply[UnitTypeId.MOTHERSHIP] = 8

def get_unit_supply(unit_type: UnitTypeId) -> int:
    return supply.get(unit_type, 0)

def get_units_supply(army: Units) -> float:
    army_supply: float = 0
    for unit in army:
        if (unit.type_id == UnitTypeId.BUNKER):
            supply: int = 0
            for passenger in unit.passengers:
                supply += get_unit_supply(passenger.type_id)
            army_supply += supply
        else:
            army_supply += get_unit_supply(unit.type_id)
    return army_supply

def weighted_units_supply(units: Units) -> float:
    army_supply: float = 0
    for unit in units:
        health_percentage: float = 1 if not unit.health_max else (unit.health + unit.shield) / (unit.health_max + unit.shield_max)
        health_ratio: float = (1 - math.cos(math.pi * health_percentage)) / 2
        energy_percentage: float = 1 if not unit.energy_percentage else unit.energy_percentage
        energy_ratio: float = 1 if energy_percentage > 0.5 else (1 - math.cos(2 * math.pi * energy_percentage)) / 2
        if (unit.can_attack or unit.energy_max == 0):
            army_supply += supply[unit.type_id] * health_ratio
        else:
            army_supply += supply[unit.type_id] * energy_ratio
    return army_supply