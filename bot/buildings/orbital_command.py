from typing import override
from bot.buildings.upgrade_building import UpgradeBuilding
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class OrbitalCommand(UpgradeBuilding):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.ORBITALCOMMAND
        self.abilityId = AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND
        self.name = "Orbital Command"
        self.base_building_id = UnitTypeId.COMMANDCENTER

    @override
    @property
    def base_buildings(self) -> Units:
        townhalls_amount: int = self.bot.townhalls.ready.amount
        return self.bot.structures(self.base_building_id).ready.idle.filter(
            lambda unit: townhalls_amount <= 3 or unit.position not in self.bot.expansions.positions
        )

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

        # if each expansion we have has less workers than the optimal amount, we can upgrade to Orbital Command
        # otherwise we float and build a PF
        optimal_worker_count: int = (
            sum(expansion.optimal_mineral_workers for expansion in self.bot.expansions.taken)
            + sum(expansion.optimal_vespene_workers for expansion in self.bot.expansions.taken)
        )
        is_mining_optimal: bool = self.bot.supply_workers < optimal_worker_count - 5
        return is_mining_optimal