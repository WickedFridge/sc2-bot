from typing import List

from bot.macro.expansion import Expansion
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.unit_cargo import get_building_cargo
from bot.utils.unit_functions import calculate_bunker_range
from bot.utils.unit_tags import bio
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

class BunkerMicro:
    bot: Superbot

    def __init__(self, bot: Superbot):
        self.bot = bot

    def should_unload(self, bunker: Unit) -> bool:
        # If bunker under 20 hp, unload
        if (bunker.health <= 20):
            return True
        
        bunker_ground_range, bunker_air_range = calculate_bunker_range(self.bot, bunker)
        SAFETY_RADIUS: float = 1.5

        enemy_units_in_range: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
            lambda unit: (
                (unit.is_flying and bunker.distance_to_squared(unit) <= (bunker_air_range + unit.radius) ** 2)
                or (not unit.is_flying and bunker.distance_to_squared(unit) <= (bunker_ground_range + unit.radius) ** 2)
            )
        )
        enemy_units_potentially_in_range: Units  = (self.bot.enemy_units + self.bot.enemy_structures).filter(
            lambda unit: bunker.distance_to(unit) <= bunker_ground_range + unit.radius + SAFETY_RADIUS
        )

        # unload bunker if no enemy can shoot the bunker and the bunker can't shoot any unit => bunker is safe and doesn't need to be loaded
        enemy_units_menacing: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
            lambda unit: unit.target_in_range(bunker) or unit.distance_to(bunker) <= 10
        )
            
        # unload bunker if no unit around
        if (enemy_units_menacing.amount == 0 and enemy_units_in_range.amount == 0 and enemy_units_potentially_in_range.amount == 0):
            if (len(bunker.rally_targets) == 0):
                expansion: Expansion = self.bot.expansions.closest_to(bunker)
                if (expansion.position.distance_to(bunker) < 5):
                    rally_point: Point2 = expansion.retreat_position
                    bunker(AbilityId.RALLY_UNITS, rally_point)
            if (bunker.cargo_used >= 1):
                return True

        return False

    def select_target(self, bunker: Unit, enemy_units_in_range: Units) -> Unit:
        # sort with armored units first if we have marauders inside
        # sort with light units first if we have ghosts inside
        passengers_types: List[UnitTypeId] = [passenger.type_id for passenger in bunker.passengers]
        
        enemy_light_units: Units = enemy_units_in_range.filter(lambda enemy_unit: enemy_unit.is_light)
        enemy_armored_units: Units = enemy_units_in_range.filter(lambda enemy_unit: enemy_unit.is_armored)
        enemy_to_fight: Units = enemy_units_in_range
        
        # choose a better target if the unit has bonus damage
        if (UnitTypeId.MARAUDER in passengers_types):
            enemy_to_fight = enemy_armored_units if enemy_armored_units.amount >= 1 else enemy_units_in_range
        elif (UnitTypeId.GHOST in passengers_types):
            enemy_to_fight = enemy_light_units if enemy_light_units.amount >= 1 else enemy_units_in_range
        else:
            enemy_to_fight = enemy_units_in_range

        enemy_to_fight.sort(
            key=lambda enemy_unit: (
                BuffId.RAVENSHREDDERMISSILEARMORREDUCTION in enemy_unit.buffs,
                enemy_unit.shield,
                enemy_unit.shield + enemy_unit.health
            )
        )
        return enemy_to_fight.first
        
    
    async def handle_bunkers(self):
        for bunker in self.bot.structures(UnitTypeId.BUNKER):
            bunker_ground_range, bunker_air_range = calculate_bunker_range(self.bot, bunker)
            SAFETY_RADIUS: float = 1.5

            enemy_units_in_range: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
                lambda unit: (
                    (unit.is_flying and bunker.distance_to_squared(unit) <= (bunker_air_range + unit.radius) ** 2)
                    or (not unit.is_flying and bunker.distance_to_squared(unit) <= (bunker_ground_range + unit.radius) ** 2)
                )
            )
            enemy_units_potentially_in_range: Units  = (self.bot.enemy_units + self.bot.enemy_structures).filter(
                lambda unit: bunker.distance_to(unit) <= bunker_ground_range + unit.radius + SAFETY_RADIUS
            )

            # unload bunker if no enemy can shoot the bunker and the bunker can't shoot any unit => bunker is safe and doesn't need to be loaded
            enemy_units_menacing: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
                lambda unit: unit.target_in_range(bunker) or unit.distance_to(bunker) <= 10
            )
                
            # unload bunker if no unit around
            if (self.should_unload(bunker)):
                print("unload bunker")
                bunker(AbilityId.UNLOADALL_BUNKER)
                continue
                        
            
            # Attack the weakest enenmy in range
            if (enemy_units_in_range.amount >= 1):
                # if any units inside the bunkers is full life, stim them
                if (
                    self.bot.already_pending_upgrade(UpgradeId.STIMPACK) == 1
                    and any(passenger.health_percentage == 1 for passenger in bunker.passengers)
                ):
                    print("stimming passengers")
                    bunker(AbilityId.EFFECT_STIM)
                
                enemy: Unit = self.select_target(bunker, enemy_units_in_range)
                bunker.attack(enemy)
            
            # load the bunker with bio if there is space
            if (bunker.cargo_left == 0):
                continue
            
            bio_in_range: Units = self.bot.units(bio).filter(
                # we had a small buffer for units that are a bit too far
                lambda unit: unit.type_id != UnitTypeId.HELLIONTANK and unit.distance_to(bunker) <= bunker.radius + 0.5
            )
            if (bio_in_range.amount == 0):
                continue
            bio_in_danger: Units = bio_in_range.filter(
                lambda unit: (
                    self.bot.enemy_units.filter(
                        lambda enemy: enemy.can_attack_ground
                        and enemy.distance_to(unit) <= enemy.ground_range + SAFETY_RADIUS
                    ).amount > 0
                )
            )
            if (
                bio_in_danger.amount == 0
                and enemy_units_potentially_in_range.amount == 0
            ):
                continue

            # load the bunker with bio
            # prioritize marines, then marauders, unless enemy army is mostly armored
            default_load_priority: List[UnitTypeId] = [
                UnitTypeId.GHOST,
                UnitTypeId.MARINE,
                UnitTypeId.MARAUDER,
                UnitTypeId.REAPER,
            ]
            armored_load_priority: List[UnitTypeId] = [
                UnitTypeId.MARAUDER,
                UnitTypeId.GHOST,
                UnitTypeId.MARINE,
                UnitTypeId.REAPER,
            ] 
            enemy_army: Army = Army(enemy_units_menacing, self.bot)
            load_priority: List[UnitTypeId] = armored_load_priority if enemy_army.armored_ground_ratio >= 0.5 else default_load_priority
            
            cargo_left: int = bunker.cargo_left
            for unit_type in load_priority:
                unit_cargo: int = get_building_cargo(unit_type)
                if (unit_cargo > cargo_left):
                    continue
                for unit in bio_in_range(unit_type):
                    bunker(AbilityId.LOAD_BUNKER, unit)
                    cargo_left -= unit_cargo
                    if (unit_cargo > cargo_left):
                        break