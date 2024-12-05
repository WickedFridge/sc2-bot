from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Train:
    bot: BotAI
    
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

    async def workers(self):
        if (
            self.bot.can_afford(UnitTypeId.SCV)
            and self.bot.workers.amount < self.bot.townhalls.amount * 22
            and self.bot.workers.amount <= 84
        ) :
            if (self.bot.orbitalTechAvailable()):
                townhalls = self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).ready.idle
            else :
                townhalls = self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.idle
            for th in townhalls:
                    print("Train SCV")
                    th.train(UnitTypeId.SCV)

    async def medivac(self):
        starports: Units = self.bot.structures(UnitTypeId.STARPORT).ready
        for starport in starports :
            if (
                self.bot.can_afford(UnitTypeId.MEDIVAC)
                and (starport.is_idle or (starport.has_reactor and starport.orders.__len__() < 2))
            ):
                print("Train Medivac")
                starport.train(UnitTypeId.MEDIVAC)

    async def infantry(self):
        barracks: Units = self.bot.structures(UnitTypeId.BARRACKS).ready
        for barrack in barracks :
            if (
                (barrack.is_idle or (barrack.has_reactor and barrack.orders.__len__() < 2))
                
            ):
                # train reaper if we don't have any
                # if (
                #     self.bot.can_afford(UnitTypeId.REAPER)
                #     and self.bot.units(UnitTypeId.REAPER).amount == 0
                # ):
                #     print("Train Reaper")
                #     barrack.train(UnitTypeId.REAPER)
                #     break
                
                # otherwise train marine
                if (self.bot.can_afford(UnitTypeId.MARINE)
                    and (not self.bot.waitingForOrbital() or self.bot.minerals >= 200)
                ):
                    print("Train Marine")
                    barrack.train(UnitTypeId.MARINE)
