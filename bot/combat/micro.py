import math
from typing import Any, List, Optional, Union
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.point2_functions.utils import center
from bot.utils.unit_supply import get_unit_supply
from sc2.cache import CachedClass, custom_cache_once_per_frame
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, dont_attack, hq_types, menacing, bio_stimmable, building_priorities, creep

from s2clientprotocol import raw_pb2 as raw_pb
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import ui_pb2 as ui_pb

MAXIMUM_SNIPE_COUNT: int = 2
WEAPON_READY_THRESHOLD: float = 6.0

class Micro(CachedClass):
    bot: Superbot
    snipe_targets: dict[int, int] = {}
    emp_targets: dict[int, int] = {}
    
    def __init__(self, bot: Superbot) -> None:
        super().__init__(bot)

    
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
    
    async def medivac_unload(self, medivac: Unit):
        if (medivac.cargo_used == 0):
            return
        # unload all units at medivac position
        if (
            self.bot.raw_affects_selection is not True
            or self.bot.enable_feature_layer is not True
        ):
            medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
            return
        passengers: Units = Units(medivac.passengers, self.bot).sorted(
            lambda unit: (get_unit_supply(unit.type_id), unit.health_percentage),
            reverse=True
        )
        await self.unload_unit(medivac, passengers.first)

    ## This function was stolen from python-sc2 at
    ## https://github.com/BurnySc2/python-sc2/pull/108/files
    ## I have no idea how this works
    async def unload_unit(self, transporter_unit: Unit, unload_unit: Union[int, Unit]):
        assert isinstance(transporter_unit, Unit)
        assert isinstance(unload_unit, (int, Unit))
        assert hasattr(self.bot, "raw_affects_selection") and self.bot.raw_affects_selection is True
        assert hasattr(self.bot, "enable_feature_layer") and self.bot.enable_feature_layer is True
        if isinstance(unload_unit, Unit):
            unload_unit_tag = unload_unit.tag
        else:
            unload_unit_tag = unload_unit

        unload_unit_index = next(
            (index for index, unit in enumerate(transporter_unit._proto.passengers) if unit.tag == unload_unit_tag),
            None
        )

        if unload_unit_index is None:
            print(f"Unable to find unit {unload_unit} in transporter {transporter_unit}")
            return

        await self.bot.client._execute(
            action=sc_pb.RequestAction(
                actions=[
                    sc_pb.Action(
                        action_raw=raw_pb.ActionRaw(
                            unit_command=raw_pb.ActionRawUnitCommand(ability_id=0, unit_tags=[transporter_unit.tag])
                        )
                    ),
                    sc_pb.Action(
                        action_ui=ui_pb.ActionUI(
                            cargo_panel=ui_pb.ActionCargoPanelUnload(unit_index=unload_unit_index)
                        )
                    ),
                ]
            )
        )

    
    async def retreat(self, unit: Unit):
        if (self.bot.townhalls.amount == 0):
            return
        
        enemy_units_in_range: Units = self.bot.enemy_units.in_attack_range_of(unit)
        enemy_units_in_sight: Units = self.bot.enemy_units.filter(lambda enemy_unit: enemy_unit.distance_to(unit) <= 10)
        
        if (unit.type_id in bio_stimmable and enemy_units_in_range.amount >= 1):
            self.stim_bio(unit)
        
        # Don't get in the way of flying townhalls
        local_flying_townhall: Units = self.bot.structures([UnitTypeId.ORBITALCOMMANDFLYING, UnitTypeId.COMMANDCENTERFLYING]).in_distance_between(unit.position, 0, 10)
        retreat_position = self.retreat_position if local_flying_townhall.amount == 0 else self.retreat_position.towards(local_flying_townhall.center, -5)
        
        # handle smooth flying units retreat
        if (unit.type_id == UnitTypeId.MEDIVAC):
            # unload at 2/3 of the way
            if (
                unit.distance_to(retreat_position) * 2 < unit.distance_to(self.bot.expansions.enemy_main.position)
                and enemy_units_in_sight.amount == 0
            ):
                await self.medivac_unload(unit)
            if (not await self.medivac_safety_disengage(unit) and unit.distance_to(retreat_position) > 3):                
                unit.move(retreat_position)
                if (unit.distance_to(retreat_position) > 15):
                    await self.medivac_boost(unit)
            return
        if (unit.is_flying and self.safety_disengage(unit)):
            return
        if (unit.distance_to(retreat_position) < 5):
            return
        if (enemy_units_in_range.amount >= 1):
            safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, enemy_units_in_range.closest_to(unit))
            unit.move(safest_spot)
        else:
            unit.move(retreat_position)
    
    async def medivac_pickup(self, medivac: Unit, local_army: Units):
        # stop unloading if we are
        medivac.stop()
        await self.medivac_boost(medivac)
        units_to_pickup: Units = local_army.in_distance_between(medivac, 0, 3).sorted(key = lambda unit: unit.cargo_size, reverse = True)
        for unit in units_to_pickup:
            medivac(AbilityId.LOAD_MEDIVAC, unit)
        units_next: Units = local_army.in_distance_between(medivac, 3, 10).sorted(key = lambda unit: unit.cargo_size, reverse = True)
        if (units_next.amount == 0):
            return
        medivac.move(units_next.center.towards(units_next.closest_to(medivac)))
    
    async def medivac_safety_disengage(self, medivac: Unit) -> bool:
        if (not self.safety_disengage(medivac)):
            return False
        # Unload if we're very low on life
        if (medivac.cargo_used >= 1 and medivac.health_percentage <= 0.25):
            await self.medivac_unload(medivac)
        return True

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

    async def medivac_disengage(self, medivac: Unit, local_army: Units):
        # boost if we can
        await self.medivac_boost(medivac)
        
        if (await self.medivac_safety_disengage(medivac)):
            return
        
        # if medivac not in danger, heal the closest damaged unit
        await self.medivac_heal(medivac, local_army)

    async def medivac_fight(self, medivac: Unit, local_army: Units):
        # unload if we can, then move towards the closest ground unit
        
        # if our medivac is filled and can unload, unload
        if (medivac.cargo_used >= 1):
            if (self.bot.in_pathing_grid(medivac.position)):
                await self.medivac_unload(medivac)
            
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

        # if there's too many medivacs in our army, back
        army: Army = Army(local_army, self.bot)
        passengers: Units = army.passengers
        local_ground_units: Units = local_army.filter(lambda unit: unit.is_flying == False) + passengers
        local_medivacs: Units = local_army(UnitTypeId.MEDIVAC).sorted(key = lambda unit: unit.health_percentage)
        medivacs_amount_to_back: int = max(0, local_medivacs.amount - local_ground_units.amount)
        if (medivacs_amount_to_back > 0):
            if (medivac.tag in local_medivacs.take(medivacs_amount_to_back).tags):
                await self.retreat(medivac)
                return

        # boost if we need to
        if (medivac.is_active):
            medivac_target: Point2|int = medivac.orders[0].target
            target_position: Point2|None = None
            if (isinstance(medivac_target, Point2)):
                target_position = medivac_target
            else:
                target_unit = self.bot.units.find_by_tag(medivac_target)
                if (target_unit):
                    target_position = target_unit.position
                
            if (target_position and target_position.distance_to(medivac) > 10):
                await self.medivac_boost(medivac)
        
        if (await self.medivac_safety_disengage(medivac)):
            return
        await self.medivac_heal(medivac, local_army)

    async def medivac_fight_unload(self, medivac: Unit, drop_target: Point2):
        # if there's a base closer than our drop target, we attack it
        # if we don't know any enemy base, we just drop the enemy main
        closest_enemy_base: Expansion = (
            self.bot.expansions.enemy_bases.closest_to(medivac)
            if self.bot.expansions.enemy_bases.amount >= 1
            else self.bot.expansions.enemy_main
        )
        closest_enemy_building: Unit = self.bot.enemy_structures.closest_to(medivac) if self.bot.enemy_structures.amount >= 1 else None
        MARGIN: int = 10
        if (closest_enemy_base.position.distance_to(medivac) < drop_target.distance_to(medivac) + MARGIN):
            drop_target = closest_enemy_base.mineral_line
        if (closest_enemy_building and closest_enemy_building.position.distance_to(medivac) < drop_target.distance_to(medivac) + MARGIN):
            drop_target = closest_enemy_building.position

        # boost towards the drop target and move towards it
        await self.medivac_boost(medivac)
        medivac.move(drop_target)

        # if we're close enough, unload and fight
        if (
            medivac.distance_to(drop_target) <= 30
            and self.bot.get_terrain_height(medivac.position) == self.bot.get_terrain_height(drop_target)
        ):
            await self.medivac_unload(medivac)

    
    async def medivac_heal(self, medivac: Unit, local_army: Units):
        # heal damaged ally in local army
        damaged_allies: Units = local_army.filter(
            lambda unit: (
                unit.is_biological
                and unit.health_percentage < 1
            )
        )

        if (damaged_allies.amount >= 1):
            damaged_allies.sort(key = lambda unit: (unit.health_percentage, unit.distance_to(medivac)))
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
                await self.retreat(medivac)
    
    async def medivac_boost(self, medivac: Unit):
        available_abilities = (await self.bot.get_available_abilities([medivac]))[0]
        if (AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS in available_abilities):
            medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)

    async def bio_defense(self, bio: Unit, local_army: Units):
        # # defend the closest base under attack if it's not too close to us
        # bases_under_attack: Expansions = self.bot.expansions.taken.under_attack
        # if (bases_under_attack.amount >= 1):
        #     closest_base_under_attack: Expansion = bases_under_attack.closest_to(bio)
        #     if (closest_base_under_attack.position.distance_to(bio) > 10):
        #         bio.attack(closest_base_under_attack.retreat_position)
        #         return
        
        enemy_units: Units = self.enemy_all.sorted(key = lambda enemy_unit: (enemy_unit.distance_to(bio), enemy_unit.health + enemy_unit.shield))
        if (enemy_units.amount == 0):
            print("[Error] no enemy units to attack")
            await self.bio_fight(bio, local_army)
            return
        
        close_defensive_structure: Units = self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).filter(lambda defense: defense.distance_to(bio) <= 10 and defense.build_progress >= 0.9)
        closest_defensive_structure: Unit = close_defensive_structure.closest_to(bio) if close_defensive_structure else None
        if (closest_defensive_structure):
            # handle stim
            self.stim_bio(bio)
            self.defend_around_bunker(bio, enemy_units, closest_defensive_structure)
        else:
            await self.bio_fight(bio, local_army)
            
    async def ghost_defense(self, ghost: Unit, local_army: Units):
        if (self.ghost_emp(ghost)):
            return
        if (self.ghost_snipe(ghost)):
            return
        await self.bio_defense(ghost, local_army)


    async def reaper_grenade(self, reaper: Unit) -> bool:
        available_abilities = (await self.bot.get_available_abilities([reaper]))[0]
        if (AbilityId.KD8CHARGE_KD8CHARGE not in available_abilities):
            return False
        
        # best_target, score = self.bot.map.influence_maps.best_grenade_target(reaper)
        # if (score < 5):
        #     return False
        KD8_RANGE: int = 5
        potential_targets: Units = self.enemy_all.filter(
            lambda enemy_unit: (
                not enemy_unit.is_flying
                and enemy_unit.distance_to(reaper) <= KD8_RANGE + enemy_unit.radius + reaper.radius
            )
        ).sorted(
            lambda enemy_unit: (enemy_unit.health + enemy_unit.shield)
        )
        if (potential_targets.amount == 0):
            return False
        best_target: Point2 = potential_targets.first.position
        reaper(AbilityId.KD8CHARGE_KD8CHARGE, best_target)
        return True
    
    async def reaper(self, reaper: Unit):
        # Try grenade first
        if (await self.reaper_grenade(reaper)):
            return
        
        # If there isn't any visible unit (ghost units are probably menacing), move to safest spot
        if (self.enemy_all.amount == 0):
            safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(reaper)
            reaper.move(safest_spot)
            return

        # if no enemy is in range, we are on cooldown and are in range, shoot the lowest unit
        SAFETY: int = 2
        LIFE_THRESHOLD: int = 15
        enemy_units_in_range: Units = self.get_enemy_units_in_range(reaper)
        threats: Units = self.enemies_threatening_ground_in_range(reaper, safety_distance=SAFETY, range_override=20)
        
        # --- CASE 1: Weapon Ready ---
        if (reaper.weapon_ready):
            # if we can safely shoot, just shoot
            local_danger: float = self.bot.map.influence_maps.danger.ground[reaper.position]
            if (threats.amount == 0 or (reaper.health >= LIFE_THRESHOLD and reaper.health > local_danger)):
                if (enemy_units_in_range.amount >= 1):
                    # shoot weakest enemy in range
                    target: Unit = enemy_units_in_range.sorted(lambda u: (u.health + u.shield, u.distance_to_squared(reaper))).first
                    reaper.attack(target)
                else:
                    # move toward closest enemy to chase
                    reaper.attack(self.enemy_all.closest_to(reaper))

            
            # if we can't safely shoot, move away
            else:
                # safest_spot is preferably away from threats
                kite_target = threats.closest_to(reaper)
                safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(reaper, kite_target)
                reaper.move(safest_spot)
        
        # --- CASE 2: Short Cooldown (stutter step micro) ---
        elif (reaper.weapon_cooldown <= WEAPON_READY_THRESHOLD):
            best_target: Unit = self.enemy_all.closest_to(reaper)
            best_attack_spot: Point2 = self.bot.map.influence_maps.best_attacking_spot(reaper, best_target)
            reaper.move(best_attack_spot)
       
        # --- CASE 3: Long cooldown → retreat & wait ---
        else:
            closest_enemy: Unit = self.enemy_all.closest_to(reaper)
            safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(reaper, closest_enemy)
            reaper.move(safest_spot)


    async def bio_fight(self, unit: Unit, local_army: Units, chase: bool = False):
        enemy_units_in_range = self.get_enemy_units_in_range(unit)
        potential_targets: Units = self.get_potential_targets(unit)
        buildings_in_range = self.bot.enemy_structures.filter(
            lambda building: unit.target_in_range(building)
        ).sorted(
            lambda building: (building.type_id not in building_priorities, building.health + building.shield)
        )
        local_medivacs: Units = local_army(UnitTypeId.MEDIVAC)
        loaded_medivacs: Units = local_medivacs.filter(lambda unit: unit.cargo_used > 0)
        
        # First, if we're chasing and only have a building in range, shoot at it
        if (chase and potential_targets.amount == 0 and buildings_in_range.amount >= 1):
            self.stim_bio(unit)
            unit.attack(buildings_in_range.first)
            return

        # Determine if we should kite back or pressure forward
        # This depends on the enemy range + movement speed
        # If their average range is less than our range, kite back
        # If their average speed is less than our speed, and their range similar, kite back
        # Otherwise, pressure forward
        
        average_ground_range: float = Army(local_army, self.bot).average_ground_range
        shorter_range: bool = any([enemy_unit.ground_range < average_ground_range for enemy_unit in enemy_units_in_range])
        other_enemies: Units = self.enemy_fighting.sorted(
            lambda enemy_unit: (enemy_unit.distance_to(unit), enemy_unit.shield, enemy_unit.health + enemy_unit.shield)
        )

        # ----- CASE 1: MELEE ENGAGEMENT (kite backward) -----
        if (shorter_range and self.handle_melee_engagement(
            unit,
            enemy_units_in_range,
            other_enemies,
        )):
            return


        # ----- CASE 2: PURE RANGED ENGAGEMENT (pressure forward) -----
        if (self.handle_ranged_engagement(
            unit,
            potential_targets,
            other_enemies,
        )):
            return

        # SECONDARY CASE: No targets, but enemy units exist
        if (buildings_in_range.amount >= 1 and unit.weapon_ready):
            self.stim_bio(unit)
            unit.attack(buildings_in_range.first)
            return

        # if everything isn't unloaded, regroup before attacking
        if (loaded_medivacs):
            unit.move(local_army.center)
            return

        self.stim_bio(unit)
        if (other_enemies.amount == 0):
            # No valid targets regroup
            unit.move(local_army.center)
            return
        target: Unit = other_enemies.closest_to(unit)
        best_position: Point2 = self.bot.map.influence_maps.best_attacking_spot(unit, target)
        unit.move(best_position)

        
    def handle_melee_engagement(
        self,
        unit: Unit,
        enemy_units_in_range: Units,
        other_enemies: Units,
    ) -> bool:
        
        # If someone is in range → hit'n'run
        if (enemy_units_in_range.amount >= 1):
            self.stim_bio(unit)
            self.hit_n_run(unit, enemy_units_in_range)
            return True
        
        if (other_enemies.amount >= 1):        
            closest_target: Unit = other_enemies.closest_to(unit)
            if (closest_target.can_be_attacked):
                unit.attack(closest_target)
            else:
                unit.move(closest_target.position)
            return True
        return False

    
    def handle_ranged_engagement(
        self,
        unit: Unit,
        potential_targets: Units,
        other_enemies: Units,
    ) -> bool:
        # PRIMARY CASE: There are valid targets
        if (potential_targets.amount >= 1):
            self.stim_bio(unit)
            self.kite_forward(unit, potential_targets)
            return True
        
        if (other_enemies.amount >= 1):        
            closest_target: Unit = other_enemies.closest_to(unit)
            if (closest_target.can_be_attacked):
                unit.attack(closest_target)
            else:
                unit.move(closest_target.position)
            return True
        return False
    
        
    async def viking(self, viking: Unit, local_units: Units):
        # find a target if our weapon isn't on cooldown
        if (viking.weapon_cooldown <= WEAPON_READY_THRESHOLD):
            potential_targets: Units = self.bot.enemy_units.filter(
                lambda unit: (
                    unit.can_be_attacked and (
                        unit.is_flying
                        or unit.type_id == UnitTypeId.COLOSSUS
                    )
                )
            ).sorted(
                lambda unit: unit.health + unit.shield
            )
            enemy_in_range: Units = potential_targets.filter(
                lambda unit: viking.target_in_range(unit)
            )
            if (enemy_in_range.amount >= 1):
                viking.attack(enemy_in_range.first)
            elif (potential_targets.amount >= 1):
                viking.attack(potential_targets.closest_to(viking))
            else:
                # if (self.bot.scouting.known_enemy_army.flying_fighting_supply == 0):
                #     viking(AbilityId.MORPH_VIKINGASSAULTMODE)
                if (not self.safety_disengage(viking)):
                    viking.move(local_units.center)

        # if we're not on cooldown, either disengage or follow our army
        elif (not self.safety_disengage(viking)):
            viking.move(local_units.center)

    async def viking_retreat(self, viking: Unit):
        if (viking.weapon_cooldown > WEAPON_READY_THRESHOLD):
            await self.retreat(viking)
            return

        # find a target if our weapon isn't on cooldown
        enemy_in_range: Units = self.bot.enemy_units.flying.filter(
            lambda enemy: viking.target_in_range(enemy)
        ).sorted(
            lambda unit: unit.health + unit.shield
        )
        
        if (enemy_in_range.amount >= 1):
            viking.attack(enemy_in_range.first)
        else:
            await self.retreat(viking)

    async def ghost(self, ghost: Unit, local_army: Units):
        if (self.ghost_emp(ghost)):
            return
        if (self.ghost_snipe(ghost)):
            return
        await self.bio_fight(ghost, local_army)

    def ghost_emp(self, ghost: Unit) -> bool:
        EMP_HIT_THRESHOLD: int = 50
        MAXIMUM_EMP_COUNT: int = 1
        
        potential_emp_targets: Units = self.get_local_enemy_units(ghost.position, 10, only_menacing=True).filter(
            lambda enemy_unit: (
                enemy_unit.energy > 0 or enemy_unit.shield > 0
                and (
                    enemy_unit.tag not in self.emp_targets.keys()
                    or self.emp_targets[enemy_unit.tag] < MAXIMUM_EMP_COUNT
                )
            )
        )
        if (potential_emp_targets.amount < 1):
            return False
        # find the best position to cast EMP
        best_target: Optional[Unit] = None
        best_hit: float = 0
        for enemy_unit in potential_emp_targets:
            hit: float = 0
            for unit in potential_emp_targets.closer_than(1.5, enemy_unit.position):
                hit += min(unit.shield, 100)
                hit += min(unit.energy, 100)
            if (hit > best_hit):
                best_hit = hit
                best_target = enemy_unit
        if (best_target and best_hit >= EMP_HIT_THRESHOLD):
            print("Casting EMP")
            ghost(AbilityId.EMP_EMP, best_target.position)
            if (best_target.tag in self.emp_targets.keys()):
                self.emp_targets[best_target.tag] += 1
            else:
                self.emp_targets[best_target.tag] = 1
            return True
        return False
    
    def ghost_snipe(self, ghost: Unit) -> bool:
        # if we don't have energy or are already sniping, we just skip
        if (ghost.energy < 50 or ghost.is_using_ability(AbilityId.EFFECT_GHOSTSNIPE)):
            return False
        GHOST_SNIPE_THRESHOLD: int = 60
        potential_snipe_targets: Units = self.get_local_enemy_units(
            ghost.position,
            radius=10,
            only_menacing=True,
        ).filter(
            lambda enemy_unit: (
                enemy_unit.is_biological
                and enemy_unit.health + enemy_unit.shield >= GHOST_SNIPE_THRESHOLD
                and not enemy_unit.has_buff(BuffId.GHOSTSNIPEDOT)
                and (
                    enemy_unit.tag not in self.snipe_targets.keys()
                    or self.snipe_targets[enemy_unit.tag] < MAXIMUM_SNIPE_COUNT
                )
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
        if (target.tag in self.snipe_targets.keys()):
            self.snipe_targets[target.tag] += 1
        else:
            self.snipe_targets[target.tag] = 1
        return True
            
    def stim_bio(self, bio_unit: Unit, force: bool = False):
        DANGER_THRESHOLD: float = 5 if not force else 0
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
        RANGE_BUFFER: int = 2
        health_safety: int = MARAUDER_HEALTH_SAFETY if bio_unit.type_id == UnitTypeId.MARAUDER else 0
        
        local_usable_medivacs: Units = self.bot.units(UnitTypeId.MEDIVAC).filter(
            lambda medivac: (
                medivac.distance_to(bio_unit) <= 10
                and medivac.energy >= MEDIVAC_ENERGY_THRESHOLD
                and medivac.health >= MEDIVAC_HEALTH_THRESHOLD
            )
        )

        targets_in_range: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
            lambda target: bio_unit.distance_to(target) <= bio_unit.radius + target.radius + RANGE_BUFFER + (
                bio_unit.air_range if target.is_flying else bio_unit.ground_range
            )
        )
        
        if (
            (
                bio_unit.health >= WITHOUT_MEDIVAC_HEALTH_THRESHOLD + health_safety
                or (
                    local_usable_medivacs.amount >= 1
                    and bio_unit.health >= WITH_MEDIVAC_HEALTH_THRESHOLD + health_safety
                )
            )
            and (
                # only stimming if there's enough danger or a target in range
                targets_in_range.amount >= 1
                or self.bot.map.influence_maps.danger.ground[bio_unit.position] >= DANGER_THRESHOLD
            )
        ):
            bio_unit(AbilityId.EFFECT_STIM)

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
        potential_targets: Units = self.get_local_enemy_units(raven.position, 5)
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
    
    async def raven(self, raven: Unit, local_army: Units):
        # if we have enough energy, cast anti armor missile on the closest group of enemy units
        ANTI_ARMOR_MISSILE_ENERGY_COST: int = 75
        AUTO_TURRET_ENERGY_COST: int = 50

        available_abilities = (await self.bot.get_available_abilities([raven]))[0]
        if (AbilityId.EFFECT_ANTIARMORMISSILE in available_abilities and raven.energy >= ANTI_ARMOR_MISSILE_ENERGY_COST):
            if (await self.raven_antiarmor_missile(raven)):
                return
        
        if (AbilityId.BUILDAUTOTURRET_AUTOTURRET in available_abilities and raven.energy >= AUTO_TURRET_ENERGY_COST):
            if (await self.raven_autoturret(raven)):
                return
        
        if (not self.safety_disengage(raven)):
            raven.move(local_army.center)

    
    async def harass(self, unit: Unit, workers: Units):
        if (unit.type_id in bio_stimmable and unit.health_percentage >= 0.85):
            self.stim_bio(unit)
        
        # calculate the range of the unit based on its movement speed + range + cooldown
        range: float = unit.radius + unit.ground_range + unit.distance_to_weapon_ready
        closest_worker: Unit = workers.closest_to(unit)
        worker_potential_targets: Units = workers.filter(
            lambda worker: unit.distance_to(worker) <= range + worker.radius
        ).sorted(
            lambda worker: ((worker.health + worker.shield), worker.distance_to(unit))
        )

        buildings_in_range: Units = self.bot.enemy_structures.filter(
            lambda building: unit.target_in_range(building)
        ).sorted(
            lambda building: (building.type_id not in building_priorities, building.health + building.shield)
        )
        
        # first case : we're dangerously close to a worker + low on life => retreat to a safer spot
        if (unit.health <= 10 and workers.closest_distance_to(unit) <= 1.5):
            safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, workers.closest_to(unit), range_modifier=unit.health_percentage)
            unit.move(safest_spot)
            return
        
        # in these case we should target a worker
        if (worker_potential_targets.amount >= 1 or unit.weapon_cooldown > WEAPON_READY_THRESHOLD or buildings_in_range.amount == 0):
            # define the best target
            target: Unit = worker_potential_targets.first if worker_potential_targets.amount >= 1 else closest_worker
            # if we're not on cooldown and workers are really close, run away
            if (unit.weapon_cooldown > WEAPON_READY_THRESHOLD):
                if (workers.closest_distance_to(unit) <= 1.5 and unit.health_percentage < 1):
                    safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, workers.closest_to(unit), range_modifier=unit.health_percentage)
                    unit.move(safest_spot)
                else:
                    # move towards the unit but not too close
                    best_position: Point2 = self.bot.map.influence_maps.best_attacking_spot(unit, target, risk=1)
                    unit.move(best_position)
            # if we're on cooldown, shoot at it
            else:
                unit.attack(target)
        else:
            unit.attack(buildings_in_range.first)
    
    async def bio_disengage(self, bio_unit: Unit):
        enemy_units_in_range = self.get_enemy_units_in_range(bio_unit)
        
        # handle stim
        self.stim_bio(bio_unit)

        if (enemy_units_in_range.amount >= 1):
            self.hit_n_run(bio_unit, enemy_units_in_range)
        else:
            await self.retreat(bio_unit)
    
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
                    safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(bunker)
                    unit.move(safest_spot)
                    # Micro.move_away(unit, enemy_units.closest_to(unit))
            else:
                if (unit.weapon_ready):
                    unit.attack(enemy_units.closest_to(unit))
                else:
                    safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(bunker)
                    unit.move(safest_spot)
                    # Micro.move_away(unit, enemy_units.closest_to(unit))
    
    def kite_forward(self, unit: Unit, enemy_targets: Units):
        if (enemy_targets.amount == 0):
            return
        enemy_light_units: Units = enemy_targets.filter(lambda enemy_unit: enemy_unit.is_light)
        enemy_armored_units: Units = enemy_targets.filter(lambda enemy_unit: enemy_unit.is_armored)
        enemy_to_fight: Units = enemy_targets
        
        enemy_to_fight.first.buffs

        # choose a better target if the unit has bonus damage
        if (unit.bonus_damage):
            match(unit.bonus_damage[1]):
                case 'Light':
                    enemy_to_fight = enemy_light_units if enemy_light_units.amount >= 1 else enemy_targets
                case 'Armored':
                    enemy_to_fight = enemy_armored_units if enemy_armored_units.amount >= 1 else enemy_targets
                case _:
                    enemy_to_fight = enemy_targets

        enemy_to_fight.sort(
            key=lambda enemy_unit: (
                BuffId.RAVENSHREDDERMISSILEARMORREDUCTION in enemy_unit.buffs,
                enemy_unit.shield,
                enemy_unit.shield + enemy_unit.health
            )
        )
        target: Unit = enemy_to_fight.first
        if (unit.weapon_ready):
            unit.attack(target)
        else:
            best_position: Point2 = self.bot.map.influence_maps.best_attacking_spot(unit, target)
            unit.move(best_position)
    
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
                    BuffId.RAVENSHREDDERMISSILEARMORREDUCTION in enemy_unit.buffs,
                    enemy_unit.shield,
                    enemy_unit.shield + enemy_unit.health
                )
            )
            unit.attack(enemy_to_fight.first)
        else:
            safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, enemy_units_in_range.closest_to(unit))
            unit.move(safest_spot)

    def attack_nearest_base(self, unit: Unit):
        target_position: Point2 = self.get_nearest_base_target(unit)
        if (unit.distance_to(target_position) > 50):
            target_position = unit.position.towards(target_position, 50)
        unit.attack(target_position)

    def attack_a_position(self, unit: Unit, target_position: Point2):
        if (unit.distance_to(target_position) > 50):
            target_position = unit.position.towards(target_position, 50)
        enemy_units_in_range = self.get_enemy_units_in_range(unit)
        if (unit.weapon_cooldown <= WEAPON_READY_THRESHOLD and enemy_units_in_range.amount >= 1):
            unit.attack(enemy_units_in_range.sorted(lambda unit: (unit.health + unit.shield)).first)
        else:
            unit.move(target_position)

    def get_nearest_base_target(self, unit: Unit) -> Point2:
        enemy_main_position: Point2 = self.bot.enemy_start_locations[0]
        enemy_bases: Units = self.bot.enemy_structures.filter(
            lambda structure: structure.type_id in hq_types
        )
        possible_enemy_expansion_positions: List[Point2] = self.bot.expansions.positions
        possible_enemy_expansion_positions.sort(
            key = lambda position: position.distance_to(enemy_main_position)
        )
        
        if (enemy_bases.amount >= 1):
            return enemy_bases.closest_to(unit).position
        elif (self.bot.expansions.enemy_main.is_unknown):
            return self.bot.expansions.enemy_main.position
        else:
            return self.bot.expansions.sorted(lambda expansion: expansion.distance_from_main, True).sorted_by_oldest_scout().first.position

    def move_away(selected: Unit, enemy: Unit|Point2, distance: int = 2):
        selected_position: Point2 = selected.position
        offset: Point2 = selected_position.negative_offset(enemy.position)
        target: Point2 = selected_position.__add__(offset)
        selected.move(selected_position.towards(target, distance))

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
        
    # @custom_cache_once_per_frame
    # def enemy_towers(self) -> Units:
    #     enemy_towers: Units = self.bot.enemy_structures.filter(lambda unit: unit.type_id in tower_types)
    #     return enemy_towers
    
    # @custom_cache_once_per_frame
    # def enemy_units(self) -> Units:
    #     enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.can_be_attacked and unit.type_id not in dont_attack)
    #     enemy_tumors: Units = self.bot.enemy_structures(creep)
    #     return enemy_units + self.enemy_towers + enemy_tumors
    
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
    
    def get_enemy_units_in_range(self, unit: Unit) -> Units:
        if (unit is None):
            return Units([], self.bot)
        
        return self.enemy_all.filter(
            lambda enemy: (
                (unit.can_attack_ground and not enemy.is_flying) or
                (unit.can_attack_air and enemy.is_flying)
            )
            and unit.target_in_range(enemy)
        )
    
    def get_local_enemy_units(self, position: Point2, radius: float = 20, only_menacing: bool = False) -> Units:
        enemies = self.enemy_all
        if (only_menacing):
            enemies = enemies.filter(self.is_fighting_unit)

        return enemies.closer_than(radius, position)

    def get_local_enemy_buildings(self, position: Point2) -> Units:
        buildings = self.bot.enemy_structures.filter(self.is_valid_enemy).closer_than(10, position)
        buildings.sort(key=lambda b: b.health)
        return buildings