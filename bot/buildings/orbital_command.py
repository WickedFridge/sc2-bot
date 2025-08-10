from typing import override
from bot.buildings.upgrade_building import UpgradeBuilding
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class OrbitalCommand(UpgradeBuilding):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.ORBITALCOMMAND
        self.abilityId = AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND
        self.name = "Orbital Command"
        self.base_building_id = UnitTypeId.COMMANDCENTER

    @override
    @property
    def conditions(self) -> bool:
        orbital_tech_available: bool = self.bot.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9
        ccs_amount: int = self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.idle.amount
        if (not orbital_tech_available or ccs_amount == 0):
            return False
        
        # we only build Orbital until we have 4 CCs
        if (self.bot.townhalls.ready.amount <= 3):
            return True

        # we always want a PF for the 4th CC
        if (self.bot.townhalls.ready.amount == 4):
            return False
        
        # if each expansion we have has less workers than the optimal amount, we can upgrade to Orbital Command
        # otherwise we float and build a PF
        optimal_worker_count: int = (
            sum(expansion.optimal_mineral_workers for expansion in self.bot.expansions.taken)
            + sum(expansion.optimal_vespene_workers for expansion in self.bot.expansions.taken)
        )
        is_mining_optimal: bool = self.bot.supply_workers < optimal_worker_count - 5
        return is_mining_optimal