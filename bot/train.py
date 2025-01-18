from bot.combat.combat import Combat
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Train:
    bot: BotAI
    combat: Combat
    
    def __init__(self, bot: BotAI, combat: Combat) -> None:
        super().__init__()
        self.bot = bot
        self.combat = combat

    async def workers(self):
        workers_pending: float = self.bot.already_pending(UnitTypeId.SCV)
        worker_count: float = self.bot.supply_workers + workers_pending
        worker_max: int = min(84, self.bot.townhalls.amount * 22)
        townhalls_type: UnitTypeId = UnitTypeId.ORBITALCOMMAND if self.bot.orbitalTechAvailable() else UnitTypeId.COMMANDCENTER
        townhalls: Units = self.bot.townhalls(townhalls_type).ready.filter(
            lambda unit: (
                unit.is_idle
                or (
                    unit.orders.__len__() == 1
                    and unit.orders[0].ability.id == AbilityId.COMMANDCENTERTRAIN_SCV
                    and unit.orders[0].progress >= 0.95
                )
            )
        )
        for th in townhalls:
            if (
                self.bot.can_afford(UnitTypeId.SCV)
                and worker_count < worker_max
            ) :
                print(f'Train SCV [{worker_count + 1}/{worker_max}]')
                th.train(UnitTypeId.SCV)

    async def medivac(self):
        starports: Units = self.bot.structures(UnitTypeId.STARPORT).ready
        max_medivac_amount: int = 12
        for starport in starports :
            if (
                self.bot.can_afford(UnitTypeId.MEDIVAC)
                and (starport.is_idle or (starport.has_reactor and starport.orders.__len__() < 2))
            ):
                medivac_amount: int = self.bot.units(UnitTypeId.MEDIVAC).amount
                if (medivac_amount < max_medivac_amount):
                    print("Train Medivac")
                    starport.train(UnitTypeId.MEDIVAC)

    @property
    def should_train_marauders(self):
        enemy_armored_ratio: float = (
            0 if self.combat.known_enemy_army.supply == 0
            else self.combat.known_enemy_army.armored_supply / self.combat.known_enemy_army.supply
        )
        armored_ratio: float = (
            0 if self.combat.army_supply == 0
            else self.combat.armored_supply / self.combat.army_supply
        )
        if (enemy_armored_ratio > armored_ratio):
            return True
        return False
    
    async def infantry(self):
        barracks: Units = self.bot.structures(UnitTypeId.BARRACKS).ready
        for barrack in barracks :
            if (barrack.is_idle or (barrack.has_reactor and barrack.orders.__len__() < 2)):
                # train reaper if we don't have any
                # if (
                #     self.bot.can_afford(UnitTypeId.REAPER)
                #     and self.bot.units(UnitTypeId.REAPER).amount == 0
                # ):
                #     print("Train Reaper")
                #     barrack.train(UnitTypeId.REAPER)
                #     break

                # if we have a techlab
                if (barrack.has_techlab and self.should_train_marauders):
                    if(
                        self.bot.can_afford(UnitTypeId.MARAUDER)
                        and (not self.bot.waitingForOrbital() or self.bot.minerals >= 250)
                    ):
                        print("Train Marauder")
                        barrack.train(UnitTypeId.MARAUDER)
                    break

                # otherwise train marine
                if (self.bot.can_afford(UnitTypeId.MARINE)
                    and (not self.bot.waitingForOrbital() or self.bot.minerals >= 200)
                ):
                    print("Train Marine")
                    barrack.train(UnitTypeId.MARINE)
