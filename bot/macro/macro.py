from typing import List
from bot.combat.threats import Threat
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.macro.speed_mining import SpeedMining
from bot.strategy.strategy_types import Situation
from bot.superbot import Superbot
from bot.utils.base import Base
from bot.utils.colors import BLUE, GREEN, ORANGE, PURPLE, RED, WHITE, YELLOW
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Point3
from sc2.unit import Unit, UnitOrder
from sc2.units import Units
from ..utils.unit_tags import worker_types, add_ons, tower_types

BASE_SIZE: int = 20
THREAT_DISTANCE: int = 8
REPAIR_THRESHOLD: float = 0.6
RALLY_LOCAL_SATURATION_THRESHOLD: float = 0.5
MAX_GAS_RATIO: float = 0.30
GAS_MINERAL_GATE_ENABLE: float = 0.50   # global mineral ratio above which gas workers are added
GAS_MINERAL_GATE_DISABLE: float = 0.40  # global mineral ratio below which gas workers are pulled

class Macro:
    bot: Superbot
    bases: List[Base]
    speed_mining: SpeedMining
    supply_block_time: int = 0
    structure_to_base: dict[int, Base] = {}

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.bases = []
        self.speed_mining = SpeedMining(bot)

    async def update_threat_level(self):
        self.bases = self.threat_detection()

    # due to speedmining, some workers sometimes bug
    async def unbug_workers(self):
        for worker in (self.bot.units(UnitTypeId.MULE) + self.bot.workers).filter(lambda worker: len(worker.orders) > 0):
            order: UnitOrder = worker.orders[0]
            townhall_ids: List[int] = [townhall.tag for townhall in self.bot.townhalls]
            positions = self.bot.expansions.taken.positions
            if (
                order.ability.id == AbilityId.MOVE and order.target in townhall_ids
                or (
                    (worker.is_repairing or worker.is_attacking)
                    and not self.bot.scouting.situation.is_cheese
                    and positions and min(worker.distance_to(p) for p in positions) >= 20
                )
            ):
                worker.stop()
    
    def threat_detection(self) -> List[Base]:
        expansions_taken: Expansions = self.bot.expansions.taken
        
        # If we don't have any base left we're pretty dead
        if (expansions_taken.amount == 0):
            return []
        
        bases: List[Base] = []
        # First create a Base object for each expansion we own
        for expansion in expansions_taken:
            base: Base = Base(self.bot, expansion, Threat.NO_THREAT)
            bases.append(base)
            self.structure_to_base[base.cc.tag] = base
        
        # Then distribute our other structures among these bases based on proximity
        other_structures: Units = self.bot.structures.filter(lambda structure: structure.tag not in expansions_taken.ccs.tags)
        for building in other_structures:
            bases_with_same_height: List[Base] = [base for base in bases if self.bot.get_terrain_height(base.position) == self.bot.get_terrain_height(building.position)]
            if (len(bases_with_same_height) == 0):
                continue
            closest_base: Base = min(bases_with_same_height, key=lambda base: (
                base.cc.distance_to(building)
            ))
            closest_base.buildings.append(building)
            self.structure_to_base[building.tag] = closest_base
        
        # Then distribute our units and workers among these bases based on proximity
        for unit in self.bot.units:
            closest_base: Base = min(bases, key=lambda base: base.cc.distance_to(unit))
            
            # workers are always assigned to the closest base, even if they're far, to ensure they can respond to threats and not get lost in the middle of the map
            if (unit.type_id in worker_types):
                closest_base.workers.append(unit)
                continue

            # skip units that are too far from the base
            if (closest_base.distance_to(unit) < THREAT_DISTANCE):
                closest_base.units.append(unit)

        # Then distribute enemy units and structures among these bases based on proximity
        for unit in self.bot.enemy_units + self.bot.enemy_structures:
            # find closest structure first
            # find the base the structure belongs to
            closest_base: Base = None
            
            if (other_structures.amount > 0):
                closest_structure: Unit = other_structures.closest_to(unit)

                if (closest_structure.distance_to(unit) < 8):
                    closest_base = self.structure_to_base.get(closest_structure.tag)
            
            if (closest_base is None):
                closest_base = min(bases, key=lambda b: b.cc.distance_to(unit))

            if (closest_base is None):
                continue

            # closest_base: Base = min(bases, key=lambda base: base.cc.distance_to(unit))
            
            # skip enemy units that are too far from the base
            if (
                closest_base.distance_to(unit) > THREAT_DISTANCE
                and unit.type_id not in tower_types
                and unit.type_id != UnitTypeId.PYLON
            ):
                continue

            if (unit.is_structure):
                closest_base.enemy_structures.append(unit)
            else:
                closest_base.enemy_units.append(unit)
        
        # Then, for each base, analyze nearby enemy units to determine the threat level
        for base in bases:
            base.threat = base.threat_detection()
        return bases

    
    async def workers_response_to_threat(self):
        # if every townhalls is dead, just attack the nearest unit with every worker
        if (self.bot.townhalls.amount == 0):
            print("no townhalls left, o7")
            attackable_enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.is_flying == False and unit.can_be_attacked)
            attackable_enemy_buildings: Units = self.bot.enemy_structures.filter(lambda unit: unit.is_flying == False and unit.can_be_attacked)
            for worker in self.bot.workers:
                if (attackable_enemy_units.amount >= 1):
                    worker.attack(attackable_enemy_units.closest_to(worker))
                elif(attackable_enemy_buildings.amount >= 1):
                    worker.attack(attackable_enemy_buildings.closest_to(worker))
            return
            
        for base in self.bases:
            base.workers_response_to_threat()

    async def split_workers(self):
        cc: Unit = self.bot.townhalls.first
        mineral_fields: Units = self.bot.mineral_field.filter(lambda unit: unit.distance_to(cc) <= 10)
        mined_fields_tags: List[int] = []
        for worker in self.bot.workers:
            closest_mineral: Unit = mineral_fields.closest_to(worker)
            worker.gather(closest_mineral)
            mined_fields_tags.append(closest_mineral.tag)
            # remove the mineral field from the list if it's already being mined by 2 workers
            if (mined_fields_tags.count(closest_mineral.tag) >= 2):
                mineral_fields = mineral_fields.filter(lambda unit: unit.tag != closest_mineral.tag)
        for mineral_field in mineral_fields.filter(lambda unit: unit.tag not in mined_fields_tags):
            closest_worker: Unit = self.bot.workers.closest_to(mineral_field)
            closest_worker.gather(mineral_field)

    async def mule_idle(self):
        if (self.bot.mineral_field.amount == 0):
            print("no mineral field left")
            return
        mules_idle = self.bot.units(UnitTypeId.MULE).idle
        for mule in mules_idle:
            closest_mineral_field: Unit = self.bot.mineral_field.closest_to(mule)
            mule.gather(closest_mineral_field)

    async def distribute_workers(self, iteration: int):
        if (not self.bot.mineral_field or not self.bot.workers):
            return

        ready_safe_expansions: Expansions = self.bot.expansions.ready.safe
        if (ready_safe_expansions.amount == 0):
            return

        worker_count: int = self.bot.supply_workers - self.bot.already_pending(UnitTypeId.SCV)
        has_idle_workers: bool = self.bot.workers.idle.amount > 0
        has_oversaturated_refinery: bool = self.bot.gas_buildings.filter(
            lambda refinery: refinery.assigned_harvesters >= 4
        ).amount > 0
        # frequency: int = min(20 + worker_count, 100)
        frequency: int = 4
        if (not has_idle_workers and not has_oversaturated_refinery and iteration % frequency != 0):
            return

        # Single pass over all expansions to collect global statistics
        expansions_list: List[Expansion] = ready_safe_expansions.expansions
        total_gas_workers: int = 0
        total_actual_mineral_workers: int = 0
        total_ideal_mineral_workers: float = 0.0

        least_saturated_mineral_expansion: Expansion = None
        least_saturated_mineral_deficit: float = float('inf')   # (current - optimal), most negative = most under-saturated
        most_saturated_mineral_expansion: Expansion = None
        most_saturated_mineral_surplus: float = float('-inf')

        expansion_by_position: dict[Point2, Expansion] = {}

        for expansion in expansions_list:
            expansion_by_position[expansion.position] = expansion
            workers_on_minerals: int = expansion.mineral_worker_count
            optimal_workers_on_minerals: float = expansion.optimal_mineral_workers
            total_gas_workers += expansion.vespene_worker_count

            if (optimal_workers_on_minerals > 0):
                total_actual_mineral_workers += workers_on_minerals
                total_ideal_mineral_workers += optimal_workers_on_minerals
                mineral_deficit: float = workers_on_minerals - optimal_workers_on_minerals
                if (mineral_deficit < least_saturated_mineral_deficit):
                    least_saturated_mineral_deficit = mineral_deficit
                    least_saturated_mineral_expansion = expansion
                if (mineral_deficit > most_saturated_mineral_surplus):
                    most_saturated_mineral_surplus = mineral_deficit
                    most_saturated_mineral_expansion = expansion

        if (least_saturated_mineral_expansion is None or least_saturated_mineral_expansion.mineral_fields.amount == 0):
            return

        # Count MULE equivalents: 1 Orbital Command = 1 active MULE = 4 SCV equivalent mining power.
        orbital_count: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount
        mule_equivalent_workers: int = orbital_count * 4
        effective_worker_count: int = worker_count + mule_equivalent_workers

        # Total harvesting capacity of all ready refineries across safe expansions.
        total_refinery_capacity: int = sum(
            refinery.ideal_harvesters
            for expansion in expansions_list
            for refinery in expansion.refineries
            if refinery.is_ready
        )

        # Three-zone gas gate to prevent oscillation when mineral count sits near the threshold:
        # - Below DISABLE: pull all gas workers back to minerals.
        # - Between DISABLE and ENABLE (gray zone): freeze current allocation — no add, no pull.
        # - Above ENABLE: fill gas normally.
        if (total_ideal_mineral_workers) == 0:
            target_gas_workers: int = 0
            gas_hysteresis: int = 0
        else:
            mineral_ratio: float = total_actual_mineral_workers / total_ideal_mineral_workers
            if (mineral_ratio < GAS_MINERAL_GATE_DISABLE):
                target_gas_workers: int = 0
                gas_hysteresis: int = 0
            elif (mineral_ratio < GAS_MINERAL_GATE_ENABLE):
                target_gas_workers: int = total_gas_workers  # freeze: neither add nor pull
                gas_hysteresis: int = 1
            else:
                target_gas_workers: int = min(total_refinery_capacity, round(effective_worker_count * MAX_GAS_RATIO))
                gas_hysteresis: int = 1

        # Rally each townhall to its own mineral line while locally under-saturated,
        # then redirect to the globally least saturated line once the local base is covered.
        for expansion in expansions_list:
            local_townhall: Unit = expansion.cc
            if (local_townhall is None):
                continue
            rally_target_expansion: Expansion = (
                expansion
                if expansion.mineral_saturation < RALLY_LOCAL_SATURATION_THRESHOLD
                else least_saturated_mineral_expansion
            )
            if (rally_target_expansion.mineral_fields.amount == 0):
                continue
            target_mineral_field: Unit = rally_target_expansion.mineral_fields.random
            if (
                len(local_townhall.rally_targets) == 0
                or local_townhall.rally_targets[0].tag not in rally_target_expansion.mineral_fields.tags
            ):
                local_townhall(AbilityId.RALLY_COMMANDCENTER, target_mineral_field)

        # Idle workers → most under-saturated expansion. Virtual capacity tracks how many more
        # workers each base can absorb in this call, preventing all idle SCVs from piling onto
        # one base. Negative values mean over-saturated; workers still go there rather than
        # stay idle (over-saturating minerals is better than idling or over-saturating gas).
        expansion_virtual_capacity: dict[Point2, int] = {
            expansion.position: round(expansion.optimal_mineral_workers) - expansion.mineral_worker_count
            for expansion in expansions_list
            if (expansion.optimal_mineral_workers > 0 and expansion.mineral_fields.amount > 0)
        }
        for idle_worker in self.bot.workers.idle:
            if (not expansion_virtual_capacity):
                break
            best_position: Point2 = max(
                expansion_virtual_capacity,
                key=lambda position: expansion_virtual_capacity[position]
            )
            target_expansion: Expansion = expansion_by_position[best_position]
            if (target_expansion.mineral_fields.amount == 0):
                del expansion_virtual_capacity[best_position]
                continue
            idle_worker.gather(target_expansion.mineral_fields.random)
            expansion_virtual_capacity[best_position] -= 1

        # Fix oversaturated refineries (≥4 workers) — redirect excess to the least saturated minerals
        for refinery in self.bot.gas_buildings.filter(lambda refinery: refinery.assigned_harvesters >= 4):
            excess_harvesters: Units = self.bot.workers.filter(
                lambda worker: worker.order_target == refinery.tag and not worker.is_carrying_vespene
            )
            if (excess_harvesters.amount >= 1 and least_saturated_mineral_expansion.mineral_fields.amount >= 1):
                excess_harvesters.random.gather(least_saturated_mineral_expansion.mineral_fields.random)

        # Gas adjustment — one move per call; hysteresis band prevents flickering.
        gas_bldg_tags: set[int] = {r.tag for r in self.bot.gas_buildings}
        workers_heading_to_gas: int = sum(
            1 for w in self.bot.workers
            if w.order_target in gas_bldg_tags and not w.is_carrying_vespene
        )

        if (total_gas_workers <= target_gas_workers - gas_hysteresis):
            # Find refineries below ideal saturation, grouped by priority tier.
            # 0–1 worker refineries are preferred over 2-worker ones (both are equally efficient
            # per worker, but lower counts indicate higher need). Within the chosen tier, pick the
            # refinery closest to any sufficiently saturated mineral line to minimize travel.
            print(f"[GAS] need more | assigned={total_gas_workers} heading={workers_heading_to_gas} target={target_gas_workers} cap={total_refinery_capacity}")
            for _exp in expansions_list:
                for _ref in _exp.refineries:
                    print(f"  ref {_ref.tag}: assigned={_ref.assigned_harvesters}/{_ref.ideal_harvesters}")
            needing_gas_fill: List[Unit] = [
                refinery
                for expansion in expansions_list
                for refinery in expansion.refineries
                if (refinery.assigned_harvesters < refinery.ideal_harvesters)
            ]
            if (needing_gas_fill):
                sufficiently_saturated_expansions: List[Expansion] = [
                    expansion for expansion in expansions_list
                    if (expansion.mineral_saturation >= RALLY_LOCAL_SATURATION_THRESHOLD)
                ]
                if (sufficiently_saturated_expansions):
                    priority_refineries: List[Unit] = [
                        refinery for refinery in needing_gas_fill if (refinery.assigned_harvesters <= 1)
                    ]
                    candidate_refineries: List[Unit] = (
                        priority_refineries if priority_refineries else needing_gas_fill
                    )
                    target_refinery: Unit = min(
                        candidate_refineries,
                        key=lambda refinery: min(
                            expansion.position.distance_to(refinery.position)
                            for expansion in sufficiently_saturated_expansions
                        )
                    )
                    nearest_saturated_expansion: Expansion = min(
                        sufficiently_saturated_expansions,
                        key=lambda expansion: expansion.position.distance_to(target_refinery.position)
                    )
                    free_mineral_workers: Units = nearest_saturated_expansion.mineral_workers.filter(
                        lambda worker: not worker.is_carrying_minerals
                    )
                    if (free_mineral_workers.amount >= 1):
                        worker_to_redirect: Unit = free_mineral_workers.closest_to(target_refinery)
                        print(f"  -> redirect #{worker_to_redirect.tag} (order_target={worker_to_redirect.order_target}, orders={len(worker_to_redirect.orders)}) -> ref {target_refinery.tag}")
                        worker_to_redirect.gather(target_refinery)
                    else:
                        print(f"  -> no free mineral workers (mineral_workers={nearest_saturated_expansion.mineral_workers.amount} non-carrying={nearest_saturated_expansion.mineral_workers.filter(lambda w: not w.is_carrying_minerals).amount})")
                else:
                    print(f"  -> no saturated expansions (threshold={RALLY_LOCAL_SATURATION_THRESHOLD})")
                    for _exp in expansions_list:
                        print(f"    {_exp.position}: sat={_exp.mineral_saturation:.2f}")

        elif (total_gas_workers > target_gas_workers + gas_hysteresis):
            # Pull a gas worker back to minerals. Return to the local base if it needs minerals
            # (avoids long travel); otherwise send to the globally least saturated line.
            print(f'pull worker out of gas [{total_gas_workers}/{target_gas_workers}] (+- {gas_hysteresis})')
            most_gas_saturated_expansion: Expansion = max(
                (expansion for expansion in expansions_list if expansion.vespene_worker_count > 0),
                key=lambda expansion: expansion.vespene_saturation,
                default=None,
            )
            if (most_gas_saturated_expansion is not None):
                mineral_destination: Expansion = (
                    most_gas_saturated_expansion
                    if most_gas_saturated_expansion.mineral_saturation < RALLY_LOCAL_SATURATION_THRESHOLD
                    else least_saturated_mineral_expansion
                )
                if (mineral_destination.mineral_fields.amount >= 1):
                    all_gas_workers: Units = most_gas_saturated_expansion.vespene_workers
                    non_carrying_gas_workers: Units = all_gas_workers.filter(
                        lambda worker: not worker.is_carrying_vespene
                    )
                    worker_to_redirect: Unit = (
                        non_carrying_gas_workers.random
                        if non_carrying_gas_workers.amount > 0
                        else (all_gas_workers.random if all_gas_workers.amount > 0 else None)
                    )
                    if (worker_to_redirect is not None):
                        worker_to_redirect.gather(mineral_destination.mineral_fields.random)

        # Mineral rebalancing between bases — one move per call, only when imbalance exceeds ±2
        if (
            most_saturated_mineral_surplus > 2
            and least_saturated_mineral_deficit < -2
            and most_saturated_mineral_expansion is not least_saturated_mineral_expansion
            and least_saturated_mineral_expansion.mineral_fields.amount >= 1
        ):
            free_workers_for_rebalance: Units = most_saturated_mineral_expansion.mineral_workers.filter(
                lambda worker: not worker.is_carrying_minerals
            )
            if (free_workers_for_rebalance.amount >= 1):
                free_workers_for_rebalance.random.gather(least_saturated_mineral_expansion.mineral_fields.random)

    def supply_block_update(self):
        if (self.bot.supply_left <= 1 and self.bot.supply_cap < 200):
            production_buildings_idle: Units = self.bot.structures(
                [UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND, UnitTypeId.BARRACKS, UnitTypeId.STARPORT]
            ).ready.filter(
                lambda building: (
                    building.is_idle
                    or (building.has_reactor and len(building.orders) < 2)
                )
            )
            if (production_buildings_idle.amount >= 1):
                self.supply_block_time += 1

        self.bot.client.debug_text_screen(
            f"Supply Block Time: {self.supply_block_time}",
            (0.5, 0.01),
            GREEN,
            12,
        )

    async def debug_bases_threat(self):
        color: tuple
        for i, base in enumerate(self.bases):
            match base.threat:
                case Threat.NO_THREAT:
                    color = GREEN
                case Threat.ATTACK:
                    color = ORANGE
                case Threat.OVERWHELMED:
                    color = RED
                case Threat.WORKER_SCOUT:
                    color = YELLOW
                case Threat.HARASS:
                    color = BLUE
                case Threat.CANON_RUSH:
                    color = PURPLE
                case _:
                    color = WHITE
            base_descriptor: str = f'[{i + 1}][{base.threat.__repr__()}]'
            unit_descriptor: str = f'[{i + 1}]'
            for enemy_unit in base.enemy_units:
                self.draw_box_on_world(enemy_unit.position, enemy_unit.radius, RED)
                self.draw_text_on_world(enemy_unit.position, unit_descriptor, RED)
            for building in base.buildings:
                radius: float = building.footprint_radius if building.footprint_radius else 0.5
                self.draw_box_on_world(building.position, radius, color)
                self.draw_text_on_world(building.position, base_descriptor, color)
            for unit in base.units:
                self.draw_box_on_world(unit.position, 0.5, color)
                self.draw_text_on_world(unit.position, unit_descriptor, color)
            # for worker in base.workers:
            #     self.draw_box_on_world(worker.position, 0.3, color)
            #     self.draw_text_on_world(worker.position, unit_descriptor, color)

    def draw_sphere_on_world(self, pos: Point2, radius: float = 2, draw_color: tuple = (255, 0, 0)):
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_sphere_out(
            Point3((pos.x, pos.y, z_height)), 
            radius, color=draw_color
        )

    def draw_text_on_world(self, pos: Point2, text: str, draw_color: tuple = (255, 102, 255), font_size: int = 14) -> None:
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_text_world(
            text,
            Point3((pos.x, pos.y, z_height)),
            color=draw_color,
            size=font_size,
        )

    def draw_box_on_world(self, pos: Point2, size: float = 0.25, draw_color: tuple = (255, 0, 0)):
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_box2_out(
            Point3((pos.x, pos.y, z_height-0.45)),
            size,
            draw_color,
        )