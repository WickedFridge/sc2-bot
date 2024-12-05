from typing import List
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit
from sc2.units import Units


class Search:
    bot: BotAI
    
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

    
    async def stim(self):
        if (
            self.bot.tech_requirement_progress(UpgradeId.STIMPACK) == 1
            and self.bot.structures(UnitTypeId.BARRACKSTECHLAB).ready.idle.amount >= 1
            and self.bot.can_afford(UpgradeId.STIMPACK)
            and not self.bot.already_pending_upgrade(UpgradeId.STIMPACK)
        ):
            print("Search Stim")
            techlab: Unit = self.bot.structures(UnitTypeId.BARRACKSTECHLAB).ready.idle.random
            techlab.research(UpgradeId.STIMPACK)

    
    async def shield(self):
        if (
            self.bot.tech_requirement_progress(UpgradeId.STIMPACK) == 1
            and self.bot.structures(UnitTypeId.BARRACKSTECHLAB).ready.idle.amount >= 1
            and self.bot.can_afford(UpgradeId.STIMPACK)
            and self.bot.shield_researched == False
            # and not self.bot.already_pending_upgrade(AbilityId.RESEARCH_COMBATSHIELD)
        ):
            print("Search Shield")
            self.bot.shield_researched = True
            techlab: Unit = self.bot.structures(UnitTypeId.BARRACKSTECHLAB).ready.idle.random
            techlab(AbilityId.RESEARCH_COMBATSHIELD)


    async def upgrades(self):
        ebays: Units = self.bot.structures(UnitTypeId.ENGINEERINGBAY).ready
        if (ebays.ready.idle.amount < 1):
            return
        
        # determine which upgrade to search
        upgrade_list: List[UpgradeId] = [
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
            UpgradeId.TERRANINFANTRYARMORSLEVEL1,
        ]
        advanced_upgrades_list: List[UpgradeId] = [
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
            UpgradeId.TERRANINFANTRYARMORSLEVEL2,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL3,
            UpgradeId.TERRANINFANTRYARMORSLEVEL3,
        ]

        # if armory is unlocked, add level 2 upgrades to the pool
        if (self.bot.structures(UnitTypeId.ARMORY).ready.amount >= 1):
            upgrade_list = upgrade_list + advanced_upgrades_list

        for ebay in ebays.ready.idle:
            for upgrade in upgrade_list:
                if (self.bot.can_afford(upgrade) and self.bot.already_pending_upgrade(upgrade) == 0):
                    print("Start Upgrade : ", upgrade.name)
                    ebay.research(upgrade)
                    break