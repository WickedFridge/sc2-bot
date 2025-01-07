from sc2.bot_ai import BotAI
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
            lambda unit: unit.is_repairing and unit.order_target == scv.tag
        )
        if (workers_repairing_scv.amount >= 1):
            return
        
        close_workers = workers.filter(lambda unit: unit.distance_to(scv)).collecting
        if (close_workers.amount >= 1):
            print("Repairing SCV")
            workers.closest_to(scv).repair(scv)