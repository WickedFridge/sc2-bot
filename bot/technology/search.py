from typing import List
from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.technology.tech import Tech
from sc2.game_data import Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit


class Search:
    bot: Superbot
    shield_researched: bool = False
    concussive_shells_researched: bool = False
    tech_tree_primary: List[Tech] = []

    def __init__(self, bot: Superbot) -> None:
        super().__init__()
        self.bot = bot
        self.tech_tree_secondary = [
            Tech(UnitTypeId.BARRACKSTECHLAB, UpgradeId.STIMPACK),
            Tech(UnitTypeId.BARRACKSTECHLAB, UpgradeId.SHIELDWALL, [UpgradeId.STIMPACK]),
            Tech(UnitTypeId.BARRACKSTECHLAB, UpgradeId.PUNISHERGRENADES, [UpgradeId.SHIELDWALL]),
            # Tech(UnitTypeId.ARMORY, AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1, is_ability = True),
        ]
        self.tech_tree_primary = [
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYWEAPONSLEVEL1),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYARMORSLEVEL1),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYWEAPONSLEVEL2, requirements_buildings = [UnitTypeId.ARMORY]),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYARMORSLEVEL2, requirements_buildings = [UnitTypeId.ARMORY]),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYWEAPONSLEVEL3, [UpgradeId.TERRANINFANTRYWEAPONSLEVEL2, UpgradeId.TERRANINFANTRYARMORSLEVEL2]),
            Tech(UnitTypeId.ENGINEERINGBAY, UpgradeId.TERRANINFANTRYARMORSLEVEL3, [UpgradeId.TERRANINFANTRYWEAPONSLEVEL2, UpgradeId.TERRANINFANTRYARMORSLEVEL2]),
        ]
    
    async def tech_primary(self, resources: Resources) -> Resources:
        technology_to_research: List[Tech] = filter(
            lambda tech: self.bot.already_pending(tech.upgrade) == 0,
            self.tech_tree_primary
        )
        return self.search(technology_to_research, resources)
    
    async def tech_secondary(self, resources: Resources) -> Resources:
        technology_to_research: List[Tech] = filter(
            lambda tech: self.bot.already_pending(tech.upgrade) == 0,
            self.tech_tree_secondary
        )
        return self.search(technology_to_research, resources)
    
    def search(self, tech_tree: List[Tech], resources: Resources) -> Resources:
        resources_updated: Resources = resources
        for technology in tech_tree:
            if (
                self.bot.structures(technology.building).ready.idle.amount >= 1
                and self.bot.tech_requirement_progress(technology.upgrade) == 1
                and all(self.bot.already_pending_upgrade(requirement) > 0 for requirement in technology.requirements_ups)
                and all(self.bot.structures(building).ready.amount >= 1 for building in technology.requirements_buildings)
            ):
                searching_cost: Cost = self.bot.calculate_cost(technology.upgrade)
                can_build: bool
                resources_updated: Resources
                can_build, resources_updated = resources.update(searching_cost)
                if (can_build == False):
                    return resources_updated
                print("Search", technology.upgrade)
                building: Unit = self.bot.structures(technology.building).ready.idle.random
                if (technology.is_ability):
                    building(technology.upgrade)
                else:
                    building.research(technology.upgrade)
        return resources_updated
