from bot.utils.ability_tags import AbilityRepair
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import worker_types


class Macro:
    bot: BotAI

    def __init__(self, bot) -> None:
        self.bot = bot

    def repair_workers(self, scv: Unit, amount_damage_taken: float):
        workers = self.bot.units(UnitTypeId.SCV) + self.bot.units(UnitTypeId.MULE)
        if (workers.amount == 0):
            print("no workers available to repair o7")
            return
        workers_repairing_scv: Units = workers.filter(
            lambda unit: (
                unit.orders.__len__() >= 1
                and unit.orders[0].ability.id in AbilityRepair
                and unit.order_target == scv.tag
            )
        )
        max_workers_repairing: int = 1 if amount_damage_taken < 6 else 2
        if (workers_repairing_scv.amount >= max_workers_repairing):
            print("max worker repairing already")
            return
        
        close_workers = workers.filter(lambda unit: unit.distance_to(scv) < 30).collecting
        if (close_workers.amount >= 1):
            print("Repairing SCV")
            workers.closest_to(scv).repair(scv)

    async def split_workers(self):
        cc: Unit = self.bot.townhalls.first
        mineral_fields: Units = self.bot.mineral_field.filter(lambda unit: unit.distance_to(cc) <= 10)
        for worker in self.bot.workers:
            closest_mineral: Unit = mineral_fields.closest_to(worker)
            worker.gather(closest_mineral)
        for mineral_field in mineral_fields:
            closest_worker: Unit = self.bot.workers.closest_to(mineral_field)
            closest_worker.gather(mineral_field)