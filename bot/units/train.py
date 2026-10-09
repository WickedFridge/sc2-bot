from __future__ import annotations
from typing import TYPE_CHECKING, List, Set

from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.utils.fake_order import FakeOrder
from sc2.game_data import Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units
from bot.utils.unit_supply import get_unit_supply
from bot.utils.unit_tags import worker_types

if TYPE_CHECKING:
    from .trainer import Trainer

class Train:
    bot: Superbot
    trainer: Trainer
    unitId: UnitTypeId
    buildingIds: List[UnitTypeId]
    order_id: AbilityId
    name: str
    i: int = 0
    check_build_order: bool = False
    requires_techlab: bool = False
    # don't use a techlab building for this unit while one of these should be trained
    techlab_reserved_for: List[UnitTypeId] = []
    # progress from which a new order can be queued behind the current one
    requeue_progress: float = 0.95
    # queue behind the current order even without addon (prevents the addon from being built)
    requeue_without_addon: bool = False
        
    def __init__(self, trainer: Trainer) -> None:
        self.bot = trainer.bot
        self.trainer = trainer
    
    @property
    def default_conditions(self) -> bool:
        return (
            self.bot.supply_used + get_unit_supply(self.unitId) <= self.bot.supply_cap
            and self.building_group.amount >= 1
            and (
                self.unitId in worker_types
                or self.bot.composition_manager.should_train(self.unitId)
                or self.force_conditions
            )
        )
    
    @property
    def custom_conditions(self) -> bool:
        return True
    
    @property
    def force_conditions(self) -> bool:
        return False

    @property
    def conditions(self) -> bool:
        return self.default_conditions and self.custom_conditions

    @property
    def building_group(self) -> Units:
        lifting_tags: Set[int] = self.bot.addon_swap.lifting_tags
        return self.bot.structures(self.buildingIds).ready.filter(
            lambda building: (
                building.tag not in lifting_tags
                and self.addon_allows(building)
                and self.has_free_slot(building)
            )
        ).sorted(lambda building: building.has_reactor, reverse=True)

    def addon_allows(self, building: Unit) -> bool:
        if (not building.has_add_on):
            return not self.requires_techlab
        addon: Unit = self.bot.structures.by_tag(building.add_on_tag)
        if (addon.build_progress < 0.95):
            return False
        if (building.has_techlab):
            return not any(
                self.bot.composition_manager.should_train(unit_id)
                for unit_id in self.techlab_reserved_for
            )
        return not self.requires_techlab

    def has_free_slot(self, building: Unit) -> bool:
        """
        A reactor gives 2 slots. A new order may also be queued when a slot
        is about to free up, so that production never stops.
        Without addon, only train when idle: an idle building first gets the
        chance to build its addon, and only trains if none is planned.
        """
        if (not building.has_add_on and not self.requeue_without_addon):
            return building.is_idle
        slots: int = 2 if building.has_reactor else 1
        return (
            len(building.orders) < slots
            or (
                len(building.orders) == slots
                and any(order.progress >= self.requeue_progress for order in building.orders)
            )
        )

    @property
    def training_cost(self) -> Cost:
        return self.bot.calculate_cost(self.unitId)

    def log(self, i: int) -> None:
        print(f'Train {self.name}')

    def on_complete(self):
        pass

    async def train(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        self.i = 0
        resources_updated: Resources = resources
        for building in self.building_group:
            if (not self.conditions):
                return resources_updated
            enough_resources: bool
            resources_updated: Resources
            enough_resources, resources_updated = resources_updated.update(self.training_cost)
            if (enough_resources == False):
                return resources_updated            
            self.log(self.i)
            building.train(self.unitId)
            # add a fake order so that other function know that we are not idle anymore
            building.orders.append(FakeOrder(self.order_id))
            self.i += 1
            self.on_complete()
        return resources_updated