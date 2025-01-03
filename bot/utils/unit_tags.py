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

must_repair: List[UnitTypeId] = [
    UnitTypeId.COMMANDCENTER,
    UnitTypeId.ORBITALCOMMAND,
    UnitTypeId.PLANETARYFORTRESS,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.BUNKER
]
worker_types: List[UnitTypeId] = [
    UnitTypeId.SCV,
    UnitTypeId.PROBE,
    UnitTypeId.DRONE
]
tower_types: List[UnitTypeId] = [
    UnitTypeId.PHOTONCANNON,
    UnitTypeId.BUNKER,
    UnitTypeId.SPINECRAWLER,
    UnitTypeId.SPORECRAWLER,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.NYDUSCANAL
]
menacing: List[UnitTypeId] = [
    UnitTypeId.WIDOWMINE,
    UnitTypeId.MEDIVAC,
    UnitTypeId.RAVEN,
    UnitTypeId.BANELING,
    UnitTypeId.BANELINGCOCOON,
    UnitTypeId.BANELINGBURROWED,
    UnitTypeId.INFESTOR,
    UnitTypeId.INFESTORBURROWED,
    UnitTypeId.SWARMHOSTMP,
    UnitTypeId.SWARMHOSTBURROWEDMP,
    UnitTypeId.LURKER,
    UnitTypeId.VIPER,
]
dont_attack: List[UnitTypeId] = [
    UnitTypeId.EGG,
    UnitTypeId.LARVA
]
add_ons: List[UnitTypeId] = [
    UnitTypeId.BARRACKSREACTOR,
    UnitTypeId.BARRACKSTECHLAB,
    UnitTypeId.FACTORYREACTOR,
    UnitTypeId.FACTORYTECHLAB,
    UnitTypeId.STARPORTREACTOR,
    UnitTypeId.STARPORTTECHLAB
]
bio: List[UnitTypeId] = [
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER
]