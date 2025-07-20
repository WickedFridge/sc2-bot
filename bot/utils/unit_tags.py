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
    UnitTypeId.DRONE,
    UnitTypeId.MULE
]
tower_types: List[UnitTypeId] = [
    UnitTypeId.PHOTONCANNON,
    UnitTypeId.BUNKER,
    UnitTypeId.PLANETARYFORTRESS,
    UnitTypeId.SPINECRAWLER,
    UnitTypeId.SPORECRAWLER,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.NYDUSCANAL,
    UnitTypeId.AUTOTURRET,
    UnitTypeId.PYLON,
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
    UnitTypeId.CREEPTUMOR,
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
    UnitTypeId.STARPORTTECHLAB,
    UnitTypeId.REACTOR,
    UnitTypeId.TECHLAB,
]
bio: List[UnitTypeId] = [
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER,
    UnitTypeId.GHOST,
]
bio_stimmable: List[UnitTypeId] = [
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER
]