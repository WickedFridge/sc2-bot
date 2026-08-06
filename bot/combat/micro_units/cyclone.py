import math
from typing import Optional, override

from bot.combat.micro_units.micro_unit import MicroUnit
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroCyclone(MicroUnit):
    cyclone_locks: dict[int, int] = {}
    LOCKON_KEEP_RANGE: int = 15

    def _acquire_lock(self, cyclone: Unit, local_enemies: Units, total_range: float) -> bool:
        # look for potential targets, prioritize in range, then lowest health
        print("looking for a lock target")
        possible_targets: Units = local_enemies.sorted(
            key=lambda enemy_unit: (
                enemy_unit.distance_to(cyclone) > total_range,   # False (in range) before True
                -(enemy_unit.health + enemy_unit.shield),        # more total hp first
                -enemy_unit.shield,                              # more shield first
                enemy_unit.distance_to(cyclone)                  # closer first
            )
        )
        if (possible_targets.amount == 0):
            return False
        target: Unit = possible_targets.first
        print(f"Locking on to {target.type_id}")
        cyclone(AbilityId.LOCKON_LOCKON, target)
        self.cyclone_locks[cyclone.tag] = target.tag
        return True

    def _retreat_to_safest_spot(self, cyclone: Unit):
        safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(cyclone)
        cyclone.move(safest_spot)

    def _fight_on_lock_cooldown(self, cyclone: Unit, enemies_in_range: Units, local_enemies: Units):
        # if we have locked onto a target, stay in range and find the safest spot to kite around it
        target_tag: int = self.cyclone_locks.get(cyclone.tag, None)
        target: Unit = self.bot.enemy_units.find_by_tag(target_tag) if target_tag else None

        if (target):
            safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(target, self.LOCKON_KEEP_RANGE - target.real_speed / 2)
            cyclone.move(safest_spot)
            return

        if (enemies_in_range.amount >= 1):
            self.hit_n_run(cyclone, enemies_in_range)
            return

        if (local_enemies.amount >= 1 and cyclone.health_percentage >= 0.9):
            self.hit_n_run(cyclone, local_enemies)
            return

        self._retreat_to_safest_spot(cyclone)

    @override
    async def fight(self, cyclone: Unit, local_units: Units, chase: bool = False):
        LOCKON_RANGE: int = 7
        total_range: float = LOCKON_RANGE + cyclone.radius
        local_enemies: Units = self.get_local_enemy_units(cyclone.position, only_menacing=True)

        if (cyclone.is_using_ability(AbilityId.LOCKON_LOCKON)):
            target_tag: int = cyclone.orders[0].target
            target: Unit = self.bot.enemy_units.find_by_tag(target_tag)

            if (target and cyclone.distance_to(target) <= total_range):
                self.cyclone_locks[cyclone.tag] = target.tag
                return

            if (self._acquire_lock(cyclone, local_enemies, total_range)):
                return

        enemies_in_range: Units = self.get_enemy_units_in_range(cyclone)
        available_abilities = (await self.bot.get_available_abilities([cyclone]))[0]

        if (AbilityId.LOCKON_LOCKON not in available_abilities):
            self._fight_on_lock_cooldown(cyclone, enemies_in_range, local_enemies)
            return

        # else if we have the lock off cooldown
        if (local_enemies.amount == 0):
            self._retreat_to_safest_spot(cyclone)
            return

        self._acquire_lock(cyclone, local_enemies, total_range)