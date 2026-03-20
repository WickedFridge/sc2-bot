import math
from typing import List

from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.point2_functions.utils import center
from sc2.cache import CachedClass, custom_cache_once_per_frame
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from bot.utils.unit_tags import dont_attack, menacing, tower_types, creep, building_priorities, hq_types

class MicroUnit(CachedClass):
    bot: Superbot
    WEAPON_READY_THRESHOLD: float = 6.0
    bonus_against_ground_light: bool = False
    bonus_against_air_light: bool = False
    bonus_against_ground_armored: bool = False
    bonus_against_air_armored: bool = False
    bonus_against_ground_mechanical: bool = False
    bonus_against_air_massive: bool = False
    
    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.bot = bot

    def is_valid_enemy(self, unit: Unit) -> bool:
        # if (not unit.can_be_attacked):
        #     return False
        if (unit.type_id in dont_attack):
            return False
        return True

    def is_fighting_unit(self, unit: Unit) -> bool:
        return unit.can_attack or unit.type_id in menacing
    
    def can_threaten_air(self, unit: Unit) -> bool:
        return unit.can_attack_air or unit.type_id in menacing

    def is_tower(self, unit: Unit) -> bool:
        return unit.type_id in tower_types
    
    def is_creep_tumor(self, unit: Unit) -> bool:
        return unit.type_id in creep
    
    def filter_bonus_damage(self, unit: Unit) -> bool:
        if (unit.is_light and unit.is_flying and self.bonus_against_air_light):
            return True
        if (unit.is_light and not unit.is_flying and self.bonus_against_ground_light):
            return True
        if (unit.is_armored and unit.is_flying and self.bonus_against_air_armored):
            return True
        if (unit.is_armored and not unit.is_flying and self.bonus_against_ground_armored):
            return True
        if (unit.is_mechanical and not unit.is_flying and self.bonus_against_ground_mechanical):
            return True
        if (unit.is_massive and unit.is_flying and self.bonus_against_air_massive):
            return True

    @custom_cache_once_per_frame
    def enemy_all(self) -> Units:
        """Everything worth considering: real units, towers, and creep tumors."""
        units = self.bot.enemy_units.filter(self.is_valid_enemy)
        towers = self.bot.enemy_structures.filter(self.is_tower)
        tumors = self.bot.enemy_structures.filter(self.is_creep_tumor)
        return units + towers + tumors

    @custom_cache_once_per_frame
    def enemy_fighting(self) -> Units:
        return self.enemy_all.filter(self.is_fighting_unit)
           
    def enemies_threatening_air_in_range(self, unit: Unit, safety_distance: float = 0) -> Units:
        return self.enemy_all.filter(
            lambda enemy: (
                self.can_threaten_air(enemy) and
                enemy.distance_to(unit) <= unit.radius + enemy.radius + enemy.air_range + safety_distance
            )
        )
    
    def enemies_threatening_ground_in_range(
        self, unit: Unit, safety_distance: float = 0, range_override: float | None = None
    ) -> Units:
        """
        Returns enemy units that can threaten the given unit (ground target logic).
        If range_override is set, only considers enemies within that radius first.
        """
        # Step 1: get globally valid combat enemies
        threats = self.enemy_all.filter(self.is_fighting_unit)

        # Step 2: optional proximity filter
        if (range_override):
            threats = threats.closer_than(range_override, unit)

        # Step 3: threat capability check
        threats = threats.filter(
            lambda enemy: (
                (enemy.can_attack_ground or enemy.type_id in menacing)
                and enemy.distance_to(unit) <= unit.radius + enemy.radius + enemy.ground_range + safety_distance
            )
        )

        return threats
    
    def get_potential_targets(self, unit: Unit) -> Units:
        if (unit is None):
            return Units([], self.bot)
        base_range: float = unit.distance_to_weapon_ready + unit.radius

        return self.enemy_all.filter(
            lambda enemy: enemy.distance_to(unit) <= (
                base_range + enemy.radius + 
                (unit.ground_range if not enemy.is_flying else unit.air_range)
            )
        )
    
    def get_enemy_units_in_range(self, unit: Unit, include_buildings: bool = False) -> Units:
        if (unit is None):
            return Units([], self.bot)
        
        enemies: Units = (
            self.enemy_all
            if not include_buildings
            else (self.bot.enemy_units + self.bot.enemy_structures).filter(self.is_valid_enemy)
        )
        return enemies.filter(
            lambda enemy: unit.target_in_range(enemy)
        )
    
    def get_local_enemy_units(self, position: Point2, radius: float = 20, only_menacing: bool = False) -> Units:
        enemies = self.enemy_all
        if (only_menacing):
            enemies = enemies.filter(self.is_fighting_unit)

        return enemies.filter(
            lambda enemy: enemy.distance_to(position) <= radius + enemy.radius
        )

    def get_local_enemy_buildings(self, position: Point2) -> Units:
        return self.bot.enemy_structures.filter(
            self.is_valid_enemy
        ).closer_than(
            10, position
        ).sorted(
            lambda building: building.health + building.shield
        )
        
    def pick_best_target(self, enemy_units_in_range: Units) -> Unit:
        enemy_bonus_damage: Units = enemy_units_in_range.filter(self.filter_bonus_damage)
        enemy_to_fight: Units = (
            enemy_bonus_damage
            if enemy_bonus_damage.amount >= 1
            else enemy_units_in_range
        ).sorted(
            lambda enemy_unit: (
                not enemy_unit.has_buff(BuffId.RAVENSHREDDERMISSILEARMORREDUCTION), # False to come up first
                not enemy_unit.has_buff(BuffId.GUARDIANSHIELD),                     # False to come up first
                enemy_unit.has_buff(BuffId.PROTECTIVEBARRIER),                      # True to come up last
                enemy_unit.shield,
                enemy_unit.shield + enemy_unit.health
            )
        )
        return enemy_to_fight.first

    @custom_cache_once_per_frame
    def retreat_position(self) -> Point2:
        if (self.bot.expansions.taken.amount <= 1):
            return self.bot.expansions.main.retreat_position
        if (self.bot.scouting.known_enemy_army.supply == 0):
            return self.bot.expansions.last_taken.retreat_position
        # if one of our expand is getting harassed, choose this one
        if (self.bot.enemy_units.amount >= 1):
            # select enemy harassing
            enemy_units_harassing: Units = self.bot.enemy_units.in_distance_of_group(self.bot.expansions.taken.ccs, 15)
            if (enemy_units_harassing.amount >= 1):
                return self.bot.expansions.taken.closest_to(enemy_units_harassing.center).retreat_position
        return self.bot.expansions.taken.without_main.closest_to(self.bot.scouting.known_enemy_army.center).retreat_position
    
        
    async def a_move(self, unit: Unit, target_position: Point2):
        DISTANCE_THRESHOLD: int = 50
        if (unit.distance_to(target_position) > DISTANCE_THRESHOLD):
            target_position: Point2 = unit.position.towards(target_position, 50)
        enemy_units_in_range: Units = self.get_enemy_units_in_range(unit)
        if (unit.weapon_cooldown <= self.WEAPON_READY_THRESHOLD and enemy_units_in_range.amount >= 1):
            target: Unit = self.pick_best_target(enemy_units_in_range)
            unit.attack(target)
        else:
            unit.move(target_position)
    
    def safety_disengage(self, flying_unit: Unit) -> bool:
        safety_distance =  0.5 + 2.5 * (1 - math.pow(flying_unit.health_percentage, 2))
        # if medivac is in danger
        menacing_enemy_units = self.enemies_threatening_air_in_range(flying_unit, safety_distance)
        if (menacing_enemy_units.amount == 0):
            return False
        
        # if flying unit in danger, move towards a better retreat position
        retreat_direction: Point2 = flying_unit.position
        for enemy_unit in menacing_enemy_units:
            margin: float = flying_unit.radius + enemy_unit.radius + enemy_unit.air_range + safety_distance
            excess_distance: float = margin - enemy_unit.distance_to(flying_unit)
            retreat_direction = retreat_direction.towards(enemy_unit, -excess_distance)
        retreat_direction = retreat_direction.towards(self.retreat_position, 5 - safety_distance)
        
        # this should help us avoid splash damage like Storms and Biles
        safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_point(retreat_direction, air=True)
        flying_unit.move(safest_spot)
        return True
    
    def hit_n_run(self, unit: Unit, enemy_units_in_range: Units, kite_forward: bool = False):
        if (enemy_units_in_range.amount == 0):
            return
        target: Unit = self.pick_best_target(enemy_units_in_range)
        if (unit.weapon_cooldown <= self.WEAPON_READY_THRESHOLD):
            unit.attack(target)
        else:
            best_spot: Point2 = (
                self.bot.map.influence_maps.best_attacking_spot(unit, target)
                if kite_forward
                else self.bot.map.influence_maps.safest_spot_away(unit, enemy_units_in_range.closest_to(unit))
            )
            unit.move(best_spot)
    
    def handle_engagement(
        self,
        unit: Unit,
        enemy_units_in_range: Units,
        other_enemies: Units,
        kite_forward: bool = False,
    ) -> bool:
        
        # If someone is in range → hit'n'run
        if (enemy_units_in_range.amount >= 1):
            self.hit_n_run(unit, enemy_units_in_range, kite_forward)
            return True
        
        if (other_enemies.amount >= 1):
            closest_target: Unit = other_enemies.closest_to(unit)
            if (closest_target.can_be_attacked):
                unit.attack(closest_target)
            else:
                unit.move(closest_target.position)
            return True
        return False
    
    
    # TODO if enemy units are menacing something else than the bunker, get out and fight
    def fight_around_structure(self, unit: Unit, enemy_units: Units, structure: Unit):
        if (not structure):
            return
        close_townhalls: Units = self.bot.townhalls.filter(lambda townhall: townhall.distance_to(unit) <= 20)
        closest_townhall: Unit = close_townhalls.closest_to(unit) if close_townhalls.amount >= 1 else None
        retreat_position: Point2 = structure.position if close_townhalls.amount == 0 else center([structure.position, closest_townhall.position])

        if (enemy_units.amount == 0):
            unit.move(retreat_position)

        enemy_units_in_range: Units = self.get_enemy_units_in_range(unit)

        if (unit.weapon_cooldown <= self.WEAPON_READY_THRESHOLD and enemy_units_in_range.amount >= 1):
            target: Unit = self.pick_best_target(enemy_units_in_range)
            unit.attack(target)
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
            if (menacing_enemy_units.amount == 0 or menacing_enemy_units.closest_distance_to(structure) <= 8):
                if (structure.cargo_left >= 1):
                    unit.move(structure.position.towards(retreat_position, 2))
                elif (unit.distance_to(retreat_position) > 2):
                    unit.move(retreat_position)
                else:
                    safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(structure)
                    unit.move(safest_spot)
            else:
                if (unit.weapon_cooldown <= self.WEAPON_READY_THRESHOLD):
                    target: Unit = self.pick_best_target(enemy_units)
                    unit.attack(target)
                else:
                    safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(structure)
                    unit.move(safest_spot)
    
    async def fight(self, unit: Unit, local_units: Units, chase: bool = False):
        if (self.bot.enemy_units.amount >= 1):
            closest_enemy_unit: Unit = self.bot.enemy_units.closest_to(unit)
            unit.attack(closest_enemy_unit)
        else:
            unit.move(local_units.center)

    async def fight_defense(self, unit: Unit, local_units: Units):
        await self.fight(unit, local_units)

    async def fight_unload(self, unit: Unit, local_units: Units, drop_target: Point2):
        await self.fight(unit, local_units)

    async def harass(self, unit: Unit, local_units: Units, workers: Units):
        # calculate the range of the unit based on its movement speed + range + cooldown
        closest_worker: Unit = workers.closest_to(unit)
        worker_potential_targets: Units = self.get_potential_targets(unit).sorted(
            lambda worker: ((worker.health + worker.shield), worker.distance_to(unit))
        )

        buildings_in_range: Units = self.bot.enemy_structures.filter(
            lambda building: unit.target_in_range(building)
        ).sorted(
            lambda building: (building.type_id not in building_priorities, building.health + building.shield)
        )
        
        # first case : we're dangerously close to a worker + low on life => retreat to a safer spot
        if (unit.health <= 10 and workers.closest_distance_to(unit) <= 1.5):
            unit.move(unit.position.towards(closest_worker, -1))
            # safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, workers.closest_to(unit), range_modifier=unit.health_percentage)
            # unit.move(safest_spot)
            return
        
        # in these case we should target a worker
        if (worker_potential_targets.amount >= 1 or unit.weapon_cooldown > self.WEAPON_READY_THRESHOLD or buildings_in_range.amount == 0):
            # define the best target
            target: Unit = worker_potential_targets.first if worker_potential_targets.amount >= 1 else closest_worker
            # if we're not on cooldown and workers are really close, run away
            if (unit.weapon_cooldown > self.WEAPON_READY_THRESHOLD):
                if (workers.closest_distance_to(unit) <= 1.5 and unit.health_percentage < 1):
                    # safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, workers.closest_to(unit), range_modifier=unit.health_percentage)
                    # unit.move(safest_spot)
                    unit.move(unit.position.towards(closest_worker, -1))
                else:
                    # move towards the unit but not too close
                    best_position: Point2 = self.bot.map.influence_maps.best_attacking_spot(unit, target, risk=1)
                    unit.move(best_position)
            # if we're on cooldown, shoot at it
            else:
                unit.attack(target)
        else:
            unit.attack(buildings_in_range.first)
    
    async def kill_buildings(self, unit: Unit, local_units: Units, enemy_buildings: Units):
        target: Unit = enemy_buildings.first
        if (unit.weapon_cooldown > self.WEAPON_READY_THRESHOLD):
            unit.move(target.position)
            return
        in_range_enemy_buildings: Units = enemy_buildings.filter(lambda building: unit.target_in_range(building))
        if (in_range_enemy_buildings.amount >= 1):
            target = in_range_enemy_buildings.first
        unit.attack(target)
    
    async def attack_nearest_base(self, unit: Unit, army: Army, target: Point2):
        target: Point2 = (
            army.leader.position
            if unit.position.distance_to(army.leader.position) >= 3
            else center([unit.position, army.leader.position, target])
        )
        unit.move(target)
      
    async def chase_buildings(self, unit: Unit, army: Army, target: Point2):
        enemy_units_in_range = self.get_enemy_units_in_range(unit)
        if (unit.weapon_cooldown <= self.WEAPON_READY_THRESHOLD and enemy_units_in_range.amount >= 1):
            unit.attack(enemy_units_in_range.sorted(lambda unit: (unit.health + unit.shield)).first)
        elif (unit.distance_to(army.leader) >= 3):
            unit.move(army.leader.position)
        else:
            unit.move(center([unit.position, army.leader.position, target]))
    
    async def disengage(self, unit: Unit, local_units: Units):
        await self.retreat(unit, local_units)

    async def defend(self, unit: Unit, local_units: Units, expansion: Expansion):
        unit.attack(expansion.position)        
    
    async def heal_up(self, unit: Unit, local_units: Units):
        if (unit.distance_to(local_units.center) > 5):
            unit.move(local_units.center)
    
    async def retreat(self, unit: Unit, local_units: Units):
        if (self.bot.townhalls.amount == 0):
            return
        
        # Don't get in the way of flying townhalls
        local_flying_townhall: Units = self.bot.structures([UnitTypeId.ORBITALCOMMANDFLYING, UnitTypeId.COMMANDCENTERFLYING]).in_distance_between(unit.position, 0, 10)
        retreat_position = self.retreat_position if local_flying_townhall.amount == 0 else self.retreat_position.towards(local_flying_townhall.center, -5)
        
        if (unit.is_flying and self.safety_disengage(unit)):
            return
        if (unit.distance_to(retreat_position) < 5):
            return
        
        enemy_units_in_range: Units = self.bot.enemy_units.in_attack_range_of(unit)
        if (enemy_units_in_range.amount >= 1):
            safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, enemy_units_in_range.closest_to(unit))
            unit.move(safest_spot)
        else:
            unit.move(retreat_position)