import math
from sc2.bot_ai import BotAI
from sc2.data import Race
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types, dont_attack, hq_types, menacing


class Micro:
    bot: BotAI

    def __init__(self, bot) -> None:
        self.bot = bot

    def retreat(self, unit: Unit):
        # TODO: handle retreat when opponent is blocking our way
        enemy_main_position: Point2 = self.bot.enemy_start_locations[0]
        if (self.bot.townhalls.amount == 0):
            return
        unit.move(self.bot.townhalls.closest_to(enemy_main_position))

    async def medivac(self, medivac: Unit, local_army: Units):
        # if not boosting, boost
        await self.medivac_boost(medivac)
        
        # heal damaged ally in local army
        damaged_allies: Units = local_army.filter(
            lambda unit: (
                unit.is_biological
                and unit.health_percentage < 1
            )
        )

        if (damaged_allies.amount >= 1):
            damaged_allies.sort(key = lambda unit: unit.health)
            medivac(AbilityId.MEDIVACHEAL_HEAL, damaged_allies.first)
            # medivac(AbilityId.MEDIVACHEAL_HEAL, damaged_allies.closest_to(medivac))
        else:
            local_ground_units: Units = local_army.filter(lambda unit: unit.is_flying == False)
            if (local_ground_units.amount >= 1):
                medivac.move(local_ground_units.center)
            elif (self.bot.townhalls.amount >= 1):
                self.retreat(medivac)

    async def medivac_boost(self, medivac: Unit):
        available_abilities = (await self.bot.get_available_abilities([medivac]))[0]
        if AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS in available_abilities:
            medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)

    def marine(self, marine: Unit):
        enemy_units_in_range = self.get_enemy_units_in_range(marine)
        other_enemy_units: Unit = self.get_enemy_units()
        enemy_buildings_in_sight = self.bot.enemy_structures.filter(
            lambda building: building.distance_to(marine) <= 12
        )
        
        if (enemy_units_in_range.amount >= 1):
            self.hit_n_run(marine, enemy_units_in_range)
        elif(other_enemy_units.amount >= 1):
            marine.attack(other_enemy_units.closest_to(marine))
        elif(enemy_buildings_in_sight.amount >= 1):
            enemy_buildings_in_sight.sort(key = lambda building: building.health)
            marine.attack(enemy_buildings_in_sight.first)
        else:
            print("[Error] no enemy units to attack")
    
    def hit_n_run(self, unit: Unit, enemy_units_in_range: Units):
        if (enemy_units_in_range.amount == 0):
            return
        enemy_units_in_range.sort(
            key=lambda unit: (
                unit.shield if unit.race == Race.Protoss else unit.health
            )
        )
        if (unit.weapon_ready):
            unit.attack(enemy_units_in_range.first)
        else:
            # only run away from unit with smaller range that are facing (chasing us)
            closest_enemy: Unit = enemy_units_in_range.closest_to(unit)
            if(
                (closest_enemy.can_attack or closest_enemy.type_id in menacing)
                and closest_enemy.is_facing(unit, math.pi)
                and closest_enemy.ground_range < unit.ground_range
            ):
                Micro.move_away(unit, closest_enemy)
            # else:
            #     marine.move(closest_enemy)

    def attack_nearest_base(self, unit: Unit):
        enemy_bases: Units = self.bot.enemy_structures.filter(
            lambda structure: structure.type_id in hq_types
        )
        enemy_main_position: Point2 = self.bot.enemy_start_locations[0]

        if (enemy_bases.amount >= 1):
            unit.attack(enemy_bases.closest_to(unit))
        else:
            unit.attack(enemy_main_position)


    def move_away(selected: Unit, enemy: Unit, distance: int = 2):
        selected_position: Point2 = selected.position
        offset: Point2 = selected_position.negative_offset(enemy.position)
        target: Point2 = selected_position.__add__(offset)
        selected.move(selected_position.towards(target, distance))

    def get_enemy_units(self) -> Units:
        enemy_units: Units = self.bot.enemy_units.filter(lambda unit: not unit.is_structure and unit.can_be_attacked and unit.type_id not in dont_attack)
        enemy_towers: Units = self.bot.enemy_structures.filter(lambda unit: unit.type_id in tower_types)
        return enemy_units + enemy_towers
    
    def get_enemy_units_in_range(self, unit: Unit) -> Units:
        enemy_units_in_range: Units = self.get_enemy_units().filter(
            lambda enemy: unit.target_in_range(enemy)
        )
        return enemy_units_in_range