from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class CaduceusReactor(Upgrade):
    upgrade = UpgradeId.MEDIVACCADUCEUSREACTOR
    building = UnitTypeId.FUSIONCORE
    ability = AbilityId.FUSIONCORERESEARCH_RESEARCHMEDIVACENERGYUPGRADE
    name = "Medivac Energy"