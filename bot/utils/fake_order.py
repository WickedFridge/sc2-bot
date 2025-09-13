from sc2.game_data import AbilityData
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import UnitOrder


class FakeAbilityData(AbilityData):
    _ability_id: AbilityId

    def __init__(self, id: AbilityId):
        self._ability_id = id

    @property
    def id(self) -> int:
        return self._ability_id

    @property
    def exact_id(self) -> AbilityId:
        return self._ability_id

    @property
    def link_name(self) -> str:
        return f"Fake {self._ability_id.name}"

    @property
    def button_name(self) -> str:
        return f"Fake {self._ability_id.name}"

    @property
    def remaps_to_ability_id(self) -> bool:
        return False

class FakeOrder(UnitOrder):
    ability: AbilityData
    target: None
    progress: float = 0

    def __init__(self, ability_id: AbilityId):
        self.ability = FakeAbilityData(ability_id)

    # in case some code calls .to_dict() or similar
    def __repr__(self) -> str:
        return f"<FakeOrder {self.ability.id}>"