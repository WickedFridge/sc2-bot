import math
from typing import List
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.utils.point2_functions import center
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
    expansions: Expansions

    def __init__(self, bot: BotAI, expansions: Expansions) -> None:
        self.bot = bot
        self.expansions = expansions

    @property
    def retreat_position(self) -> Point2:
        last_expansion: Expansion = self.expansions.last_taken
        if (last_expansion):
            return last_expansion.retreat_position
        return self.expansions.main.position
    
    def retreat(self, unit: Unit):
        if (self.bot.townhalls.amount == 0):
            return
        enemy_units_in_range: Units = self.bot.enemy_units.in_attack_range_of(unit)
        enemy_units_in_sight: Units = self.bot.enemy_units.filter(lambda enemy_unit: enemy_unit.distance_to(unit) <= 10)
        if (unit.type_id in bio and enemy_units_in_range.amount >= 1):
            self.stim_bio(unit)
        
        # TODO: handle retreat when opponent is blocking our way
        retreat_position = self.retreat_position
        if (
            unit.type_id == UnitTypeId.MEDIVAC
            and unit.distance_to(retreat_position) < unit.distance_to(self.bot.enemy_start_locations[0])
            and enemy_units_in_sight.amount == 0
        ):
            unit(AbilityId.UNLOADALLAT_MEDIVAC, unit)
        if (unit.distance_to(retreat_position) < 5):
            return
        unit.move(retreat_position)
    
    async def medivac(self, medivac: Unit, local_army: Units):
        if (medivac.cargo_used >= 1):
            medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac.position)

        if (medivac.is_active):
            medivac_target: Point2|int = medivac.orders[0].target 
            target_position: Point2|None = None
            if (type(medivac_target) is Point2):
                target_position = medivac_target
            else:
                target_unit = self.bot.units.find_by_tag(medivac_target)
                if (target_unit):
                    target_position = target_unit.position
                
            if (target_position and target_position.distance_to(medivac) > 10):
                await self.medivac_boost(medivac)
        
        # heal damaged ally in local army
        damaged_allies: Units = local_army.filter(
            lambda unit: (
                unit.is_biological
                and unit.health_percentage < 1
            )
        )

        if (damaged_allies.amount >= 1):
            damaged_allies.sort(key = lambda unit: (unit.health, unit.distance_to(medivac)))
            # start with allies in range
            damaged_allies_in_range: Units = damaged_allies.filter(lambda unit: unit.distance_to(medivac) <= 3)
            if (damaged_allies_in_range.amount):
                medivac(AbilityId.MEDIVACHEAL_HEAL, damaged_allies_in_range.first)
            else:
                medivac(AbilityId.MEDIVACHEAL_HEAL, damaged_allies.first)
        else:
            local_ground_units: Units = local_army.filter(lambda unit: unit.is_flying == False)
            if (local_ground_units.amount >= 1):
                medivac.move(local_ground_units.center)
            elif (self.bot.townhalls.amount >= 1):
                self.retreat(medivac)

    async def medivac_boost(self, medivac: Unit):
        available_abilities = (await self.bot.get_available_abilities([medivac]))[0]
        if (AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS in available_abilities):
            medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)

    def bio_defense(self, bio: Unit):
        enemy_units: Units = self.get_enemy_units().sorted(key = lambda enemy_unit: (enemy_unit.distance_to(bio), enemy_unit.health + enemy_unit.shield))
        if (enemy_units.amount == 0):
            print("[Error] no enemy units to attack")
            self.bio(bio)
            return
        
        close_bunkers: Units = self.bot.structures(UnitTypeId.BUNKER).filter(lambda bunker: bunker.distance_to(bio) <= 10)
        closest_bunker: Unit = close_bunkers.closest_to(bio) if close_bunkers else None
        if (closest_bunker):
            # handle stim
            self.stim_bio(bio)
            self.defend_around_bunker(bio, enemy_units, closest_bunker)
        else:
            self.bio(bio)
            
    
    def bio(self, bio: Unit):
        enemy_units_in_range = self.get_enemy_units_in_range(bio)
        other_enemy_units: Units = self.get_enemy_units()
        other_enemy_units.sort(key = lambda enemy_unit: (enemy_unit.distance_to(bio), enemy_unit.health + enemy_unit.shield))
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
        elif(enemy_buildings.amount >= 1):
            # print("[Error] no enemy units to attack")
            bio.attack(enemy_buildings.closest_to(bio))
        else:
            self.retreat(bio)

    def stim_bio(self, bio_unit: Unit):
        if (self.bot.already_pending_upgrade(UpgradeId.STIMPACK) < 1):
            return

        local_enemy_units: Units = self.get_local_enemy_units(bio_unit.position)
        local_enemy_buildings: Units = self.get_local_enemy_buildings(bio_unit.position)

        match bio_unit.type_id:
            case UnitTypeId.MARINE:
                if (
                    (local_enemy_units.amount >= 1 and bio_unit.health >= 25 or (local_enemy_buildings.amount >= 1 and bio_unit.health >= 40))
                    and not bio_unit.has_buff(BuffId.STIMPACK)
                ):
                    bio_unit(AbilityId.EFFECT_STIM)
            case UnitTypeId.MARAUDER:
                if (
                    (local_enemy_units.amount >= 1 and bio_unit.health >= 35 or (local_enemy_buildings.amount >= 1 and bio_unit.health >= 55))
                    and not bio_unit.has_buff(BuffId.STIMPACKMARAUDER)
                ):
                    bio_unit(AbilityId.EFFECT_STIM)

    # TODO if enemy units are menacing something else than the bunker, get out and fight
    def defend_around_bunker(self, unit: Unit, enemy_units: Units, bunker: Unit):
        if (not bunker):
            return
        close_townhalls: Units = self.bot.townhalls.filter(lambda townhall: townhall.distance_to(unit) <= 20)
        closest_townhall: Unit = close_townhalls.closest_to(unit) if close_townhalls.amount >= 1 else None
        retreat_position: Point2 = bunker if close_townhalls.amount == 0 else center([bunker.position, closest_townhall.position])

        if (enemy_units.amount == 0):
            unit.move(retreat_position)

        enemy_units.sort(
            key=lambda enemy_unit: (
                enemy_unit.shield + enemy_unit.health
            )
        )
        enemy_units_in_range: Units = enemy_units.filter(lambda enemy_unit: unit.target_in_range(enemy_unit))
            
        if (unit.weapon_ready and enemy_units_in_range.amount >= 1):
            unit.attack(enemy_units_in_range.first)
        else:
            # if no enemy units are menacing something else than the bunker
            # defend by the bunker
            # otherwise get out and fight
            other_structures_than_bunkers: Units = self.bot.structures.filter(lambda structure: structure.type_id != UnitTypeId.BUNKER)
            menacing_enemy_units: Units = enemy_units.filter(lambda enemy_unit: other_structures_than_bunkers.in_attack_range_of(enemy_unit))
            if (menacing_enemy_units.amount == 0 or menacing_enemy_units.closest_distance_to(bunker) <= 8):
                if (bunker.cargo_left >= 1):
                    unit.move(bunker)
                elif (unit.distance_to(retreat_position) > 2):
                    unit.move(retreat_position)
                else:
                    Micro.move_away(unit, enemy_units.closest_to(unit))
            else:
                if (unit.weapon_ready):
                    unit.attack(enemy_units.closest_to(unit))
                else:
                    Micro.move_away(unit, enemy_units.closest_to(unit))
    
    def hit_n_run(self, unit: Unit, enemy_units_in_range: Units):
        if (enemy_units_in_range.amount == 0):
            return
        enemy_units_in_range.sort(
            key=lambda enemy_unit: (
                enemy_unit.shield + enemy_unit.health
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

    def attack_nearest_base(self, unit: Unit):
        target_position: Point2 = self.get_nearest_base_target(unit)
        if (unit.distance_to(target_position) > 50):
            target_position = unit.position.towards(target_position, 50)
        unit.attack(target_position)

    def attack_position(self, unit: Unit, target_position: Point2):
        if (unit.distance_to(target_position) > 50):
            target_position = unit.position.towards(target_position, 50)
        unit.attack(target_position)

    def get_nearest_base_target(self, unit: Unit) -> Point2:
        enemy_main_position: Point2 = self.bot.enemy_start_locations[0]
        enemy_bases: Units = self.bot.enemy_structures.filter(
            lambda structure: structure.type_id in hq_types
        )
        possible_enemy_expansion_positions: List[Point2] = self.bot.expansion_locations_list
        possible_enemy_expansion_positions.sort(
            key = lambda position: position.distance_to(enemy_main_position)
        )
        
        if (enemy_bases.amount >= 1):
            return enemy_bases.closest(unit)
        else:
            for possible_expansion in possible_enemy_expansion_positions:
                if (self.bot.state.visibility[possible_expansion.rounded] == 0):
                    return possible_expansion
            for possible_expansion in possible_enemy_expansion_positions:
                if (self.bot.state.visibility[possible_expansion.rounded] == 1):
                    return possible_expansion
            print("Error : A building is hidden somewhere ?")
            return enemy_main_position

    def move_away(selected: Unit, enemy: Unit, distance: int = 2):
        selected_position: Point2 = selected.position
        offset: Point2 = selected_position.negative_offset(enemy.position)
        target: Point2 = selected_position.__add__(offset)
        selected.move(selected_position.towards(target, distance))

    def get_enemy_units(self) -> Units:
        enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.can_be_attacked and unit.type_id not in dont_attack)
        enemy_towers: Units = self.bot.enemy_structures.filter(lambda unit: unit.type_id in tower_types)
        return enemy_units + enemy_towers
    
    def get_enemy_units_in_range(self, unit: Unit) -> Units:
        if (unit is None):
            return Units([], self.bot)
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