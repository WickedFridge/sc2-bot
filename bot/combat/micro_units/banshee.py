from typing import override

from bot.combat.micro_units.scouting_unit import MicroScoutingUnit
from bot.utils.unit_tags import detectors, worker_types, townhalls
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.effect_id import EffectId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

class MicroBanshee(MicroScoutingUnit):
    WEAPON_READY_THRESHOLD: int = 4
    DETECTION_RANGE: float = 11
    SCAN_RADIUS: float = 13

    @override
    async def heal_up(self, unit: Unit, local_units: Units):
        threats: Units = self.local_threats(unit)
        if (threats.amount == 0):
            self.uncloak(unit)
        closest_mineral_line: Point2 = self.bot.expansions.closest_to(self.retreat_position).mineral_line
        unit.move(closest_mineral_line)

    def cloak(self, banshee: Unit):
        if (not banshee.has_buff(BuffId.BANSHEECLOAK) and banshee.energy >= 25):
            banshee(AbilityId.BEHAVIOR_CLOAKON_BANSHEE)

    def uncloak(self, banshee: Unit):
        if (banshee.has_buff(BuffId.BANSHEECLOAK)):
            banshee(AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE)

    def local_threats(self, banshee: Unit) -> Units:
        return self.enemy_all.filter(
            lambda enemy: (
                enemy.distance_to(banshee) < 20
                and enemy.can_attack_air
            )
        )

    def is_detected(self, banshee: Unit) -> bool:
        enemy_detectors: Units = (self.bot.enemy_units + self.bot.enemy_structures)(detectors)
        if (enemy_detectors.closer_than(self.DETECTION_RANGE, banshee).amount >= 1):
            return True
        # Orbital scans also reveal us
        for effect in self.bot.state.effects:
            if (effect.id == EffectId.SCANNERSWEEP and effect.is_enemy):
                if (any(banshee.distance_to(position) <= self.SCAN_RADIUS for position in effect.positions)):
                    return True
        return False

    def is_invisible(self, banshee: Unit) -> bool:
        return (
            banshee.has_buff(BuffId.BANSHEECLOAK)
            and not self.is_detected(banshee)
            and banshee.energy > 5
        )

    def fight_invisible(self, banshee: Unit) -> bool:
        """
        Nobody can hit us: ignore every threat and act as if the local danger was 0.
        Returns False if there's nothing to fight, so the default behaviour can take over.
        """
        enemy_ground: Units = self.enemy_all.filter(lambda enemy: enemy.is_flying == False)
        if (enemy_ground.amount == 0):
            return False

        # Weapon ready: shoot the weakest enemy in range, otherwise go for the closest one
        if (banshee.weapon_cooldown <= self.WEAPON_READY_THRESHOLD):
            # if there's an enemy in range, shoot it
            enemy_ground_in_range: Units = self.get_enemy_units_in_range(banshee).filter(lambda enemy: enemy.is_flying == False)
            if (enemy_ground_in_range.amount >= 1):
                target: Unit = enemy_ground_in_range.sorted(lambda enemy: (enemy.health + enemy.shield, enemy.distance_to_squared(banshee))).first
                banshee.attack(target)
                return True

            # if there are workers around, attack the closest one
            workers_around: Units = enemy_ground.filter(lambda enemy: enemy.type_id in worker_types and enemy.distance_to(banshee) < 10)
            if (workers_around.amount >= 1):
                banshee.attack(workers_around.closest_to(banshee))
                return True

            # if there are townhalls around, move to the closest one (looking for workers)
            townhalls_around: Units = self.bot.enemy_structures.filter(lambda enemy: enemy.type_id in townhalls and enemy.distance_to(banshee) < 10)
            if (townhalls_around.amount >= 1):
                banshee.move(townhalls_around.closest_to(banshee))
                return True

            # otherwise, attack the closest enemy
            banshee.attack(enemy_ground.closest_to(banshee))
            return True

        # On cooldown: stay just in range of the closest enemy, no need to back off
        closest_enemy: Unit = enemy_ground.closest_to(banshee)
        attack_distance: float = banshee.radius + closest_enemy.radius + banshee.ground_range - 0.5
        banshee.move(closest_enemy.position.towards(banshee, attack_distance))
        return True

    @override
    async def fight(self, unit: Unit, local_units: Units, chase: bool = False):
        if (self.is_invisible(unit) and self.fight_invisible(unit)):
            return
        threats: Units = self.local_threats(unit)
        if (threats.amount >= 1):
            self.cloak(unit)
        return await super().fight(unit, local_units, chase)

    @override
    async def retreat(self, unit: Unit, local_units: Units):
        threats: Units = self.local_threats(unit)
        if (threats.amount == 0):
            self.uncloak(unit)
        return await super().retreat(unit, local_units)
