from typing import List

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId

AbilityBuild: List[AbilityId] = [
    AbilityId.TERRANBUILD_ARMORY,
    AbilityId.TERRANBUILD_BARRACKS,
    AbilityId.TERRANBUILD_BUNKER,
    AbilityId.TERRANBUILD_COMMANDCENTER,
    AbilityId.TERRANBUILD_ENGINEERINGBAY,
    AbilityId.TERRANBUILD_FACTORY,
    AbilityId.TERRANBUILD_FUSIONCORE,
    AbilityId.TERRANBUILD_GHOSTACADEMY,
    AbilityId.TERRANBUILD_MISSILETURRET,
    AbilityId.TERRANBUILD_REFINERY,
    AbilityId.TERRANBUILD_SENSORTOWER,
    AbilityId.TERRANBUILD_STARPORT,
    AbilityId.TERRANBUILD_SUPPLYDEPOT,
]

AbilityRepair: List[AbilityId] = [
    AbilityId.EFFECT_REPAIR,
    AbilityId.EFFECT_REPAIR_SCV,
    AbilityId.EFFECT_REPAIR_MULE,
]