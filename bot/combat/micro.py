import math
from typing import List
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.superbot import Superbot
from bot.utils.point2_functions import center
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, dont_attack, hq_types, menacing, bio_stimmable


class Micro:
    bot: Superbot

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
    
    @property
    def retreat_position(self) -> Point2:
        last_expansion: Expansion = self.bot.expansions.last_taken
        if (last_expansion):
            return last_expansion.retreat_position
        return self.bot.expansions.main.position
    
    def retreat(self, unit: Unit):
        if (self.bot.townhalls.amount == 0):
            return
        enemy_units_in_range: Units = self.bot.enemy_units.in_attack_range_of(unit)
        enemy_units_in_sight: Units = self.bot.enemy_units.filter(lambda enemy_unit: enemy_unit.distance_to(unit) <= 10)
        if (unit.type_id in bio_stimmable and enemy_units_in_range.amount >= 1):
            self.stim_bio(unit)
        
        # TODO: handle retreat when opponent is blocking our way
        local_flying_orbital: Units = self.bot.structures(UnitTypeId.ORBITALCOMMANDFLYING).in_distance_between(unit.position, 0, 10)
        retreat_position = self.retreat_position if local_flying_orbital.amount == 0 else self.retreat_position.towards(local_flying_orbital.center, -2)
        if (unit.type_id == UnitTypeId.MEDIVAC):
            if (
                unit.distance_to(retreat_position) < unit.distance_to(self.bot.enemy_start_locations[0])
                and enemy_units_in_sight.amount == 0
            ):
                unit(AbilityId.UNLOADALLAT_MEDIVAC, unit)
            if (not self.medivac_safety_disengage(unit)):
                unit.move(retreat_position)
            return
        if (unit.distance_to(retreat_position) < 5):
            return
        if (enemy_units_in_range.amount >= 1):
            Micro.move_away(unit, enemy_units_in_range.closest_to(unit), 5)
        else:
            unit.move(retreat_position)
    
    async def medivac_pickup(self, medivac: Unit, local_army: Units):
        # stop unloading if we are
        medivac.stop()
        await self.medivac_boost(medivac)
        units_to_pickup: Units = local_army.in_distance_between(medivac, 0, 3)
        for unit in units_to_pickup:
            medivac(AbilityId.LOAD_MEDIVAC, unit)
        units_next: Units = local_army.in_distance_between(medivac, 3, 10)
        if (units_next.amount == 0):
            return
        medivac.move(units_next.center.towards(units_next.closest_to(medivac)))
    
    def medivac_safety_disengage(self, medivac: Unit, safety_distance: int = 2) -> bool:
        # if medivac is in danger
        menacing_enemy_units: Units = self.enemy_units.filter(
            lambda enemy_unit: (
                (enemy_unit.can_attack_air or enemy_unit.type_id in menacing)
                and enemy_unit.distance_to(medivac) <= enemy_unit.air_range + safety_distance
            )
        )
        # if medivac in danger, retreat and drop units
        if (menacing_enemy_units.amount == 0):
            return False
        
        Micro.move_away(medivac, menacing_enemy_units.center, safety_distance)
        if (medivac.cargo_used >= 1):
            # unload all units if we can
            medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
        return True

    
    async def medivac_disengage(self, medivac: Unit, local_army: Units):
        # boost if we can
        await self.medivac_boost(medivac)
        
        SAFETY_DISTANCE: int = 2
        if (self.medivac_safety_disengage(medivac, SAFETY_DISTANCE)):
            return
        
        # if medivac not in danger, heal the closest damaged unit
        self.medivac_heal(medivac, local_army)

    async def medivac_fight(self, medivac: Unit, local_army: Units):
        # unload if we can, then move towards the closest ground unit
        
        # if our medivac is filled and can unload, unload
        if (medivac.cargo_used >= 1):
            if (self.bot.in_pathing_grid(medivac.position)):
                medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
            
            ground_allied_units: Units = local_army.filter(lambda unit: unit.is_flying == False)
            ground_enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.is_flying == False)
            ground_enemy_buildings: Units = self.bot.enemy_structures
            if (ground_allied_units.amount >= 1):
                medivac.move(medivac.position.towards(ground_allied_units.closest_to(medivac)))
            elif(ground_enemy_units.amount >= 1):
                medivac.move(medivac.position.towards(ground_enemy_units.closest_to(medivac)))
            elif(ground_enemy_buildings.amount >= 1):
                medivac.move(medivac.position.towards(ground_enemy_buildings.closest_to(medivac)))
            else:
                medivac.move(medivac.position.towards(self.bot.expansions.enemy_main.position))

        # boost if we need to
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
        
        SAFETY_DISTANCE: int = 2
        if (self.medivac_safety_disengage(medivac, SAFETY_DISTANCE)):
            return
        self.medivac_heal(medivac, local_army)

    async def medivac_fight_drop(self, medivac: Unit, drop_target: Point2):
        # first boost
        await self.medivac_boost(medivac)
        
        # if there's a base closer than our drop target, we attack it
        # if we don't know any enemy base, we just drop the enemy main
        closest_enemy_base: Expansion = (
            self.bot.expansions.enemy_bases.closest_to(medivac)
            if self.bot.expansions.enemy_bases.amount >= 1
            else self.bot.expansions.enemy_main
        )
        MARGIN: int = 5
        if (closest_enemy_base.position.distance_to(medivac) < drop_target.distance_to(medivac) + MARGIN):
            drop_target = closest_enemy_base.position

        
        # if we are at the same height, unload all units
        # we need to check the height position of the map
        if (self.bot.get_terrain_height(medivac.position) == self.bot.get_terrain_height(drop_target)):
            medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
        
        medivac.move(drop_target)
    
    def medivac_heal(self, medivac: Unit, local_army: Units):
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

    def bio_defense(self, bio: Unit, local_army: Units):
        enemy_units: Units = self.enemy_units.sorted(key = lambda enemy_unit: (enemy_unit.distance_to(bio), enemy_unit.health + enemy_unit.shield))
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
            self.bio(bio, local_army)
            
    def ghost_defense(self, ghost: Unit, local_army: Units):
        if (self.ghost_snipe):
            return
        self.bio_defense(ghost, local_army)


    def bio(self, bio_unit: Unit, local_army: Units):
        local_medivacs: Units = local_army(UnitTypeId.MEDIVAC)
        local_medivacs_with_cargo: Units = local_medivacs.filter(lambda unit: unit.cargo_used > 0)
        enemy_units_in_range = self.get_enemy_units_in_range(bio_unit)
        other_enemy_units: Units = self.enemy_units
        other_enemy_units.sort(key = lambda enemy_unit: (enemy_unit.distance_to(bio_unit), enemy_unit.health + enemy_unit.shield))
        enemy_buildings: Units = self.bot.enemy_structures
        enemy_buildings_in_sight = enemy_buildings.filter(
            lambda building: building.distance_to(bio_unit) <= 12
        )
        enemy_buildings_in_range = enemy_buildings.filter(
            lambda building: bio_unit.target_in_range(building)
        )
        
        
        if (enemy_units_in_range.amount >= 1):
            self.stim_bio(bio_unit)
            self.hit_n_run(bio_unit, enemy_units_in_range)
        elif (other_enemy_units.amount >= 1):
            if (enemy_buildings_in_range.amount >= 1 and bio_unit.weapon_ready):
                self.stim_bio(bio_unit)
                bio_unit.attack(enemy_buildings_in_range.closest_to(bio_unit))
            # if everything isn't unloaded, regroup before attacking
            elif (local_medivacs_with_cargo):
                bio_unit.move(local_army.center)
            else:
                self.stim_bio(bio_unit)
                bio_unit.attack(other_enemy_units.closest_to(bio_unit))
        elif (enemy_buildings_in_sight.amount >= 1):
            enemy_buildings_in_sight.sort(key = lambda building: building.health)
            bio_unit.attack(enemy_buildings_in_sight.first)
        elif (enemy_buildings.amount >= 1):
            # print("[Error] no enemy units to attack")
            bio_unit.attack(enemy_buildings.closest_to(bio_unit))
        else:
            self.retreat(bio_unit)

    def ghost(self, ghost: Unit, local_army: Units):
        if (self.ghost_snipe(ghost)):
            return
        self.bio(ghost, local_army)

    def ghost_snipe(self, ghost: Unit) -> bool:
        # if we don't have energy or are already sniping, we just skip
        if (ghost.energy < 50 or ghost.is_using_ability(AbilityId.EFFECT_GHOSTSNIPE)):
            return False
        potential_snipe_targets: Units = self.bot.enemy_units.filter(
            lambda enemy_unit: (
                enemy_unit.can_be_attacked
                and enemy_unit.type_id not in dont_attack
                and enemy_unit.is_biological
                and enemy_unit.health + enemy_unit.shield >= 60
                and enemy_unit.distance_to(ghost) <= 10
                and not enemy_unit.has_buff(BuffId.GHOSTSNIPEDOT)
            )
        )

        # if we don't have snipe targets, we skip
        if (potential_snipe_targets.amount == 0):
            return False
        potential_snipe_targets.sort(
            key=lambda enemy_unit: (enemy_unit.health + enemy_unit.shield)
        )
        target: Unit = potential_snipe_targets.first
        ghost(AbilityId.EFFECT_GHOSTSNIPE, target)
        return True
            
    def stim_bio(self, bio_unit: Unit):
        if (
            self.bot.already_pending_upgrade(UpgradeId.STIMPACK) < 1
            or bio_unit.has_buff(BuffId.STIMPACK)
            or bio_unit.has_buff(BuffId.STIMPACKMARAUDER)
            or bio_unit.type_id == UnitTypeId.GHOST
        ):
            return
        
        WITH_MEDIVAC_HEALTH_THRESHOLD: int = 30
        WITHOUT_MEDIVAC_HEALTH_THRESHOLD: int = 45
        MARAUDER_HEALTH_SAFETY: int = 10
        MEDIVAC_ENERGY_THRESHOLD: int = 25
        MEDIVAC_HEALTH_THRESHOLD: int = 40
        health_safety: int = MARAUDER_HEALTH_SAFETY if bio_unit.type_id == UnitTypeId.MARAUDER else 0
        
        local_usable_medivacs: Units = self.bot.units(UnitTypeId.MEDIVAC).filter(
            lambda medivac: (
                medivac.distance_to(bio_unit) <= 10
                and medivac.energy >= MEDIVAC_ENERGY_THRESHOLD
                and medivac.health >= MEDIVAC_HEALTH_THRESHOLD
            )
        )
    
        
        if (
            bio_unit.health >= WITHOUT_MEDIVAC_HEALTH_THRESHOLD + health_safety
            or (
                local_usable_medivacs.amount >= 1
                and bio_unit.health >= WITH_MEDIVAC_HEALTH_THRESHOLD + health_safety
            )
        ):
            bio_unit(AbilityId.EFFECT_STIM)

    def bio_disengage(self, bio_unit: Unit):
        enemy_units_in_range = self.get_enemy_units_in_range(bio_unit)
        
        # handle stim
        self.stim_bio(bio_unit)

        if (enemy_units_in_range.amount >= 1):
            self.hit_n_run(bio_unit, enemy_units_in_range)
        else:
            self.retreat(bio_unit)
    
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
            menacing_enemy_units: Units = enemy_units.filter(
                lambda enemy_unit: (
                    other_structures_than_bunkers.in_attack_range_of(enemy_unit).amount >= 1
                    or self.bot.workers.in_attack_range_of(enemy_unit).amount >= 1
                )
            )
            if (menacing_enemy_units.amount == 0 or menacing_enemy_units.closest_distance_to(bunker) <= 8):
                if (bunker.cargo_left >= 1):
                    unit.move(bunker.position.towards(retreat_position, 2))
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
        if (unit.weapon_ready):
            enemy_light_units: Units = enemy_units_in_range.filter(lambda enemy_unit: enemy_unit.is_light)
            enemy_armored_units: Units = enemy_units_in_range.filter(lambda enemy_unit: enemy_unit.is_armored)
            enemy_to_fight: Units = enemy_units_in_range
            
            # choose a better target if the unit has bonus damage
            if (unit.bonus_damage):
                match(unit.bonus_damage[1]):
                    case 'Light':
                        enemy_to_fight = enemy_light_units if enemy_light_units.amount >= 1 else enemy_units_in_range
                    case 'Armored':
                        enemy_to_fight = enemy_armored_units if enemy_armored_units.amount >= 1 else enemy_units_in_range
                    case _:
                        enemy_to_fight = enemy_units_in_range

            enemy_to_fight.sort(
                key=lambda enemy_unit: (
                    enemy_unit.shield + enemy_unit.health
                )
            )
            unit.attack(enemy_to_fight.first)
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
            return enemy_bases.closest_to(unit)
        else:
            for possible_expansion in possible_enemy_expansion_positions:
                if (self.bot.state.visibility[possible_expansion.rounded] == 0):
                    return possible_expansion
            for possible_expansion in possible_enemy_expansion_positions:
                if (self.bot.state.visibility[possible_expansion.rounded] == 1):
                    return possible_expansion
            print("Error : A building is hidden somewhere ?")
            return enemy_main_position

    def move_away(selected: Unit, enemy: Unit|Point2, distance: int = 2):
        selected_position: Point2 = selected.position
        offset: Point2 = selected_position.negative_offset(enemy.position)
        target: Point2 = selected_position.__add__(offset)
        selected.move(selected_position.towards(target, distance))

    @property
    def enemy_units(self) -> Units:
        enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.can_be_attacked and unit.type_id not in dont_attack)
        enemy_towers: Units = self.bot.enemy_structures.filter(lambda unit: unit.type_id in tower_types)
        return enemy_units + enemy_towers
    
    def get_enemy_units_in_range(self, unit: Unit) -> Units:
        if (unit is None):
            return Units([], self.bot)
        enemy_units_in_range: Units = self.enemy_units.filter(
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