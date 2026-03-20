import math
from typing import override

from bot.combat.micro_units.micro_unit import MicroUnit
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroCyclone(MicroUnit):
    cyclone_locks: dict[int, int] = {}
    LOCKON_KEEP_RANGE: int = 15

    @override
    async def fight(self, cyclone: Unit, local_units: Units, chase: bool = False):
        if (cyclone.is_using_ability(AbilityId.LOCKON_LOCKON)):
            target_tag: int = cyclone.orders[0].target
            # print("target: ", target_tag)
            target: Unit = self.bot.enemy_units.find_by_tag(target_tag)
            if (target):
                # print(f"Cyclone is currently locking on to a {target.type_id.name}")
                self.cyclone_locks[cyclone.tag] = target.tag
                return            
        
        local_enemies: Units = self.get_local_enemy_units(cyclone.position, only_menacing=True)
        enemies_in_range: Units = self.get_enemy_units_in_range(cyclone)

        # if we have locked onto a target, stay in range and find the safest spot to kite around it
        available_abilities = (await self.bot.get_available_abilities([cyclone]))[0]
        if (AbilityId.LOCKON_LOCKON not in available_abilities):
            target_tag: int = self.cyclone_locks.get(cyclone.tag, None)
            target: Unit = self.bot.enemy_units.find_by_tag(target_tag) if target_tag else None
            if (target_tag is None or target is None):
                # print("Cyclone is on lock cooldown but target is lost/dead")
                if (enemies_in_range.amount >= 1):
                    self.hit_n_run(cyclone, enemies_in_range)
                    return
                safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(cyclone)
                cyclone.move(safest_spot)
                return    
            
            target: Unit = self.bot.enemy_units.find_by_tag(target_tag)
            if (target):
                self.hit_n_run(cyclone, Units([target], self.bot))
            elif (enemies_in_range.amount >= 1):
                self.hit_n_run(cyclone, enemies_in_range)
            else:
                safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(cyclone)
                cyclone.move(safest_spot)
            return
        
        # else if we have the lock on cooldown
        if (local_enemies.amount == 0):
            safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(cyclone)
            cyclone.move(safest_spot)
            return
        
        # look for potential targets, prioritize in range, then lowest health
        print("looking for a lock target")
        LOCKON_RANGE: int = 7
        total_range: float = LOCKON_RANGE + cyclone.radius
        possible_targets: Units = local_enemies.sorted(
            key=lambda enemy_unit: (
                enemy_unit.distance_to(cyclone) > total_range,   # False (in range) before True
                -(enemy_unit.health + enemy_unit.shield),        # more total hp first
                -enemy_unit.shield,                              # more shield first
                enemy_unit.distance_to(cyclone)                  # closer first
            )
        )
        target: Unit = possible_targets.first
        print(f"Locking on to {target.type_id}")
        cyclone(AbilityId.LOCKON_LOCKON, target)
        self.cyclone_locks[cyclone.tag] = target.tag