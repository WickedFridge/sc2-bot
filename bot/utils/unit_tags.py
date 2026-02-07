from typing import List

from sc2.ids.unit_typeid import UnitTypeId

hq_types: List[UnitTypeId] = [
    UnitTypeId.COMMANDCENTER,
    UnitTypeId.ORBITALCOMMAND,
    UnitTypeId.PLANETARYFORTRESS,
    UnitTypeId.HATCHERY,
    UnitTypeId.LAIR,
    UnitTypeId.HIVE,
    UnitTypeId.NEXUS
]

zerg_townhalls: List[UnitTypeId] = [
    UnitTypeId.HATCHERY,
    UnitTypeId.LAIR,
    UnitTypeId.HIVE,
]

must_repair: List[UnitTypeId] = [
    UnitTypeId.PLANETARYFORTRESS,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.BUNKER,
    UnitTypeId.SUPPLYDEPOT
]
worker_types: List[UnitTypeId] = [
    UnitTypeId.SCV,
    UnitTypeId.PROBE,
    UnitTypeId.DRONE,
    UnitTypeId.MULE
]
tower_types: List[UnitTypeId] = [
    UnitTypeId.PHOTONCANNON,
    UnitTypeId.SHIELDBATTERY,
    UnitTypeId.BUNKER,
    UnitTypeId.PLANETARYFORTRESS,
    UnitTypeId.SPINECRAWLER,
    UnitTypeId.SPORECRAWLER,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.NYDUSCANAL,
    UnitTypeId.AUTOTURRET,
]
menacing: List[UnitTypeId] = [
    UnitTypeId.WIDOWMINE,
    UnitTypeId.WIDOWMINEBURROWED,
    UnitTypeId.MEDIVAC,
    UnitTypeId.RAVEN,
    UnitTypeId.BANELING,
    UnitTypeId.BANELINGCOCOON,
    UnitTypeId.BANELINGBURROWED,
    UnitTypeId.ZERGLINGBURROWED,
    UnitTypeId.ROACHBURROWED,
    UnitTypeId.INFESTOR,
    UnitTypeId.INFESTORBURROWED,
    UnitTypeId.SWARMHOSTMP,
    UnitTypeId.SWARMHOSTBURROWEDMP,
    UnitTypeId.LURKER,
    UnitTypeId.VIPER,
    UnitTypeId.CARRIER,
    UnitTypeId.DISRUPTORPHASED,
    UnitTypeId.WARPPRISM,
]
dont_attack: List[UnitTypeId] = [
    UnitTypeId.EGG,
    UnitTypeId.LARVA,
    UnitTypeId.INTERCEPTOR
]
add_ons: List[UnitTypeId] = [
    UnitTypeId.BARRACKSREACTOR,
    UnitTypeId.BARRACKSTECHLAB,
    UnitTypeId.FACTORYREACTOR,
    UnitTypeId.FACTORYTECHLAB,
    UnitTypeId.STARPORTREACTOR,
    UnitTypeId.STARPORTTECHLAB,
    UnitTypeId.REACTOR,
    UnitTypeId.TECHLAB,
    UnitTypeId.TECHREACTOR,
]
bio: List[UnitTypeId] = [
    UnitTypeId.REAPER,
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER,
    UnitTypeId.GHOST,
]
bio_stimmable: List[UnitTypeId] = [
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER
]
building_priorities: List[UnitTypeId] = [
    UnitTypeId.COMMANDCENTER,
    UnitTypeId.ORBITALCOMMAND,
    UnitTypeId.PLANETARYFORTRESS,
    UnitTypeId.HATCHERY,
    UnitTypeId.LAIR,
    UnitTypeId.HIVE,
    UnitTypeId.NEXUS,
    UnitTypeId.PYLON,
    UnitTypeId.ENGINEERINGBAY,
    UnitTypeId.EVOLUTIONCHAMBER,
    UnitTypeId.FORGE
]
burrowed_units: List[UnitTypeId] = [
    UnitTypeId.QUEENBURROWED,
    UnitTypeId.DRONEBURROWED,
    UnitTypeId.ZERGLINGBURROWED,
    UnitTypeId.BANELINGBURROWED,
    UnitTypeId.ROACHBURROWED,
    UnitTypeId.RAVAGERBURROWED,
    UnitTypeId.HYDRALISKBURROWED,
    UnitTypeId.LURKER,
    UnitTypeId.LURKERMP,
    UnitTypeId.LURKERBURROWED,
    UnitTypeId.INFESTORBURROWED,
    UnitTypeId.SWARMHOSTBURROWEDMP,
    UnitTypeId.ULTRALISKBURROWED,
]
cloaked_units: List[UnitTypeId] = [
    UnitTypeId.GHOST,
    # This one is visible
    # UnitTypeId.WIDOWMINE,
    UnitTypeId.WIDOWMINEBURROWED,
    UnitTypeId.BANSHEE,
    # These shouldn't trigger detection on their own
    # UnitTypeId.OBSERVER,
    # UnitTypeId.OBSERVERSIEGEMODE,
    UnitTypeId.DARKTEMPLAR,
]
friendly_fire: List[UnitTypeId] = [
    UnitTypeId.WIDOWMINE,
    UnitTypeId.SIEGETANK,
]
build_order_structures: List[UnitTypeId] = [
    UnitTypeId.REFINERY,
    UnitTypeId.COMMANDCENTER,
    UnitTypeId.BARRACKS,
    UnitTypeId.FACTORY,
    UnitTypeId.STARPORT,
    UnitTypeId.ENGINEERINGBAY,
    UnitTypeId.ARMORY,
    UnitTypeId.BARRACKSTECHLAB,
    UnitTypeId.BARRACKSREACTOR,
    UnitTypeId.FACTORYREACTOR,
]
creep: List[UnitTypeId] = [
    UnitTypeId.CREEPTUMOR,
    UnitTypeId.CREEPTUMORQUEEN,
    UnitTypeId.CREEPTUMORBURROWED,
]
production: List[UnitTypeId] = [
    UnitTypeId.BARRACKS,
    UnitTypeId.FACTORY,
    UnitTypeId.STARPORT,
]
production_flying: List[UnitTypeId] = [
    UnitTypeId.BARRACKSFLYING,
    UnitTypeId.FACTORYFLYING,
    UnitTypeId.STARPORTFLYING,
]
important_buildings: List[UnitTypeId] = [
    UnitTypeId.COMMANDCENTER,
    UnitTypeId.BUNKER,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.SUPPLYDEPOT,
]
flying_units: list[UnitTypeId] = [
    # Terran
    UnitTypeId.VIKING,
    UnitTypeId.MEDIVAC,
    UnitTypeId.LIBERATOR,
    UnitTypeId.RAVEN,
    UnitTypeId.BANSHEE,
    UnitTypeId.BATTLECRUISER,
    # Zerg
    UnitTypeId.MUTALISK,
    UnitTypeId.CORRUPTOR,
    UnitTypeId.VIPER,
    UnitTypeId.BROODLORD,
    # Protoss
    UnitTypeId.PHOENIX,
    UnitTypeId.VOIDRAY,
    UnitTypeId.ORACLE,
    UnitTypeId.CARRIER,
    UnitTypeId.TEMPEST,
    UnitTypeId.MOTHERSHIP,
    UnitTypeId.COLOSSUS,
]