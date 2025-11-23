import math
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

class Macro:
    bot: Superbot
    bases: List[Base]
    speed_mining: SpeedMining
    supply_block_time: int = 0

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.bases = []
        self.speed_mining = SpeedMining(bot)

    async def update_threat_level(self):
        self.bases = self.threat_detection()

    # due to speedmining, some workers sometimes bug
    async def unbug_workers(self):
        for worker in (self.bot.units(UnitTypeId.MULE) + self.bot.workers).filter(lambda worker: worker.is_idle == False):
            order: UnitOrder = worker.orders[0]
            townhall_ids: List[int] = [townhall.tag for townhall in self.bot.townhalls]
            positions = self.bot.expansions.taken.positions
            if (
                order.ability.id == AbilityId.MOVE and order.target in townhall_ids
                or (
                    (worker.is_repairing or worker.is_attacking)
                    and self.bot.scouting.situation not in [Situation.CANON_RUSH, Situation.BUNKER_RUSH]
                    and positions and min(worker.distance_to(p) for p in positions) >= 20
                )
            ):
                worker.stop()
    
    def threat_detection(self) -> List[Base]:
        # If we don't have any base left we're pretty dead
        if (self.bot.expansions.taken.amount == 0):
            return []
        
        bases: List[Base] = []
        ccs: List[int] = []
        # First create a Base object for each expansion we own
        for expansion in self.bot.expansions.taken:
            bases.append(Base(self.bot, expansion.cc, Threat.NO_THREAT))
            ccs.append(expansion.cc.tag)
        
        # Then distribute our other structures among these bases based on proximity
        other_structures: Units = self.bot.structures.filter(lambda structure: structure.tag not in ccs)
        for building in other_structures:
            bases_with_same_height: List[Base] = [base for base in bases if self.bot.get_terrain_height(base.position) == self.bot.get_terrain_height(building.position)]
            if (len(bases_with_same_height) == 0):
                continue
            closest_base: Base = min(bases_with_same_height, key=lambda base: (
                base.cc.distance_to(building)
                # and self.bot.get_terrain_height(base.position) == self.bot.get_terrain_height(building.position)
            ))
            closest_base.buildings.append(building)
        
        # Then distribute our units and workers among these bases based on proximity
        for unit in self.bot.units:
            closest_base: Base = min(bases, key=lambda base: base.cc.distance_to(unit))
            
            # skip enemy units that are too far from the base
            if (closest_base.distance_to(unit) > THREAT_DISTANCE):
                continue
            
            if (unit.type_id in worker_types):
                closest_base.workers.append(unit)
            closest_base.units.append(unit)

        # Then distribute enemy units and structures among these bases based on proximity
        for unit in self.bot.enemy_units + self.bot.enemy_structures:
            closest_base: Base = min(bases, key=lambda base: base.cc.distance_to(unit))
            
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

    async def saturate_gas(self):
        # Saturate refineries
        for refinery in self.bot.gas_buildings:
            if (
                refinery.assigned_harvesters < refinery.ideal_harvesters
                and self.bot.vespene <= self.bot.minerals + 300
                and self.bot.workers.amount >= 5 * self.bot.townhalls.amount
            ):
                workers: Units = self.bot.workers.gathering.closer_than(10, refinery).filter(
                    lambda unit: self.bot.gas_buildings.find_by_tag(unit.orders[0].target) is None
                )
                if workers:
                    closest_worker = workers.closest_to(refinery)
                    closest_worker.gather(refinery)

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
        worker_count = self.bot.workers.amount
        frequency = min(40 + worker_count * 2, 200)  # Scale up to a max of 200 iterations

        # Check if one gas is oversaturated
        oversaturated_ref: Units = self.bot.gas_buildings.filter(lambda unit: unit.assigned_harvesters >= 4)

        if (iteration % frequency != 0 and self.bot.workers.idle.amount == 0 and oversaturated_ref.amount == 0):
            return
        if (not self.bot.mineral_field or not self.bot.workers or self.bot.expansions.ready.amount == 0):
            return
        if (self.bot.expansions.ready.safe.amount == 0):
            return

        expansions_sorted_by_deficit_in_mining: Expansions = self.bot.expansions.ready.safe.sorted(
            key = lambda expansion: expansion.mineral_worker_count - expansion.optimal_mineral_workers,
        )


        most_saturated_expansion: Expansion = expansions_sorted_by_deficit_in_mining.last
        least_saturated_expansion: Expansion = expansions_sorted_by_deficit_in_mining.first
        for th in self.bot.townhalls.ready:
            if (
                len(th.rally_targets) >= 1
                and th.rally_targets[0].tag not in least_saturated_expansion.mineral_fields.tags
                and least_saturated_expansion.mineral_fields.amount >= 1
            ):
                th(AbilityId.RALLY_COMMANDCENTER, least_saturated_expansion.mineral_fields.random)
        
        for worker in self.bot.workers.idle:
            if (least_saturated_expansion.mineral_fields.amount == 0):
                break
            mineral_field_target: Unit = least_saturated_expansion.mineral_fields.random
            worker.gather(mineral_field_target)

        # make some movements with SCVs on oversaturated lines
        if (
            most_saturated_expansion.mineral_worker_count > most_saturated_expansion.optimal_mineral_workers + 2
            and least_saturated_expansion.mineral_worker_count < least_saturated_expansion.optimal_mineral_workers - 2
        ):
            most_saturated_expansion.mineral_workers.random.stop()

        # saturate gas
        # v2
        # for expansion in self.bot.expansions.filter(lambda expansion: expansion.refineries.amount >= 1):
        #     # Calculate the ideal number of gas workers per refinery
        #     total_vespene_workers_needed: int = expansion.desired_vespene_saturation * 3
        #     actual_vespene_workers: int = expansion.vespene_worker_count
        #     vespene_worker_difference: float = total_vespene_workers_needed - actual_vespene_workers

        #     # we don't change until we have a 0.75 difference
        #     if (abs(vespene_worker_difference) <= 0.5):
        #         break

        #     # Loop through refineries and check if they need workers
        #     for refinery in expansion.refineries:
        #         # Current assigned workers for the refinery
        #         current_workers = refinery.assigned_harvesters
                                
        #         # If the difference is above a threshold, we need to take action
        #         if (vespene_worker_difference > 0):  # If we need more workers (threshold of 0.5)
        #             # Find idle mineral workers
        #             mineral_workers: Units = expansion.mineral_workers.filter(
        #                 lambda unit: unit.is_carrying_minerals == False
        #             )
                    
        #             # If there are mineral workers, assign the closest to the refinery
        #             if mineral_workers.amount > 0:
        #                 mineral_workers.closest_to(refinery).gather(refinery)
        #                 break
                        
        #         elif (vespene_worker_difference < 0):  # If we have too many workers (threshold of -0.5)
        #             # Find vespene workers that are not carrying vespene and stop them
        #             vespene_workers: Units = expansion.vespene_workers.filter(
        #                 lambda unit: unit.is_carrying_vespene == False
        #             )
                    
        #             # Stop a worker if there's an excess
        #             if vespene_workers.amount >= 1:
        #                 vespene_workers.random.stop()
        #                 break

        # v1
        # for expansion in self.bot.expansions.filter(lambda expansion: expansion.refineries.amount >= 1):
        #     # if we're oversaturated
        #     if (expansion.vespene_worker_count > expansion.desired_vespene_workers):
        #         vespene_workers: Units = expansion.vespene_workers.filter(lambda unit: unit.is_carrying_vespene == False)
        #         if (vespene_workers.amount >= 1):
        #             vespene_workers.random.stop()
        #     # if we're undersaturated
        #     if (expansion.vespene_worker_count < expansion.desired_vespene_workers):
        #         least_saturated_refinery: Unit = expansion.refineries.sorted(lambda unit: unit.assigned_harvesters).first
        #         mineral_workers: Units = expansion.mineral_workers.filter(
        #             lambda unit: unit.is_carrying_minerals == False
        #         )
        #         mineral_workers.closest_to(least_saturated_refinery).gather(least_saturated_refinery)
        #         break
        
        #v0
        expansion_sorted_by_vespene_mining: Expansions = self.bot.expansions.ready.filter(
            lambda expansion: expansion.refineries.amount >= 1
        ).sorted(
            key = lambda expansion: expansion.vespene_saturation,
            reverse = True
        )
        
        # we want 0 gas if saturation of any base is under 2/3 and we have 200 or more gas in bank while we have under 44 scvs
        if (
            expansion_sorted_by_vespene_mining.amount >= 1 and 
            least_saturated_expansion.mineral_saturation <= 2/3 and
            worker_count <= 44 and
            self.bot.vespene >= 200
        ):
            # find a vespene worker and ask it to stop
            vespene_workers: Units = expansion_sorted_by_vespene_mining.first.vespene_workers
            if (vespene_workers.amount >= 1):
                vespene_workers.random.stop()
                return
        
        # we want to avoid oversaturation
        oversaturated_refineries: Units = self.bot.structures(UnitTypeId.REFINERY).filter(lambda unit: unit.assigned_harvesters >= 4)
        for oversaturated_ref in oversaturated_refineries:
            harvesters: Units = self.bot.workers.filter(
                lambda worker: worker.order_target == oversaturated_ref.tag and not worker.is_carrying_vespene
            )
            if (harvesters.amount >= 1):
                harvesters.random.stop()

        # we want saturation in gas if every mineral line is over 2/3rd saturation
        if (least_saturated_expansion.mineral_saturation <= 0.6):
            return
        
        # expansions_not_saturated_in_vespene: Expansions = self.bot.expansions.filter(
        #     lambda expansion: expansion.refineries.amount >= 1 and math.floor(expansion.vespene_saturation * 3) < expansion.desired_vespene_saturation * 3
        # ).sorted(lambda expansion: expansion.vespene_saturation)
        
        for expansion in expansion_sorted_by_vespene_mining:
            if (expansion.refineries.amount == 0 or math.floor(expansion.vespene_saturation * 3) >= expansion.desired_vespene_saturation * 3):
                continue
            least_saturated_refinery: Unit = expansion.refineries.sorted(lambda unit: unit.assigned_harvesters).first
            mineral_workers: Units = expansion.mineral_workers.filter(
                lambda unit: unit.is_carrying_minerals == False
            )
            if (mineral_workers.amount == 0):
                continue
            mineral_workers.closest_to(least_saturated_refinery).gather(least_saturated_refinery)
            break

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
                radius: float = building.footprint_radius if building.type_id not in add_ons else 0.5
                self.draw_box_on_world(building.position, radius, color)
                self.draw_text_on_world(building.position, base_descriptor, color)
            for unit in base.units:
                self.draw_box_on_world(unit.position, 0.5, color)
                self.draw_text_on_world(unit.position, unit_descriptor, color)
            for worker in base.workers:
                self.draw_box_on_world(worker.position, 0.3, color)
                self.draw_text_on_world(worker.position, unit_descriptor, color)

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