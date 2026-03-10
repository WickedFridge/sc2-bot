from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId

LIFT_ABILITY: dict[UnitTypeId, AbilityId] = {
    UnitTypeId.BARRACKS: AbilityId.LIFT_BARRACKS,
    UnitTypeId.FACTORY: AbilityId.LIFT_FACTORY,
    UnitTypeId.STARPORT: AbilityId.LIFT_STARPORT,
}