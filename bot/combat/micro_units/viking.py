from typing import override

from bot.combat.micro_units.micro_unit import MicroUnit
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroViking(MicroUnit):
    bonus_against_air_armored: bool = True
    bonus_against_ground_mechanical: bool = True

    @override
    async def fight(self, viking: Unit, local_units: Units, chase: bool = False):
        # find a target
        potential_targets: Units = self.enemy_all.filter(
            lambda unit: (
                unit.can_be_attacked and (
                    unit.is_flying
                    or unit.type_id == UnitTypeId.COLOSSUS
                )
            )
        ).sorted(
            lambda unit: unit.health + unit.shield
        )
        # if our weapon isn't on cooldown
        if (viking.weapon_cooldown <= self.WEAPON_READY_THRESHOLD):
            enemy_in_range: Units = self.get_enemy_units_in_range(viking)
            if (enemy_in_range.amount >= 1):
                target: Unit = self.pick_best_target(enemy_in_range)
                viking.attack(target)
            elif (potential_targets.amount >= 1):
                viking.attack(potential_targets.closest_to(viking))
            else:
                # if (self.bot.scouting.known_enemy_army.flying_fighting_supply == 0):
                #     viking(AbilityId.MORPH_VIKINGASSAULTMODE)
                if (not self.safety_disengage(viking)):
                    viking.move(local_units.center)

        # if we're not on cooldown, either disengage or keep attacking
        elif (not self.safety_disengage(viking)):
            threats: Units = self.enemies_threatening_air_in_range(viking, safety_distance=2, range_override=20)
            if (threats.amount == 0 and potential_targets.amount >= 1):
                best_attacking_spot: Point2 = self.bot.map.influence_maps.best_attacking_spot(viking, potential_targets.closest_to(viking), risk=0.5)
                viking.move(best_attacking_spot)
            else:
                viking.move(local_units.center)

    @override
    async def harass(self, unit: Unit, local_units: Units, workers: Units):
        unit.move(local_units.center)
    
    @override
    async def retreat(self, viking: Unit, local_units: Units):
        if (viking.weapon_cooldown > self.WEAPON_READY_THRESHOLD):
            await super().retreat(viking, local_units)
            return

        # find a target if our weapon isn't on cooldown
        enemy_in_range: Units = self.get_enemy_units_in_range(viking)
        if (enemy_in_range.amount >= 1):
            target: Unit = self.pick_best_target(enemy_in_range)
            viking.attack(target)
        else:
            await super().retreat(viking, local_units)