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
    UnitTypeId.CARRIER,
    UnitTypeId.SENTRY,
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
    UnitTypeId.WIDOWMINE,
    UnitTypeId.WIDOWMINEBURROWED,
    UnitTypeId.BANSHEE,
    UnitTypeId.OBSERVER,
    UnitTypeId.OBSERVERSIEGEMODE,
    UnitTypeId.DARKTEMPLAR,
]