import math
from typing import List, Set
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.macro.map.influence_maps.layers.buildings_layer import BuildingLayer
from bot.strategy.strategy_types import Situation
from bot.superbot import Superbot
from bot.utils.ability_tags import AbilityRepair
from bot.utils.matchup import Matchup
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from bot.utils.point2_functions.utils import center, points_to_build_addon
from bot.utils.unit_functions import is_being_constructed
from sc2.game_state import EffectData
from sc2.ids.ability_id import AbilityId
from sc2.ids.effect_id import EffectId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import must_repair, add_ons, worker_types, menacing, creep, cloaked_units, burrowed_units

class BuildingsHandler:
    bot: Superbot
    DANGER_THRESHOLD: float = 8

    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot
    
    async def finish_construction(self):
        if (self.bot.workers.collecting.amount == 0):
            return
        
        incomplete_buildings: Units = self.bot.structures.filter(
            lambda structure: (
                structure.build_progress < 1
                and structure.type_id not in add_ons
                and structure.type_id != UnitTypeId.ORBITALCOMMAND
                and structure.type_id != UnitTypeId.PLANETARYFORTRESS
                and is_being_constructed(self.bot, structure) == False
            )
        )


        for incomplete_building in incomplete_buildings:
            closest_worker: Unit = self.bot.workers.collecting.closest_to(incomplete_building)
            print("ordering SCV to finish", incomplete_building.name)
            closest_worker.smart(incomplete_building)
            
    async def repair_buildings(self):
        if (self.bot.minerals == 0):
            return
        workers = self.bot.workers + self.bot.units(UnitTypeId.MULE)
        available_workers: Units = workers.filter(
            lambda worker: (
                worker.is_moving
                or worker.is_collecting
                or worker.is_idle
                or worker.is_attacking
            )
        )
        workers_repairing: Units = workers.filter(
            lambda worker: (
                len(worker.orders) >= 1
                and worker.orders[0].ability.id in AbilityRepair
            )
        )
        max_workers_repairing: int = min(round(self.bot.supply_workers / 2), self.bot.supply_workers - 6)

        # we don't want under 6 workers mining
        # we don't want over 1/2 of our workers repairing
        if (available_workers.amount <= 6 or workers_repairing.amount >= self.bot.supply_workers / 2):
            print(f'max amount of repairnig workers reached [{workers_repairing.amount}/{max_workers_repairing}]')
            return
        
        burning_buildings_in_pathing = self.bot.structures.ready.filter(
            lambda unit: (
                (
                    unit.is_flying == False or
                    self.bot.in_pathing_grid(unit)
                ) and (
                    unit.health_percentage < 0.6 or
                    (unit.type_id in must_repair and unit.health_percentage < 1)
                )
            )
        )
        # When in danger we don't repair stuff that's too far
        REPAIR_RANGE_DANGER: float = 6
        REPAIR_RANGE_SAFE: float = 20
        for burning_building in burning_buildings_in_pathing:
            workers_repairing_building: Units = workers_repairing.filter(
                lambda unit: unit.order_target == burning_building.tag
            )
            repair_ratio: float = min(1, self.bot.supply_workers / 10)
            max_workers_repairing_building: int = (8 if burning_building.type_id in must_repair else 3) * repair_ratio
            local_avaiable_workers: Units = (
                available_workers.closer_than(REPAIR_RANGE_DANGER, burning_building)
                if (burning_building.type_id not in must_repair and self.bot.scouting.situation == Situation.UNDER_ATTACK)
                else available_workers.closer_than(REPAIR_RANGE_SAFE, burning_building)
            )
            if (
                workers_repairing_building.amount >= max_workers_repairing_building
                or workers_repairing.amount >= max_workers_repairing
                or local_avaiable_workers.amount == 0
            ):
                return
            
            print(f'pulling worker to repair {burning_building.name} [{workers_repairing_building.amount}/{max_workers_repairing}]')
            # use SCV in priority then Mules
            repairer: Unit = available_workers.sorted(lambda worker: (worker.type_id != UnitTypeId.SCV, worker.distance_to(burning_building))).first
            repairer.repair(burning_building)
            available_workers.remove(repairer)
            workers_repairing.append(repairer)
            workers_repairing_building.append(repairer)
    
    async def cancel_buildings(self):
        incomplete_buildings: Units = self.bot.structures.filter(
            lambda structure: (
                structure.health_percentage < structure.build_progress < 1
                and structure.type_id not in add_ons
                # and (
                #     self.bot.workers.amount == 0
                #     or self.bot.workers.closest_to(structure).is_constructing_scv == False
                #     or self.bot.workers.closest_distance_to(structure) >= structure.radius * math.sqrt(2)
                # )
                and (
                    (structure.health < 100 and structure.health_percentage < 0.1)
                    or (
                        structure.health_percentage < 0.3
                        and self.bot.scouting.situation == Situation.UNDER_ATTACK
                    )
                )
            )
        )
        for building in incomplete_buildings:
            building(AbilityId.CANCEL_BUILDINPROGRESS)
    
    async def morph_orbitals(self):
        if (self.bot.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9):
            for cc in self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.idle:
                if(self.bot.can_afford(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)):
                    print("Morph Orbital Command")
                    cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

    def scan_amount_to_bank(self) -> int:
        WORKER_THRESHOLD: int = 30
        scan_to_bank: int = 0
        orbital_command_amount: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount
        
        # if we're playing vs Zerg bank 1 scan once we reach worker threshold and 3 orbitals
        if (self.bot.matchup == Matchup.TvZ and self.bot.supply_workers >= WORKER_THRESHOLD and orbital_command_amount >= 3):
            scan_to_bank += 1

        # if we've know the enemy has cloaked units, bank more scans
        if (UpgradeId.BURROW in self.bot.scouting.known_enemy_upgrades and self.bot.supply_workers >= WORKER_THRESHOLD):
            scan_to_bank += 1

        if (self.bot.enemy_units(cloaked_units).amount >= 1):
            scan_to_bank += 1
        
        if (self.bot.enemy_units(burrowed_units).amount >= 1):
            scan_to_bank += 1
        
        # never bank more than 1 scan per orbital
        return min(scan_to_bank, orbital_command_amount)
    
    async def drop_mules(self):
        # find biggest mineral fields near a full base
        safe_mineral_fields: Units = self.bot.expansions.ready.safe.mineral_fields
        if (safe_mineral_fields.amount == 0):
            return
        richest_mineral_field: Unit = max(safe_mineral_fields, key=lambda x: x.mineral_contents)

        # bank scans if we have 3 or more orbitals and enough SCVs
        scan_to_bank: int = self.scan_amount_to_bank()
        scan_banked: int = 0
        
        # call down a mule on this guy
        for orbital_command in self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            if (
                orbital_command.energy >= 100
                or scan_banked >= scan_to_bank
            ):
                orbital_command(AbilityId.CALLDOWNMULE_CALLDOWNMULE, richest_mineral_field)
            else:
                scan_banked += 1

    def scan_creep(self, orbitals_with_energy: Units, units: Units, BASE_RADIUS: int, SCAN_RADIUS: int):
        CREEP_DENSITY_THRESHOLD: float = 0.5
        
        # find bases that have creep around and units who should clean creep
        # Check all owned bases
        creep_layer = self.bot.map.influence_maps.creep
        expansions_to_check: Expansions = self.bot.expansions.taken.copy()
        expansions_to_check.add(self.bot.expansions.next)
        
        for expansion in expansions_to_check:
            density, position = creep_layer.max_density_in_radius(expansion.position, BASE_RADIUS * 2)
            if (position is None):
                continue
            tumors: Units = self.bot.enemy_structures(creep).closer_than(BASE_RADIUS * 2, expansion.position)
            detected: bool = bool(self.bot.map.influence_maps.detection.detected[position])
            if (density > CREEP_DENSITY_THRESHOLD and tumors.amount == 0 and not detected):
                fighting_units_around: Units = units.closer_than(BASE_RADIUS, expansion.position)
                if (fighting_units_around.amount >= 1):
                    print("scanning creep around base")
                    orbital: Unit = orbitals_with_energy.random
                    orbital(AbilityId.SCANNERSWEEP_SCAN, position)
                    # only 1 scan per frame
                    return

        # find fighting units that are on creep without a building in 15 range and not close to an expansion slot (that could have died the last frame)
        enemy_buildings: Units = self.bot.enemy_structures
        on_creep_fighting_units: Units = units.filter(
            lambda unit: (
                self.bot.has_creep(unit.position)
                and self.bot.map.influence_maps.detection.detected[unit.position] == 0
                and (
                    enemy_buildings.amount == 0
                    or enemy_buildings.closest_distance_to(unit) > SCAN_RADIUS
                )
            )
        )

        # scan for creep tumors    
        # look for optimal spot to scan
        best_density: float = 0
        best_position: Point2 = None

        for unit in on_creep_fighting_units:
            # get highest creep density around
            range: float = unit.ground_range
            density, position = creep_layer.max_density_in_radius(unit.position, range)
            if (density > best_density):
                best_density = density
                best_position = position
        
        if (best_density >= CREEP_DENSITY_THRESHOLD):
            orbitals_with_energy.random(AbilityId.SCANNERSWEEP_SCAN, best_position)
            # scan only once per frame
            return
    
    def scan_invisible_units(self, orbitals_with_energy: Units) -> bool:
        detection_layer = self.bot.map.influence_maps.detection
        # find invisible enemy unit that we should kill
        enemy_units_to_scan: Units = self.bot.enemy_units.filter(
            lambda unit: (
                not unit.is_visible
                and (unit.is_cloaked or unit.is_burrowed)
                and detection_layer.detected[unit.position] == 0
            )
        )
        # TODO : lurker spines means burrowed lurker
        
        # invisible enemy units we should scan are in range of our fighting units
        for enemy_unit in enemy_units_to_scan:
            local_fighting_units: Units = self.bot.units.closer_than(10, enemy_unit).filter(
                lambda unit: (
                    unit.type_id not in worker_types
                    and (
                        unit.can_attack_air if enemy_unit.is_flying else unit.can_attack_ground
                    )
                )
            )
            local_enemy_units: Units = self.bot.enemy_units.closer_than(8, enemy_unit).filter(
                lambda unit: unit.tag != enemy_unit.tag
            )
            if (local_fighting_units.amount == 0):
                print(f'no fighting unit close to {enemy_unit.name}')
                continue
            if (local_enemy_units.amount > local_fighting_units.amount + 5):
                print(f'too much enemy units close to {enemy_unit.name}')
                continue
            print(f'scan enemy unit {enemy_unit.name}')
            orbitals_with_energy.random(AbilityId.SCANNERSWEEP_SCAN, enemy_unit.position)
            return True

    async def scan(self):
        BASE_RADIUS: int = 6
        SCAN_RADIUS: int = 15
        
        orbitals_with_energy: Units = self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).ready.filter(lambda x: x.energy >= 50)
        if (self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount == 0 or orbitals_with_energy.amount == 0):
            return
        
        # if we have no fighting units we can't clean creep
        ravens: Units = self.bot.units(UnitTypeId.RAVEN)
        enemy_units: Units = self.bot.enemy_units
        creep_cleaners: Units = self.bot.units.filter(
            lambda unit: (
                unit.type_id not in worker_types
                and unit.can_attack_ground
                and (
                    ravens.amount == 0
                    or ravens.closer_than(15, unit).amount == 0
                )
                and (
                    enemy_units.amount == 0
                    or enemy_units.closer_than(10, unit).amount == 0
                )
            )
        )

        if (self.scan_invisible_units(orbitals_with_energy)):
            return
        if (creep_cleaners.amount == 0):
            return
        self.scan_creep(orbitals_with_energy, creep_cleaners, BASE_RADIUS, SCAN_RADIUS)
        
   
    async def handle_supplies(self):
        supplies_raised: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready
        supplies_lowered: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOTLOWERED)
        minimal_distance: float = 6
        ground_enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.is_flying == False)
        for supply in supplies_raised:
            if (ground_enemy_units.amount == 0 or ground_enemy_units.closest_distance_to(supply) > minimal_distance):
                print("Lower Supply Depot")
                supply(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        for supply in supplies_lowered:
            if (ground_enemy_units.amount >= 1 and ground_enemy_units.closest_distance_to(supply) <= minimal_distance):
                print("Raise Supply Depot")
                supply(AbilityId.MORPH_SUPPLYDEPOT_RAISE)

    async def rally_points(self):
        rally_production_building_ids: List[UnitTypeId] = [
            UnitTypeId.BARRACKS,
            UnitTypeId.FACTORY,
            UnitTypeId.STARPORT,
        ]
        production_buildings: Units = self.bot.structures.ready.filter(
            lambda structure: structure.type_id in rally_production_building_ids
        )
        for production_building in production_buildings:
            bunkers: Units = self.bot.structures(UnitTypeId.BUNKER).ready.closer_than(10, production_building)
            rally_point: Point2
            if (bunkers.amount >= 1):
                rally_point: Point2 = bunkers.closest_to(production_building).position
            else:
                rally_point: Point2 = self.bot.expansions.closest_to(production_building.position).retreat_position
            if (len(production_building.rally_targets) == 0 or production_building.rally_targets[0].point != rally_point):
                production_building(AbilityId.RALLY_BUILDING, rally_point)
            
    async def lift_townhalls(self):
        townhalls_not_on_slot = self.bot.expansions.townhalls_not_on_slot.ready.idle
        # calculate the optimal worker count based on mineral field left in bases
        optimal_worker_count: int = (
            sum(expansion.optimal_mineral_workers for expansion in self.bot.expansions.taken)
            + sum(expansion.optimal_vespene_workers for expansion in self.bot.expansions.taken)
        )
        is_mining_optimal: bool = self.bot.supply_workers < optimal_worker_count - 5

        for townhall in townhalls_not_on_slot:
            # don't lift Orbitals after the third CC
            if (townhall.type_id == UnitTypeId.ORBITALCOMMAND):
                if (self.bot.townhalls.ready.amount >= 4):
                    continue
            
            # don't lift CCs before the 4th CC
            if (townhall.type_id == UnitTypeId.COMMANDCENTER):
                if (self.bot.townhalls.ready.amount < 4):
                    continue
            
            # check if we should lift the command center or upgrade it to orbital command
            if (is_mining_optimal and self.bot.townhalls.ready.amount != 4):
                # don't lift this command center because mining is already optimal
                # unless it's to plant the 4th PF
                continue
            landing_spot: Point2 = self.bot.expansions.next.position
            danger_around: float = self.bot.map.influence_maps.average_danger_around(landing_spot, radius=10, air=False)
            # enemy_units_around_spot: Units = self.bot.enemy_units.filter(lambda unit: unit.distance_to(landing_spot) < SAFETY_DISTANCE)
            
            if (danger_around >= self.DANGER_THRESHOLD):
                print("too much danger")
                return

            if (townhall.type_id == UnitTypeId.COMMANDCENTER):
                print("Lift Command Center")
                townhall(AbilityId.LIFT_COMMANDCENTER)
            else:
                print("Lift Orbital")
                townhall(AbilityId.LIFT_ORBITALCOMMAND)

    
    async def land_townhalls(self):
        flying_townhall: Units = self.bot.structures([UnitTypeId.ORBITALCOMMANDFLYING, UnitTypeId.COMMANDCENTERFLYING]).ready
        for townhall in flying_townhall:
            landing_spot: Point2 = (
                townhall.orders[0].target if len(townhall.orders) >= 1 and townhall.orders[0].ability.id in [AbilityId.LAND_COMMANDCENTER, AbilityId.LAND_ORBITALCOMMAND]
                else self.bot.expansions.next.position if flying_townhall.amount == 1
                else self.bot.expansions.free.closest_to(townhall.position).position if self.bot.expansions.free.amount >= 1
                else self.bot.expansions.last_taken.position if self.bot.expansions.taken.amount >= 1
                else self.bot.expansions.main.position
            )
            danger_around: float = self.bot.map.influence_maps.average_danger_around(landing_spot, radius=10, air=False)
            # enemy_units_around_spot: Units = self.bot.enemy_units.filter(lambda unit: unit.distance_to(landing_spot) < 10)
            if (danger_around < self.DANGER_THRESHOLD):
                if (not townhall.is_idle):
                    continue
                if (townhall.type_id == UnitTypeId.COMMANDCENTERFLYING):
                    townhall(AbilityId.LAND_COMMANDCENTER, landing_spot)
                else:
                    townhall(AbilityId.LAND_ORBITALCOMMAND, landing_spot)
            else:
                if (self.bot.expansions.taken.safe.amount == 0):
                    continue
                safest_base: Expansion = self.bot.expansions.taken.safe.closest_to(townhall.position)
                safe_spot: Point2 = dfs_in_pathing(self.bot, safest_base.position, UnitTypeId.COMMANDCENTER, landing_spot, 2)
                if (townhall.type_id == UnitTypeId.COMMANDCENTERFLYING):
                    townhall(AbilityId.LAND_COMMANDCENTER, safe_spot)
                else:
                    townhall(AbilityId.LAND_ORBITALCOMMAND, safe_spot)

    async def reposition_buildings(self) -> None:
        """
        Lift production buildings that cannot build an addon at their current
        position (blocked by creep, enemy structures, or a misplaced own
        building), and land flying production buildings that are not being
        managed by the AddonSwapManager.

        Responsibility split:
        - This method handles the *reposition* concern: a building ended up
          somewhere it cannot build its addon → lift it so it can find a
          better spot.
        - AddonSwapManager handles the *swap* concern: a building needs to
          vacate its addon for another building type.

        Buildings that are mid-swap (tracked by AddonSwapManager.managed_tags)
        are explicitly excluded so the two systems never fight each other.
        """
        # Tags currently managed by an active swap — we must not touch these.
        swap_managed_tags: set[int] = self.bot.addon_swap.managed_tags

        production_building_ids: list[UnitTypeId] = [
            UnitTypeId.BARRACKS,
            UnitTypeId.FACTORY,
            UnitTypeId.STARPORT,
        ]

        # --- Lift grounded buildings that cannot build their addon ----------
        production_buildings_without_addon: Units = self.bot.structures.ready.idle.filter(
            lambda structure: (
                structure.type_id in production_building_ids
                and structure.has_add_on == False
                and structure.tag not in swap_managed_tags
            )
        )

        # Never reposition the very first barracks (it walls the ramp).
        barracks_amount: int = (
            self.bot.structures([UnitTypeId.BARRACKS, UnitTypeId.BARRACKSFLYING]).amount
            + self.bot.already_pending(UnitTypeId.BARRACKS)
        )
        if (barracks_amount >= 2):
            for production_building in production_buildings_without_addon:
                addon_pos: Point2 = production_building.add_on_position
                if not (await self.bot.can_place_single(UnitTypeId.SUPPLYDEPOT, addon_pos)):
                    print(
                        f"[reposition_buildings] Cannot build addon — "
                        f"{production_building.name} (tag={production_building.tag}) lifts."
                    )
                    production_building(AbilityId.LIFT)

        # --- Land flying buildings that are idle and not mid-swap -----------
        flying_building_ids: list[UnitTypeId] = [
            UnitTypeId.BARRACKSFLYING,
            UnitTypeId.FACTORYFLYING,
            UnitTypeId.STARPORTFLYING,
        ]
        flying_buildings: Units = self.bot.structures.idle.filter(
            lambda building: (
                building.type_id in flying_building_ids
                and building.tag not in swap_managed_tags
            )
        )

        for flying_building in flying_buildings:
            land_type: UnitTypeId
            match flying_building.type_id:
                case UnitTypeId.BARRACKSFLYING:
                    land_type = UnitTypeId.BARRACKS
                case UnitTypeId.FACTORYFLYING:
                    land_type = UnitTypeId.FACTORY
                case UnitTypeId.STARPORTFLYING:
                    land_type = UnitTypeId.STARPORT
                case _:
                    continue

            land_position: Point2 = dfs_in_pathing(
                self.bot,
                flying_building.position,
                land_type,
                self.bot.game_info.map_center,
                1,
                True,
            )
            print(
                f"[reposition_buildings] Landing {flying_building.name} "
                f"(tag={flying_building.tag}) at {land_position}."
            )
            flying_building(AbilityId.LAND, land_position)

    async def salvage_bunkers(self) -> None:
        if (self.bot.scouting.situation != Situation.STABLE or self.bot.expansions.taken.amount < 3):
            return

        # Salvage main bunker once we're stable
        main_ramp_bunkers: Units = self.bot.structures(UnitTypeId.BUNKER).closer_than(8, self.bot.main_base_ramp.top_center)
        if (main_ramp_bunkers.amount >= 1):
            main_ramp_bunkers.first(AbilityId.SALVAGEEFFECT_SALVAGE)

        planetaries: Units = self.bot.structures(UnitTypeId.PLANETARYFORTRESS)
        if (planetaries.amount == 0):
            return
        
        BASE_SIZE: int = 12
        bunkers_to_salvage: Units = self.bot.structures(UnitTypeId.BUNKER).filter(
            lambda unit: (
                unit.cargo_used == 0
                and planetaries.closest_distance_to(unit) <= BASE_SIZE
            )
        )
        for bunker in bunkers_to_salvage:
            bunker(AbilityId.SALVAGEEFFECT_SALVAGE)
    
    def reserve_bunkers(self):
        buildings_layer: BuildingLayer = self.bot.map.influence_maps.buildings
        for expansion in self.bot.expansions:
            bunkers: Units = self.bot.structures(UnitTypeId.BUNKER)
            if (bunkers.closer_than(12, expansion.position).amount >= 1):
                continue
            bunker_position: Point2 = expansion.bunker_position
            if (bunker_position not in buildings_layer.reservations):
                buildings_layer.reserve_bunker(bunker_position)
    
    async def find_land_position(self, building: Unit):
        possible_land_positions_offset = sorted(
            (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
            key=lambda point: point.x**2 + point.y**2,
        )
        offset_point: Point2 = Point2((-0.5, -0.5))
        possible_land_positions = (building.position.rounded + offset_point + p for p in possible_land_positions_offset)
        for target_land_position in possible_land_positions:
            land_and_addon_points: List[Point2] = self.building_land_positions(target_land_position)
            if all(await self.bot.can_place(UnitTypeId.SUPPLYDEPOT, land_and_addon_points)):
                print(building.name, " found a position to land")
                building(AbilityId.LAND, target_land_position)
                break

    def building_land_positions(self, sp_position: Point2) -> List[Point2]:
        """ Return all points that need to be checked when trying to land at a location where there is enough space to build an addon. Returns 13 points. """
        land_positions = [(sp_position + Point2((x, y))).rounded for x in range(-1, 2) for y in range(-1, 2)]
        return land_positions + points_to_build_addon(sp_position)
 
    
    def scv_build_progress(self, scv: Unit) -> float:
        if (not scv.is_constructing_scv):
            return 1
        building: Unit = self.bot.structures.closest_to(scv)
        return 1 if building.is_ready else building.build_progress