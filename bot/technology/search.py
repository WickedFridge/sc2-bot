from typing import List
from bot.technology.tech import Tech
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit


class Search:
    bot: BotAI
    shield_researched: bool = False
    concussive_shells_researched: bool = False
    tech_tree: List[Tech] = []

    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot
        self.tech_tree = [
            Tech(UnitTypeId.BARRACKSTECHLAB, UpgradeId.STIMPACK),
            Tech(UnitTypeId.BARRACKSTECHLAB, UpgradeId.SHIELDWALL, [UpgradeId.STIMPACK]),
            Tech(UnitTypeId.BARRACKSTECHLAB, UpgradeId.PUNISHERGRENADES, [UpgradeId.SHIELDWALL]),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYWEAPONSLEVEL1),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYARMORSLEVEL1),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYWEAPONSLEVEL2),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYARMORSLEVEL2),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYWEAPONSLEVEL3),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYARMORSLEVEL3),
            # Tech(UnitTypeId.ARMORY, AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1, is_ability = True),
        ]
    
    async def tech(self):
        for technology in self.tech_tree:
            if (
                self.bot.structures(technology.building).ready.idle.amount >= 1
                and self.bot.tech_requirement_progress(technology.upgrade) == 1
                and all(self.bot.already_pending(requirement) == 1 for requirement in technology.requirements)
                and self.bot.can_afford(technology.upgrade)
                and not self.bot.already_pending(technology.upgrade)
            ):
                print("Search", technology.upgrade)
                building: Unit = self.bot.structures(technology.building).ready.idle.random
                if (technology.is_ability):
                    building(technology.upgrade)
                else:
                    building.research(technology.upgrade)

                # return to avoid double queuing upgrades
                return