from typing import List, override

from bot.combat.micro_units.micro_unit import MicroUnit
from bot.utils.unit_supply import get_unit_supply
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroThor(MicroUnit):
    bonus_against_air_massive: bool = True
    bonus_against_air_light: bool = True
    WEAPON_READY_THRESHOLD: int = 8
    WEAPON_DURATION_COOLDOWN: int = 40

    async def thor_switch_mode(self, thor: Unit):
        available_abilities = (await self.bot.get_available_abilities([thor]))[0]
        enemy_flying_units: Units = self.bot.scouting.known_enemy_army.units.filter(lambda unit: unit.is_flying)
        air_supply: int = 0
        light_air_supply: int = 0
        for flyer in enemy_flying_units:
            supply: int = get_unit_supply(flyer.type_id)
            air_supply += supply
            if (flyer.is_light):
                light_air_supply += supply

        if (light_air_supply > 0.5 * air_supply):
            if (AbilityId.MORPH_THOREXPLOSIVEMODE in available_abilities):
                thor(AbilityId.MORPH_THOREXPLOSIVEMODE)
                return
        else:
            if (AbilityId.MORPH_THORHIGHIMPACTMODE in available_abilities):
                thor(AbilityId.MORPH_THORHIGHIMPACTMODE)
                return
            
    @override
    async def fight(self, thor: Unit, local_units: Units, chase: bool = False):
        local_enemies: Units = self.get_local_enemy_units(thor.position, only_menacing=True).sorted(
            lambda unit: (not unit.is_massive, unit.health + unit.shield)
        )
        if (local_enemies.amount == 0):
            thor.move(local_units.center)
            return
        
        # Switch to super air mode if opponent has mostly massive aerial stuff
        local_flying_units: Units = local_enemies.filter(lambda unit: unit.is_flying)
        if (local_flying_units.amount >= 1):
            await self.thor_switch_mode(thor)
        
        # find a target if our weapon isn't on cooldown
        print(f'thor weapon cooldown : {thor.weapon_cooldown}')
        if (thor.weapon_cooldown <= self.WEAPON_READY_THRESHOLD or thor.weapon_cooldown >= self.WEAPON_DURATION_COOLDOWN):
            enemy_in_range: Units = local_enemies.filter(
                lambda unit: thor.target_in_range(unit)
            )
            if (enemy_in_range.amount >= 1):
                if (thor.is_attacking and thor.orders[0].target in enemy_in_range.tags):
                    # keep attacking
                    return
                thor.attack(enemy_in_range.first)
            else:
                best_position: Point2 = self.bot.map.influence_maps.best_attacking_spot(thor, local_enemies.closest_to(thor), risk=0.3 * thor.health_percentage)
                thor.move(best_position)
        else:
            best_position: Point2 = self.bot.map.influence_maps.best_attacking_spot(thor, local_enemies.closest_to(thor), risk=0.3 * thor.health_percentage)
            thor.move(best_position)

    @override
    async def retreat(self, thor: Unit, local_units: Units):
        await self.thor_switch_mode(thor)
        await super().retreat(thor, local_units)