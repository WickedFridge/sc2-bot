from typing import override

from bot.combat.micro_units.scouting_unit import MicroScoutingUnit
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroReaper(MicroScoutingUnit):
    async def reaper_grenade(self, reaper: Unit) -> bool:
        available_abilities = (await self.bot.get_available_abilities([reaper]))[0]
        if (AbilityId.KD8CHARGE_KD8CHARGE not in available_abilities):
            return False
        
        # best_target, score = self.bot.map.influence_maps.best_grenade_target(reaper)
        # if (score < 5):
        #     return False
        KD8_RANGE: int = 5
        potential_targets: Units = self.enemy_all.filter(
            lambda enemy_unit: (
                not enemy_unit.is_flying
                and enemy_unit.distance_to(reaper) <= KD8_RANGE + enemy_unit.radius + reaper.radius
            )
        ).sorted(
            lambda enemy_unit: (enemy_unit.health + enemy_unit.shield)
        )
        if (potential_targets.amount == 0):
            return False
        best_target: Point2 = potential_targets.first.position
        reaper(AbilityId.KD8CHARGE_KD8CHARGE, best_target)
        return True
    
    @override
    async def fight(self, reaper: Unit, local_units: Units, chase: bool = False):
        # Try grenade first
        if (await self.reaper_grenade(reaper)):
            return
        await super().fight(reaper, local_units, chase)

    @override
    async def harass(self, unit: Unit, local_units: Units, workers: Units):
        if (not await self.reaper_grenade(unit)):
            await super().harass(unit, local_units, workers)
        
        