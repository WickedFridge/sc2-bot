from typing import override

from bot.combat.micro_units.scouting_unit import MicroScoutingUnit
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroBanshee(MicroScoutingUnit):
    WEAPON_READY_THRESHOLD: int = 4

    @override
    async def heal_up(self, unit: Unit, local_units: Units):
        threats: Units = self.local_threats(unit)
        if (threats.amount == 0):
            await self.uncloak(unit)
        closest_mineral_line: Point2 = self.bot.expansions.closest_to(self.retreat_position).mineral_line
        unit.move(closest_mineral_line)

    async def cloak(self, banshee: Unit):
        available_abilities = (await self.bot.get_available_abilities([banshee]))[0]
        if (AbilityId.BEHAVIOR_CLOAKON_BANSHEE in available_abilities and banshee.energy >= 25):
            banshee(AbilityId.BEHAVIOR_CLOAKON_BANSHEE)

    async def uncloak(self, banshee: Unit):
        available_abilities = (await self.bot.get_available_abilities([banshee]))[0]
        if (AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE in available_abilities):
            banshee(AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE)

    def local_threats(self, banshee: Unit) -> Units:
        return self.enemy_all.filter(
            lambda enemy: (
                enemy.distance_to(banshee) < 20
                and enemy.can_attack_air
            )
        )
    
    @override
    async def fight(self, unit: Unit, local_units: Units, chase: bool = False):
        threats: Units = self.local_threats(unit)
        if (threats.amount >= 1):
            await self.cloak(unit)
        return await super().fight(unit, local_units, chase)

    @override
    async def retreat(self, unit: Unit, local_units: Units):
        threats: Units = self.local_threats(unit)
        if (threats.amount == 0):
            await self.uncloak(unit)
        return await super().retreat(unit, local_units)