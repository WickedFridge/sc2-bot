from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from sc2.game_data import Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

if TYPE_CHECKING:
    from .builder import Builder

class Building:
    bot: Superbot
    builder: Builder
    unitId: UnitTypeId
    unitIdFlying: Optional[UnitTypeId] = None
    abilityId: Optional[AbilityId] = None
    name: str
    radius: float = 1
    ignore_build_order: bool = False

    def __init__(self, build: Builder):
        self.bot = build.bot
        self.builder = build
    
    @property
    def force_position(self) -> bool:
        return False
    
    @property
    def override_conditions(self) -> bool:
        return False
    
    @property
    def custom_conditions(self) -> bool:
        return True
    
    @property
    def conditions(self) -> bool:
        return (
            self.bot.workers.amount >= 1
            and self.bot.tech_requirement_progress(self.unitId) == 1
            and (
                self.override_conditions
                or (
                    self.custom_conditions
                    and (
                        self.ignore_build_order
                        or self.unitId in self.bot.build_order.build.pending_ids
                        or self.bot.build_order.build.is_completed
                    )
                )
            )
        )

    @property
    def position(self) -> Point2 | None:
        pass

    @property
    def has_addon(self) -> bool:
        return self.unitId in [
            UnitTypeId.BARRACKS,
            UnitTypeId.FACTORY,
            UnitTypeId.STARPORT,
        ]

    @property
    def base_amount(self) -> int:
        return self.bot.townhalls.amount
        
    @property
    def pending_amount(self) -> int:
        return max(
            self.bot.structures(self.unitId).not_ready.amount,
            self.bot.already_pending(self.unitId)
        )

    @property
    def amount(self) -> int:
        amount: int = (
            self.bot.structures(self.unitId).ready.amount +
            self.pending_amount
        )
        if (self.unitIdFlying):
            amount += self.bot.structures(self.unitIdFlying).ready.amount

        return amount
    
    @property
    def precarious(self) -> int:
        return self.bot.scouting.situation.is_cheese
    
    def on_complete(self):
        print(f'Build {self.name}')

    async def build(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        building_cost: Cost = self.bot.calculate_cost(self.unitId)
        enough_resources: bool
        resources_updated: Resources
        enough_resources, resources_updated = resources.update(building_cost)
        if (enough_resources == False):
            return resources_updated
        
        pos: Point2 | None = self.position
        if (pos is None):
            print("Error, no valid position for {self.name}")
            return resources_updated
        
        position: Point2 = dfs_in_pathing(self.bot, pos, self.unitId, self.bot.game_info.map_center, self.radius, self.has_addon)
        if (position != pos):
            print(f"position changed for {self.name} from {pos} to {position}")
        await self.builder.build(self.unitId, position, self.radius, self.has_addon, self.force_position)
        self.on_complete()
        return resources_updated