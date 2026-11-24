from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId

LIFT_ABILITY: dict[UnitTypeId, AbilityId] = {
    UnitTypeId.BARRACKS: AbilityId.LIFT_BARRACKS,
    UnitTypeId.FACTORY: AbilityId.LIFT_FACTORY,
    UnitTypeId.STARPORT: AbilityId.LIFT_STARPORT,
}

# Orders of a production building that is building an addon (the real in-game
# orders, plus the morph abilities used by FakeOrder in the same frame).
ADDON_BUILD_ABILITIES: set[AbilityId] = {
    AbilityId.BUILD_TECHLAB,
    AbilityId.BUILD_REACTOR,
    AbilityId.BUILD_TECHLAB_BARRACKS,
    AbilityId.BUILD_REACTOR_BARRACKS,
    AbilityId.BUILD_TECHLAB_FACTORY,
    AbilityId.BUILD_REACTOR_FACTORY,
    AbilityId.BUILD_TECHLAB_STARPORT,
    AbilityId.BUILD_REACTOR_STARPORT,
    AbilityId.BARRACKSTECHLABMORPH_TECHLABBARRACKS,
    AbilityId.FACTORYTECHLABMORPH_TECHLABFACTORY,
    AbilityId.STARPORTTECHLABMORPH_TECHLABSTARPORT,
    AbilityId.BARRACKSREACTORMORPH_REACTOR,
    AbilityId.FACTORYREACTORMORPH_REACTOR,
    AbilityId.STARPORTREACTORMORPH_REACTOR,
}