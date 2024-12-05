from typing import List

from sc2.ids.unit_typeid import UnitTypeId

hq_types: List[int] = [
    UnitTypeId.COMMANDCENTER,
    UnitTypeId.ORBITALCOMMAND,
    UnitTypeId.PLANETARYFORTRESS,
    UnitTypeId.HATCHERY,
    UnitTypeId.LAIR,
    UnitTypeId.HIVE,
    UnitTypeId.NEXUS
]
worker_types: List[int] = [
    UnitTypeId.SCV,
    UnitTypeId.PROBE,
    UnitTypeId.DRONE
]
tower_types: List[int] = [
    UnitTypeId.PHOTONCANNON,
    UnitTypeId.BUNKER,
    UnitTypeId.SPINECRAWLER,
    UnitTypeId.SPORECRAWLER,
    UnitTypeId.MISSILETURRET
]
dont_attack: List[int] = [
    UnitTypeId.EGG,
    UnitTypeId.LARVA
]
add_ons: List[int] = [
    UnitTypeId.BARRACKSREACTOR,
    UnitTypeId.BARRACKSTECHLAB,
    UnitTypeId.FACTORYREACTOR,
    UnitTypeId.FACTORYTECHLAB,
    UnitTypeId.STARPORTREACTOR,
    UnitTypeId.STARPORTTECHLAB
]