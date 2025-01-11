from typing import List, Optional
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

class Tech:
    building: UnitTypeId
    upgrade: UpgradeId | AbilityId
    requirements_ups: List[UpgradeId]
    requirements_buildings: List[UnitTypeId]
    is_ability: bool

    def __init__(self, building: UnitTypeId, upgrade: UpgradeId,
                 requirements_ups: Optional[List[UpgradeId]] = [],
                 requirements_buildings: Optional[List[UnitTypeId]] = [],
                 is_ability: Optional[bool] = False
            ) -> None:
        self.building = building
        self.upgrade = upgrade
        self.requirements_ups = requirements_ups
        self.requirements_buildings = requirements_buildings
        self.is_ability = is_ability