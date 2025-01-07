from bot.utils.ability_tags import AbilityRepair
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit


class Macro:
    bot: BotAI

    def __init__(self, bot) -> None:
        self.bot = bot

    def repair_workers(self, scv: Unit):
        workers = self.bot.units(UnitTypeId.SCV) + self.bot.units(UnitTypeId.MULE)
        if (workers.amount == 0):
            return
        workers_repairing_scv = workers.filter(
            lambda unit: (
                unit.orders.__len__()
                and unit.orders[0].ability.id in AbilityRepair
                and unit.order_target == scv.tag
            )
        )
        if (workers_repairing_scv.amount >= 1):
            return
        
        close_workers = workers.filter(lambda unit: unit.distance_to(scv)).collecting
        if (close_workers.amount >= 1):
            print("Repairing SCV")
            workers.closest_to(scv).repair(scv)

    async def split_workers(self):
        for worker in self.bot.workers:
            closest_mineral: Unit = self.bot.mineral_field.closest_to(worker)
            worker.gather(closest_mineral)