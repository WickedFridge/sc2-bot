from typing import override

from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class BlueFlame(Upgrade):
    upgrade = UpgradeId.INFERNALPREIGNITERS
    building = UnitTypeId.FACTORYTECHLAB
    ability = AbilityId.RESEARCH_INFERNALPREIGNITER
    name = "Blue Flame"
    is_ability: bool = True

    @property
    @override
    def custom_conditions(self) -> bool:
        hellion_count: int = (
            self.bot.units([UnitTypeId.HELLION, UnitTypeId.HELLIONTANK]).amount
            + self.bot.already_pending(UnitTypeId.HELLION)
        )
        target_hellion_count: int = self.bot.composition_manager.amount_to_train(UnitTypeId.HELLION)
        return max(hellion_count, target_hellion_count) >= 7