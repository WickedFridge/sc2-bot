import math
from typing import List
from sc2.bot_ai import BotAI
from sc2.data import Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types, dont_attack, hq_types, menacing, bio


class Micro:
    bot: BotAI

    def __init__(self, bot) -> None:
        self.bot = bot

    def retreat(self, unit: Unit):
        if (self.bot.townhalls.amount == 0):
            return
        enemy_units_in_range: Units = self.bot.enemy_units.in_attack_range_of(unit)
        if (unit.type_id in bio and enemy_units_in_range.amount >= 1):
            self.stim_bio(unit)
        # TODO: handle retreat when opponent is blocking our way
        enemy_main_position: Point2 = self.bot.enemy_start_locations[0]
        townhalls: Units = self.bot.townhalls
        if (townhalls.amount == 1):
            unit.move(townhalls.first)
            return
        townhalls.sort(key = lambda unit: unit.distance_to(enemy_main_position))
        retreat_position: Point2 = townhalls.first.position.towards(townhalls[1].position, 5)
        bunkers_close = self.bot.structures(UnitTypeId.BUNKER).filter(lambda unit: unit.distance_to(retreat_position) <= 10)
        
        # TODO : does this goes by the bunker ?
        if (bunkers_close.amount >= 1):
            retreat_position = retreat_position.towards(bunkers_close.center, 2)
        if (unit.distance_to(retreat_position) < 5):
            return
        unit.move(retreat_position)

    async def medivac(self, medivac: Unit, local_army: Units):
        # TODO: boost only when the target of the order is far away
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

    def bio(self, bio: Unit):
        enemy_units_in_range = self.get_enemy_units_in_range(bio)
        other_enemy_units: Units = self.get_enemy_units()
        enemy_buildings_in_sight = self.bot.enemy_structures.filter(
            lambda building: building.distance_to(bio) <= 12
        )
        enemy_buildings: Units = self.bot.enemy_structures
        
        # handle stim
        self.stim_bio(bio)

        if (enemy_units_in_range.amount >= 1):
            self.hit_n_run(bio, enemy_units_in_range)
        elif(other_enemy_units.amount >= 1):
            bio.attack(other_enemy_units.closest_to(bio))
        elif(enemy_buildings_in_sight.amount >= 1):
            enemy_buildings_in_sight.sort(key = lambda building: building.health)
            bio.attack(enemy_buildings_in_sight.first)
        else:
            # print("[Error] no enemy units to attack")
            bio.attack(enemy_buildings.closest_to(bio))
    

    def stim_bio(self, marine: Unit):
        if (self.bot.already_pending_upgrade(UpgradeId.STIMPACK) < 1):
            return

        local_enemy_units: Units = self.get_local_enemy_units(marine.position)
        local_enemy_buildings: Units = self.get_local_enemy_buildings(marine.position)

        match marine.type_id:
            case UnitTypeId.MARINE:
                if (
                    (local_enemy_units.amount >= 1 and marine.health >= 25 or (local_enemy_buildings.amount >= 1 and marine.health >= 45))
                    and not marine.has_buff(BuffId.STIMPACK)
                ):
                    marine(AbilityId.EFFECT_STIM)
            case UnitTypeId.MARAUDER:
                if (
                    (local_enemy_units.amount >= 1 and marine.health >= 25 or (local_enemy_buildings.amount >= 1 and marine.health >= 45))
                    and not marine.has_buff(BuffId.STIMPACKMARAUDER)
                ):
                    marine(AbilityId.EFFECT_STIM)

    def hit_n_run(self, unit: Unit, enemy_units_in_range: Units):
        if (enemy_units_in_range.amount == 0):
            return
        enemy_units_in_range.sort(
            key=lambda unit: (
                unit.shield + unit.health
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
        possible_enemy_expansion_positions: List[Point2] = self.bot.expansion_locations_list
        possible_enemy_expansion_positions.sort(
            key = lambda position: position.distance_to(enemy_main_position)
        )

        if (enemy_bases.amount >= 1):
            unit.attack(enemy_bases.closest_to(unit))
        else:
            for possible_expansion in possible_enemy_expansion_positions:
                if (self.bot.state.visibility[possible_expansion.rounded] == 0):
                    unit.attack(possible_expansion)
                    return
            for possible_expansion in possible_enemy_expansion_positions:
                if (self.bot.state.visibility[possible_expansion.rounded] == 1):
                    unit.attack(possible_expansion)
                    return
            print("Error : A building is hidden somewhere ?")


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
    
    def get_local_enemy_units(self, position: Point2) -> Units:
        global_enemy_units: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.can_be_attacked
                and unit.type_id not in dont_attack
            )
        )
        local_enemy_units: Units = global_enemy_units.filter(
            lambda unit: unit.distance_to(position) <= 20
        )
        local_enemy_towers: Units = self.bot.enemy_structures.filter(
            lambda unit: unit.type_id in tower_types and unit.can_be_attacked
        )
        return local_enemy_units + local_enemy_towers

    def get_local_enemy_buildings(self, position: Point2) -> Units:
        local_enemy_buildings: Units = self.bot.enemy_structures.filter(
            lambda unit: unit.distance_to(position) <= 10 and unit.can_be_attacked
        )
        local_enemy_buildings.sort(key=lambda building: building.health)
        return local_enemy_buildings