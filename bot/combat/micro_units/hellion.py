from typing import override

from bot.combat.micro_units.scouting_unit import MicroScoutingUnit
from bot.utils.army import Army
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroHellion(MicroScoutingUnit):
    WEAPON_READY_THRESHOLD: int = 8
    bonus_against_ground_light: bool = True

    @override
    async def fight(self, unit: Unit, local_units: Units, chase: bool = False):
        if (not chase and local_units(UnitTypeId.MEDIVAC).amount >= 1):
            unit(AbilityId.MORPH_HELLBAT)
        await super().fight(unit, local_units, chase)

    @override
    async def kill_buildings(self, unit: Unit, local_units: Units, enemy_buildings: Units):
        if (local_units(UnitTypeId.MEDIVAC).amount >= 1):
            unit(AbilityId.MORPH_HELLBAT)
        await super().kill_buildings(unit, local_units, enemy_buildings)
    
    @override
    async def attack_nearest_base(self, unit: Unit, army: Army, target: Point2):
        if (army.units(UnitTypeId.MEDIVAC).amount >= 1):
            unit(AbilityId.MORPH_HELLBAT)
        await super().attack_nearest_base(unit, army, target)

    @override
    async def chase_buildings(self, unit: Unit, army: Army, target: Point2):
        if (army.units(UnitTypeId.MEDIVAC).amount >= 1):
            unit(AbilityId.MORPH_HELLBAT)
        await super().chase_buildings(unit, army, target)
    
    @override
    async def retreat(self, unit: Unit, local_units: Units):
        if (local_units(UnitTypeId.MEDIVAC).amount >= 1):
            unit(AbilityId.MORPH_HELLBAT)
        await super().retreat(unit, local_units)