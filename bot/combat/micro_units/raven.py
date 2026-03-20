from typing import Optional, override

from bot.combat.micro_units.micro_unit import MicroUnit
from bot.utils.unit_supply import get_unit_supply
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroRaven(MicroUnit):
    
    async def raven_interference_matrix(self, raven: Unit) -> bool:
        INTERFERENCE_MATRIX_RANGE: int = 9
        
        close_enemy_units: Units = self.get_local_enemy_units(raven.position, INTERFERENCE_MATRIX_RANGE + 2, only_menacing=True)
        # TODO improve this, so far we consider that every unit that costs 3 or more supply is a good potential target
        potential_targets: Units = close_enemy_units.filter(
            lambda enemy_unit: (
                get_unit_supply(enemy_unit.type_id) > 2
                and not enemy_unit.has_buff(BuffId.RAVENSCRAMBLERMISSILE)
            )
        )
        
        if (potential_targets.amount == 0):
            return False
        
        best_target: Unit = potential_targets.sorted(
            lambda enemy_unit: (
                get_unit_supply(enemy_unit.type_id),
                enemy_unit.health + enemy_unit.shield,
            ),
            reverse=True
        ).first
        print("Casting interference matrix on ", best_target.type_id)
        raven(AbilityId.EFFECT_INTERFERENCEMATRIX, best_target)
        return True
    
    async def raven_antiarmor_missile(self, raven: Unit) -> bool:
        close_enemy_units: Units = self.get_local_enemy_units(raven.position, 10, only_menacing=True)
        if (close_enemy_units.amount < 3):
            return False
        # find the best position to cast anti armor missile
        best_target: Optional[Unit] = None
        best_hit_count: int = 0
        HEALTH_THRESHOLD: int = 200
        for enemy_unit in close_enemy_units:
            enemy_hits: Units = close_enemy_units.closer_than(1.5, enemy_unit.position)
            ally_hits: Units = self.bot.units.closer_than(1.5, enemy_unit.position)
            hit_count: int = sum([enemy.health + enemy.shield for enemy in enemy_hits])
            ally_hit_count: int = sum([ally.health + ally.shield for ally in ally_hits])
            if (hit_count - ally_hit_count > best_hit_count):
                best_hit_count = hit_count - ally_hit_count
                best_target = enemy_unit
        if (best_hit_count >= HEALTH_THRESHOLD and best_target):
            print("Casting anti armor missile")
            raven(AbilityId.EFFECT_ANTIARMORMISSILE, best_target)
            return True
        return False

    async def raven_autoturret(self, raven: Unit) -> bool:
        AUTOTURRET_RANGE: int = 2
        potential_targets: Units = self.get_local_enemy_units(raven.position, AUTOTURRET_RANGE + 4)
        if (potential_targets.amount == 0):
            return False
        # find a position to cast auto turret
        target_enemy: Unit = potential_targets.sorted(
            lambda enemy_unit: (
                -enemy_unit.health + enemy_unit.shield,
                enemy_unit.distance_to(raven)
            )
        ).first
        location: Point2 = await self.bot.find_placement(UnitTypeId.AUTOTURRET, near=target_enemy.position.towards(raven.position))
        if (location):
            print("Casting auto turret")
            raven(AbilityId.BUILDAUTOTURRET_AUTOTURRET, location)
            return True
        else:
            print("No valid location found for auto turret")
            return False
    
    @override
    async def fight(self, raven: Unit, local_units: Units, chase: bool = False):
        # if we have enough energy, cast anti armor missile on the closest group of enemy units
        ANTI_ARMOR_MISSILE_ENERGY_COST: int = 75
        INTERFERENCE_MATRIX_ENERGY_COST: int = 75
        AUTO_TURRET_ENERGY_COST: int = 50

        available_abilities = (await self.bot.get_available_abilities([raven]))[0]
        if (AbilityId.EFFECT_INTERFERENCEMATRIX in available_abilities and raven.energy >= INTERFERENCE_MATRIX_ENERGY_COST):
            if (await self.raven_interference_matrix(raven)):
                return

        if (AbilityId.EFFECT_ANTIARMORMISSILE in available_abilities and raven.energy >= ANTI_ARMOR_MISSILE_ENERGY_COST):
            if (await self.raven_antiarmor_missile(raven)):
                return
        
        if (AbilityId.BUILDAUTOTURRET_AUTOTURRET in available_abilities and raven.energy >= AUTO_TURRET_ENERGY_COST):
            if (await self.raven_autoturret(raven)):
                return
        
        if (not self.safety_disengage(raven)):
            raven.move(local_units.center)

    @override
    async def harass(self, unit: Unit, local_units: Units, workers: Units):
        await self.fight(unit, local_units)

    @override
    async def kill_buildings(self, unit: Unit, local_units: Units, enemy_buildings: Units):
        await self.fight(unit, local_units)