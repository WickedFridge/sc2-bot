from sc2.ids.unit_typeid import UnitTypeId


building_cargo: dict[UnitTypeId, int] = {
    UnitTypeId.SCV: 1,
    UnitTypeId.MARINE: 1,
    UnitTypeId.REAPER: 1,
    UnitTypeId.MARAUDER: 2,
    UnitTypeId.GHOST: 2,
}
transport_cargo: dict[UnitTypeId, int] = {
    UnitTypeId.SCV: 1,
    UnitTypeId.MARINE: 1,
    UnitTypeId.REAPER: 1,
    UnitTypeId.MARAUDER: 2,
    UnitTypeId.GHOST: 2,
    UnitTypeId.HELLION: 2,
    UnitTypeId.WIDOWMINE: 2,
    UnitTypeId.CYCLONE: 4,
    UnitTypeId.HELLIONTANK: 4,
    UnitTypeId.SIEGETANK: 4,
    UnitTypeId.THOR: 8,
}


def get_building_cargo(unit_type: UnitTypeId) -> int:
    return building_cargo.get(unit_type, 0)

def get_transport_cargo(unit_type: UnitTypeId) -> int:
    return transport_cargo.get(unit_type, 0)