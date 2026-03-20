from typing import Optional, override

from bot.combat.micro_units.bio_unit import MicroBioUnit
from bot.combat.micro_units.micro_unit import MicroUnit
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.unit import Unit
from sc2.units import Units


class MicroGhost(MicroBioUnit):
    snipe_targets: dict[int, int] = {}
    emp_targets: dict[int, int] = {}
    stimmable: bool = False
    bonus_against_ground_light: bool = True
    bonus_against_air_light: bool = True

    def emp(self, ghost: Unit) -> bool:
        EMP_HIT_THRESHOLD: int = 50
        MAXIMUM_EMP_COUNT: int = 1
        
        potential_emp_targets: Units = self.get_local_enemy_units(ghost.position, 10, only_menacing=True).filter(
            lambda enemy_unit: (
                enemy_unit.energy + enemy_unit.shield > 0
                and (
                    enemy_unit.tag not in self.emp_targets
                    or self.emp_targets[enemy_unit.tag] < MAXIMUM_EMP_COUNT
                )
            )
        )
        if (potential_emp_targets.amount < 1):
            return False
        # find the best position to cast EMP
        best_target: Optional[Unit] = None
        best_hit: float = 0
        for enemy_unit in potential_emp_targets:
            hit: float = 0
            for unit in potential_emp_targets.closer_than(1.5, enemy_unit.position):
                hit += min(unit.shield, 100)
                hit += min(unit.energy, 100)
            if (hit > best_hit):
                best_hit = hit
                best_target = enemy_unit
        if (best_target and best_hit >= EMP_HIT_THRESHOLD):
            print("Casting EMP")
            ghost(AbilityId.EMP_EMP, best_target.position)
            if (best_target.tag in self.emp_targets):
                self.emp_targets[best_target.tag] += 1
            else:
                self.emp_targets[best_target.tag] = 1
            return True
        return False
    
    def snipe(self, ghost: Unit) -> bool:
        MAXIMUM_SNIPE_COUNT: int = 2
        # if we don't have energy or are already sniping, we just skip
        if (ghost.energy < 50 or ghost.is_using_ability(AbilityId.EFFECT_GHOSTSNIPE)):
            return False
        GHOST_SNIPE_THRESHOLD: int = 60
        potential_snipe_targets: Units = self.get_local_enemy_units(
            ghost.position,
            radius=10,
            only_menacing=True,
        ).filter(
            lambda enemy_unit: (
                enemy_unit.is_biological
                and enemy_unit.health + enemy_unit.shield >= GHOST_SNIPE_THRESHOLD
                and not enemy_unit.has_buff(BuffId.GHOSTSNIPEDOT)
                and (
                    enemy_unit.tag not in self.snipe_targets.keys()
                    or self.snipe_targets[enemy_unit.tag] < MAXIMUM_SNIPE_COUNT
                )
            )
        ).sorted(lambda enemy_unit: (enemy_unit.health + enemy_unit.shield))

        # if we don't have snipe targets, we skip
        if (potential_snipe_targets.amount == 0):
            return False
        target: Unit = potential_snipe_targets.first
        ghost(AbilityId.EFFECT_GHOSTSNIPE, target)
        if (target.tag in self.snipe_targets):
            self.snipe_targets[target.tag] += 1
        else:
            self.snipe_targets[target.tag] = 1
        return True
    
    @override
    async def fight(self, ghost: Unit, local_units: Units, chase: bool = False):
        if (self.emp(ghost)):
            return
        if (self.snipe(ghost)):
            return
        await super().fight(ghost, local_units)