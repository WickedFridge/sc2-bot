from typing import List, Optional
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

class Tech:
    building: UnitTypeId
    upgrade: UpgradeId | AbilityId
    requirements: List[UpgradeId | UnitTypeId]
    is_ability: bool

    def __init__(self, building: UnitTypeId, upgrade: UpgradeId, requirements: Optional[List[UpgradeId | UnitTypeId]] = [], is_ability: Optional[bool] = False) -> None:
        self.building = building
        self.upgrade = upgrade
        self.requirements = requirements
        self.is_ability = is_ability