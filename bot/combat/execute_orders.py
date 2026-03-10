from typing import List, Optional
from bot.combat.micro import Micro
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.point2_functions.utils import center
from bot.utils.unit_cargo import get_transport_cargo
from sc2.cache import CachedClass, custom_cache_once_per_frame
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import building_priorities, creep

PICKUP_RANGE: int = 3
WEAPON_READY_THRESHOLD: float = 6.0

class Execute(CachedClass):
    bot: Superbot
    micro: Micro
    _drop_target: Point2
    _last_calculated_drop_target_time: float = 0

    def __init__(self, bot: Superbot) -> None:
        super().__init__(bot)
        self.micro = Micro(bot)
        self._drop_target = Point2((5,5))

    @custom_cache_once_per_frame
    def default_drop_target(self) -> Point2:
        # switch default drop target every 60 seconds
        index_base_to_hit = round(self.bot.time / 60) % 2
        match (index_base_to_hit):
            case 0:
                # print("dropping main")
                return self.bot.expansions.enemy_main.mineral_line
            case 1:
                # print("dropping natural")
                return self.bot.expansions.enemy_b2.mineral_line

    @custom_cache_once_per_frame
    def drop_target(self) -> Point2:
        # if we don't know about enemy army or enemy bases, drop on the default target
        if (self.bot.expansions.potential_enemy_bases.amount == 0):
            return self.default_drop_target
        
        # otherwise drop on the furthest base from the enemy army if there's an army
        # otherwise drop on the furthest base from our last base
        furthest_point: Point2 = (
            self.bot.scouting.known_enemy_army.center
            if self.bot.scouting.known_enemy_army.units.amount >= 1
            else self.bot.expansions.taken.last.position
        )
        
        sorted_enemy_bases: Expansions = self.bot.expansions.potential_enemy_bases.sorted(
            lambda base: base.position._distance_squared(furthest_point),
            reverse=True,
        )
        return sorted_enemy_bases.first.mineral_line
    
    @custom_cache_once_per_frame
    def best_edge(self) -> Point2:
        if (self.bot.scouting.known_enemy_army.units.amount == 0):
            return self.bot.map.closest_center(self.drop_target)
        closest_two_centers: List[Point2] = self.bot.map.closest_centers(self.drop_target, 2)
        closest_two_centers.sort(key=lambda center: center._distance_squared(self.bot.scouting.known_enemy_army.center), reverse= True)
        return closest_two_centers[0]

    async def drop_load(self, army: Army):
        if (army.can_drop_medivacs.amount == 0):
            print("Error: no usable medivacs for drop")
            return
        
        # Step 1: Select the 2 fullest Medivacs among the healthy ones
        medivacs_to_use: Units = army.can_drop_medivacs.sorted(lambda unit: (unit.health_percentage >= 0.75, unit.cargo_used, unit.energy, unit.health), True).take(2)

        # Step 2: Split the medivacs
        medivacs_to_retreat = army.units(UnitTypeId.MEDIVAC).filter(lambda unit: unit.tag not in medivacs_to_use.tags)
        flyers_to_retreat = army.units.filter(lambda unit: unit.is_flying and unit.type_id != UnitTypeId.MEDIVAC)
        
        # Step 3: Unload and retreat extras
        for medivac in medivacs_to_retreat + flyers_to_retreat:
            if (medivac.passengers):
                await self.micro.medivac_unload(medivac)
            await self.micro.retreat(medivac)
        
        # Step 4: Check if the best two are full or need more units (don't drop ghosts)
        ground_units: Units = army.units.filter(lambda unit: unit.is_flying == False)
        maximum_cargo_left: int = max(medivac.cargo_left for medivac in medivacs_to_use)
        pickable_ground_units: Units = ground_units.filter(
            lambda unit: (
                unit.type_id != UnitTypeId.GHOST
                and get_transport_cargo(unit.type_id) <= maximum_cargo_left
            )
        )
        
        # Step 5: Select the ground units to pickup and retreat with the rest
        if (pickable_ground_units.amount >= 1 and maximum_cargo_left >= 1):
            await self.pickup(medivacs_to_use, pickable_ground_units)
            return

        for unit in ground_units:
            await self.micro.retreat(unit)
    
    async def drop_move(self, army: Army):
        # get the 2 closest edge of the map to the drop target
        # take the furthest one from the enemy army
        
        # -- Select the 2 fullest Medivacs among the healthy ones
        medivacs_to_use: Units = army.can_drop_medivacs.sorted(lambda unit: (unit.health_percentage >= 0.75, unit.cargo_used, unit.health, unit.tag), True).take(2)
        
        # -- Special case, if our army is only filled medivacs, select all of them and move along
        filled_medivacs: Units = army.can_drop_medivacs.filter(lambda unit: unit.cargo_used >= 1)
        if (army.units.amount == filled_medivacs.amount):
            medivacs_to_use = filled_medivacs
        
        
        # -- Drop with the medivacs
        for medivac in medivacs_to_use:
            distance_medivac_to_target = medivac.position.distance_to(self.drop_target)
            distance_edge_to_target = self.best_edge.distance_to(self.drop_target)
            
            # if the medivac are far appart, bring them closer
            if (medivac.distance_to(medivacs_to_use.center) > 4):
                medivac.move(medivacs_to_use.center)
                continue

            # If the edge is closer to the target than we are, take the detour
            if (distance_edge_to_target < distance_medivac_to_target):
                # Optional: Only go to edge if not already very close to it
                if medivac.position.distance_to(self.best_edge) > 5:
                    await self.micro.medivac_boost(medivac)
                    medivac.move(self.best_edge)
                else:
                    medivac.move(self.drop_target)
            else:
                # Direct path is better
                medivac.move(self.drop_target)
        
        ground_units: Units = army.units.filter(lambda unit: unit.is_flying == False)
        for unit in ground_units:
            await self.micro.retreat(unit)

    async def pickup(self, medivacs: Units, ground_units: Units):
        # units get closer to medivacs
        for unit in ground_units:
            if (medivacs.amount == 0):
                await self.micro.retreat(unit)
                break
            unit.move(medivacs.filter(lambda m: m.cargo_left >= 1).closest_to(unit))
        
        # medivacs boost and pickup
        for medivac in medivacs:
            await self.micro.medivac_pickup(medivac, ground_units)


    async def pickup_leave(self, army: Army):
        # If there's ground units, pick them up
        ground_units: Units = army.units.not_flying
        medivacs: Units = army.units(UnitTypeId.MEDIVAC)
        retreating_medivacs: Units = medivacs
        if (ground_units.amount >= 1):
            # pickup units
            minimum_cargo_slot: int = 1 if ground_units(UnitTypeId.MARINE).amount >= 1 else 2
            usable_medivacs: Units = medivacs.filter(lambda unit: unit.cargo_left >= 1 and unit.health_percentage >= 0.4)
            await self.pickup(usable_medivacs, ground_units)
            retreating_medivacs: Units = medivacs.filter(lambda unit: unit.cargo_left < minimum_cargo_slot or unit.health_percentage < 0.4)
        
        for medivac in retreating_medivacs:
            should_disengage: bool = await self.micro.medivac_safety_disengage(medivac)
            if (not should_disengage):
                await self.micro.retreat(medivac)

        for viking in army.units(UnitTypeId.VIKINGFIGHTER):
            await self.micro.viking_retreat(viking)
        
        other_flying_units: Units = army.units.flying.filter(lambda unit: unit.type_id not in [UnitTypeId.MEDIVAC, UnitTypeId.VIKINGFIGHTER])
        await self.retreat_army(Army(other_flying_units, self.bot))

    async def heal_up(self, army: Army):
        # drop units
        for unit in army.units:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_unload(unit)
                await self.micro.medivac_heal(unit, army.units)
            if (unit.type_id == UnitTypeId.REAPER):
                await self.micro.retreat(unit)
            # group units that aren't near the center
            else:
                if (unit.distance_to(army.center) > 5):
                    unit.move(army.center)
    
    async def retreat_army(self, army: Army):
        for unit in army.units:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_unload(unit)
                await self.micro.medivac_heal(unit, army.units)
            elif(unit.type_id == UnitTypeId.VIKINGFIGHTER):
                await self.micro.viking_retreat(unit)
            else:
                await self.micro.retreat(unit)

    async def fight(self, army: Army, chase: bool = False):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.REAPER:
                    await self.micro.reaper(unit)
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_fight(unit, army.units)
                case UnitTypeId.MARINE:
                    await self.micro.bio_fight(unit, army.units, chase)
                case UnitTypeId.MARAUDER:
                    await self.micro.bio_fight(unit, army.units, chase)
                case UnitTypeId.GHOST:
                    await self.micro.ghost(unit, army.units)
                case UnitTypeId.CYCLONE:
                    await self.micro.cyclone(unit, army.units)
                case UnitTypeId.VIKINGFIGHTER:
                    await self.micro.viking(unit, army.units)
                case UnitTypeId.RAVEN:
                    await self.micro.raven(unit, army.units)
                case _:
                    if (self.bot.enemy_units.amount >= 1):
                        closest_enemy_unit: Unit = self.bot.enemy_units.closest_to(unit)
                        unit.attack(closest_enemy_unit)
                    else:
                        unit.move(army.center)
    
    async def fight_defense(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_fight(unit, army.units)
                case UnitTypeId.REAPER:
                    await self.micro.reaper(unit)
                case UnitTypeId.MARINE:
                    await self.micro.bio_defense(unit, army.units)
                case UnitTypeId.MARAUDER:
                    await self.micro.bio_defense(unit, army.units)
                case UnitTypeId.GHOST:
                    await self.micro.ghost_defense(unit, army.units)
                case UnitTypeId.CYCLONE:
                    await self.micro.cyclone(unit, army.units)
                case UnitTypeId.VIKINGFIGHTER:
                    await self.micro.viking(unit, army.units)
                case UnitTypeId.RAVEN:
                    await self.micro.raven(unit, army.units)
                case _:
                    closest_enemy_unit: Unit = self.bot.enemy_units.closest_to(unit)
                    unit.attack(closest_enemy_unit)

    async def drop_unload(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_fight_unload(unit, self.drop_target)
                case UnitTypeId.MARINE:
                    await self.micro.bio_fight(unit, army.units)
                case UnitTypeId.MARAUDER:
                    await self.micro.bio_fight(unit, army.units)
                case UnitTypeId.GHOST:
                    await self.micro.ghost(unit, army.units)
                case UnitTypeId.CYCLONE:
                    await self.micro.cyclone(unit, army.units)
                case UnitTypeId.VIKINGFIGHTER:
                    await self.micro.viking(unit, army.units)
                case UnitTypeId.RAVEN:
                    await self.micro.raven(unit, army.units)
                case _:
                    if (self.bot.enemy_units.amount >= 1):
                        closest_enemy_unit: Unit = self.bot.enemy_units.closest_to(unit)
                        unit.attack(closest_enemy_unit)
                    else:
                        unit.move(army.center)
    
    async def disengage(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_disengage(unit, army.units)
                case UnitTypeId.MARINE:
                    await self.micro.bio_disengage(unit)
                case UnitTypeId.MARAUDER:
                    await self.micro.bio_disengage(unit)
                case UnitTypeId.GHOST:
                    await self.micro.bio_disengage(unit)
                case UnitTypeId.CYCLONE:
                    await self.micro.cyclone(unit, army.units)
                case _:
                    await self.micro.retreat(unit)

    
    async def defend(self, army: Army):
        expansions_under_attack: Expansions = self.bot.expansions.taken.under_attack
        if (expansions_under_attack.amount == 0):
            print("Error: no expansions under attack to defend")
            await self.retreat_army(army)
            return
        closest_expansion: Expansion = expansions_under_attack.closest_to(army.center)
        for unit in army.units:
            unit.attack(closest_expansion.position)
    
    def defend_bunker_rush(self, army: Army) -> None:
        main: Point2 = self.bot.expansions.main.position
        natural: Point2 = self.bot.expansions.b2.position
        BASE_SIZE: int = 20

        # -- Gather context -------------------------------------------------------
        enemy_bunkers: Units = self.bot.enemy_structures(UnitTypeId.BUNKER).filter(
            lambda bunker: min(bunker.distance_to(main), bunker.distance_to(natural)) <= BASE_SIZE
        )
        enemy_bunkers_in_progress: Units = enemy_bunkers.filter(lambda u: u.build_progress < 1)
        enemy_bunkers_completed: Units = enemy_bunkers.ready
        ally_bunkers: Units = self.bot.structures(UnitTypeId.BUNKER).ready

        scv_menacing: Units = self.bot.enemy_units(UnitTypeId.SCV).filter(
            lambda scv: enemy_bunkers.closest_distance_to(scv) <= 5
        )
        
        scvs_building: Units = scv_menacing.filter(
            lambda scv: enemy_bunkers_in_progress.closest_distance_to(scv) <= 5
        ) if enemy_bunkers_in_progress.amount >= 1 else Units([], self.bot)

        menacing_bunkers: Units = (enemy_bunkers_in_progress + enemy_bunkers_completed).filter(
            lambda b: min(b.distance_to(self.bot.expansions.main.position), b.distance_to(self.bot.expansions.b2.position)) <= BASE_SIZE
        )

        enemy_combat_units: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.type_id in [UnitTypeId.MARINE, UnitTypeId.MARAUDER, UnitTypeId.REAPER]
                and min(unit.distance_to(main), unit.distance_to(natural)) <= BASE_SIZE
            )
        )

        # -- Issue orders per unit ------------------------------------------------
        for unit in army.units:
            if (ally_bunkers.amount >= 1 and scvs_building.amount >= 1):
                closest_ally_bunker: Unit = ally_bunkers.closest_to(unit)
                if (closest_ally_bunker.distance_to(scvs_building.closest_to(unit)) < 20):
                    unit.move(closest_ally_bunker)
                    closest_ally_bunker(AbilityId.LOAD_BUNKER, unit)
                    continue

            # Highest priority target to move toward (SCV > bunker > combat)
            move_target: Optional[Unit] = self._bunker_rush_target(
                unit,
                [scvs_building, scv_menacing, menacing_bunkers, enemy_combat_units],
                in_range_only=False,
            )

            # Best target to actually shoot (in-range only, same priority)
            attack_target: Optional[Unit] = self._bunker_rush_target(
                unit,
                [scvs_building, scv_menacing, menacing_bunkers, enemy_combat_units],
                in_range_only=True,
            )

            if (move_target is None):
                unit.attack(self.bot.main_base_ramp.top_center)
                continue

            if (unit.weapon_cooldown <= WEAPON_READY_THRESHOLD and attack_target is not None):
                unit.attack(attack_target)
            else:
                attack_spot: Point2 = self.bot.map.influence_maps.best_attacking_spot(unit, move_target)
                unit.move(attack_spot)


    def _bunker_rush_target(
        self,
        unit: Unit,
        all_threats: List[Units],
        in_range_only: bool = False,
    ) -> Optional[Unit]:
        for threat_group in all_threats:
            in_range: Units = threat_group.filter(lambda t: unit.target_in_range(t))
            if (in_range.amount >= 1):
                return in_range.sorted(lambda t: t.health + t.shield).first
            if (not in_range_only and threat_group.amount >= 1):
                return threat_group.closest_to(unit)

        return None
            
    def handle_enemy_bunkers(self, unit: Unit, bunkers: Units, menacing_bunkers: Units) -> bool:
        if (menacing_bunkers.amount >= 1):
            if (bunkers.amount >= 1):
                closest_ally_bunker: Unit = bunkers.closest_to(menacing_bunkers)
                if (menacing_bunkers.closest_distance_to(closest_ally_bunker) <= 7):
                    unit.move(closest_ally_bunker)
                    closest_ally_bunker(AbilityId.LOAD_BUNKER, unit)
                    return True
            menacing_bunkers_in_range: Units = menacing_bunkers.in_attack_range_of(unit)
            if (menacing_bunkers_in_range.amount == 0):
                unit.attack(menacing_bunkers.closest_to(unit))
                return True
            unit.attack(menacing_bunkers_in_range.sorted(lambda bunker: bunker.health).first)
            return True
        return False

    def find_bunker_rush_target(self, unit: Unit, closest_scv_building: Unit, closest_enemy_bunker_in_progress: Unit, enemy_marines: Units, enemy_reapers: Units) -> Optional[Unit]:
        if (unit.target_in_range(closest_scv_building)):
            return closest_scv_building
        if (unit.target_in_range(closest_enemy_bunker_in_progress)):
            return closest_enemy_bunker_in_progress
        marines_in_range: Units = enemy_marines.filter(lambda enemy: unit.target_in_range(enemy))
        marines_in_range.sorted(lambda unit: unit.health)
        if (marines_in_range.amount):
            return marines_in_range.first
        reapers_in_range: Units = enemy_reapers.filter(lambda enemy: unit.target_in_range(enemy))
        reapers_in_range.sorted(lambda unit: unit.health)
        if (reapers_in_range.amount):
            return reapers_in_range.first
        return None

    def defend_canon_rush(self, army: Army):
        enemies: Units = self.bot.enemy_structures([UnitTypeId.PHOTONCANNON, UnitTypeId.PYLON]).sorted(
            lambda unit: (unit.health + unit.shield, unit.distance_to(self.bot.expansions.b2.position))
        )
        
        # if there are canons, destroy them
        for unit in army.units:
            if (enemies(UnitTypeId.PHOTONCANNON).amount >= 1):
                unit.attack(enemies(UnitTypeId.PHOTONCANNON).first)
            else:
                unit.attack(enemies.first)
            


    async def harass(self, army: Army, enemy_workers: Units):
        if (enemy_workers.amount == 0):
            print("Error: no worker close")
            return
        
        for unit in army.units:
            match(unit.type_id):
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_fight(unit, army.units)
                case UnitTypeId.RAVEN:
                    await self.micro.raven(unit, army.units)
                case UnitTypeId.VIKINGFIGHTER:
                    unit.move(army.center)
                case UnitTypeId.REAPER:
                    if (not await self.micro.reaper_grenade(unit)):
                        await self.micro.harass(unit, enemy_workers)
                case _:
                    await self.micro.harass(unit, enemy_workers)
    
    async def kill_buildings(self, army: Army):
        local_enemy_buildings: Units = self.bot.enemy_structures.filter(
            lambda unit: unit.distance_to(army.units.center) <= army.radius and unit.can_be_attacked
        ).sorted(
            lambda building: (building.type_id not in building_priorities, building.health + building.shield)
        )
        for unit in army.units:
            if (unit.type_id == UnitTypeId.RAVEN):
                await self.micro.raven(unit, army.units)
                continue
            if (unit.type_id == UnitTypeId.MEDIVAC):
                if (unit.cargo_used >= 4):
                    await self.micro.medivac_fight_unload(unit, local_enemy_buildings.first.position)
                else:
                    await self.micro.medivac_fight(unit, army.units)
                continue
            
            target: Unit = local_enemy_buildings.first
            if (
                unit.health_percentage >= 0.85 and (
                    target.health > 100
                    or local_enemy_buildings.amount >= 2
                )
            ):
                self.micro.stim_bio(unit, force=True)
            if (unit.weapon_cooldown <= WEAPON_READY_THRESHOLD):
                in_range_enemy_buildings: Units = local_enemy_buildings.filter(lambda building: unit.target_in_range(building))
                if (in_range_enemy_buildings.amount >= 1):
                    target = in_range_enemy_buildings.first
            unit.attack(target)

    async def attack_nearest_base(self, army: Army):
        # if army is purely air
        if (not army.leader):
            return
        nearest_base_target: Point2 = self.micro.get_nearest_base_target(army.leader)
        self.micro.attack_a_position(army.leader, nearest_base_target)
        for unit in army.followers:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_fight(unit, army.units)
                continue
            if (unit.position.distance_to(army.leader.position) >= 3):
                unit.move(army.leader.position)
            else:
                unit.move(center([unit.position, army.leader.position, nearest_base_target]))
        
    async def chase_buildings(self, army: Army):
        # if army is purely air
        if (not army.leader):
            return
        attack_position: Point2 = self.bot.enemy_structures.closest_to(army.leader).position
        self.micro.attack_a_position(army.leader, attack_position)
        for unit in army.followers:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_fight(unit, army.units)
                continue
            enemy_units_in_range = self.micro.get_enemy_units_in_range(unit)
            if (unit.weapon_cooldown == WEAPON_READY_THRESHOLD and enemy_units_in_range.amount >= 1):
                unit.attack(enemy_units_in_range.sorted(lambda unit: (unit.health + unit.shield)).first)
            elif (unit.distance_to(army.leader) >= 3):
                unit.move(army.leader.position)
            else:
                unit.move(center([unit.position, army.leader.position, attack_position]))

    def clean_creep(self, army: Army):
        target: Point2 | Unit = None
        creep_tumors: Units = self.bot.enemy_structures([UnitTypeId.CREEPTUMORBURROWED, UnitTypeId.CREEPTUMOR, UnitTypeId.CREEPTUMORQUEEN])
        TUMOR_DISTANCE_THRESHOLD: float = 10
        
        if (creep_tumors.closer_than(TUMOR_DISTANCE_THRESHOLD, army.center).amount >= 1):
            closest_tumor: Unit = creep_tumors.closest_to(army.center)
            target = closest_tumor
        else:
            CREEP_DENSITY_THRESHOLD: float = 0.4
            BASE_RADIUS: int = 6
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
                    target = position
        
        if (target is None):
            if (creep_tumors.amount >= 1):
                target = creep_tumors.closest_to(army.center)
            else:
                print("Error : no creep target")
        for unit in army.units:
            unit.attack(target)

    def chase_creep(self, army: Army):
        target: Point2 | Unit = None
        if (self.bot.map.influence_maps.creep.density[army.center] >= 0.5):
            pos = army.center.position
            target = army.center.position.towards(self.bot.map.influence_maps.creep.direction_to_tumor(pos), 2)
        else:
            closest_clamp: Point2 = self.bot.map.influence_maps.creep.closest_creep_clamp(army.center)
            target = closest_clamp
        
        for unit in army.units:
            unit.attack(target)
    
    def regroup(self, army: Army, armies: List[Army]):
        other_armies = list(filter(lambda other_army: other_army.center != army.center, armies))
        if (other_armies.__len__() == 0):
            return
        closest_army_position: Point2 = other_armies[0].center
        for other_army in other_armies:
            if (army.center.distance_to(other_army.center) < army.center.distance_to(closest_army_position)):
                closest_army_position = other_army.center
        for unit in army.units:
            unit.move(closest_army_position)

    def scout(self, army: Army):
        bases_to_scout: List[Expansion] = [
            self.bot.expansions.b2,
            self.bot.expansions.b3,
            self.bot.expansions.b4,
            self.bot.expansions.enemy_b2,
            self.bot.expansions.enemy_main,
            self.bot.expansions.enemy_b3,
            self.bot.expansions.enemy_b4,
        ]
        scout_target: Point2 = None
        for base in bases_to_scout:
            if (base.is_unknown):
                scout_target = base.mineral_line
                break
        
        if (scout_target is None):
            scout_target = self.bot.expansions.enemy_main.mineral_line
        
        for reaper in army.units:
            reaper.move(scout_target)