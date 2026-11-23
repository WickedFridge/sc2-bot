from __future__ import annotations
from collections import Counter
from typing import List, Optional, TYPE_CHECKING

from attr import dataclass
from bot.army_composition.army_composition_manager import ArmyCompositionManager
from bot.strategy.build_order.addon_swap import AddonSwapManager
from bot.macro.expansion_manager import Expansions
from bot.macro.map.map import MapData
from bot.scouting.ghost_units.manager import GhostUnitsManager
from bot.scouting.scouting import Scouting
from bot.strategy.build_order.manager import BuildOrderManager
from bot.strategy.handler import StrategyHandler
from bot.utils.matchup import Matchup
from sc2.bot_ai import BotAI
from sc2.cache import property_cache_once_per_frame
from sc2.data import Attribute
from sc2.dicts.unit_research_abilities import RESEARCH_INFO
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit, UnitOrder
from sc2.units import Units

if TYPE_CHECKING:
    from bot.buildings.handler import BuildingsHandler  # circular import, type hints only
    from bot.combat.anchors import Anchors  # circular import, type hints only

class Superbot(BotAI):
    addon_swap: AddonSwapManager
    buildings: BuildingsHandler
    anchors: Anchors
    opponent_id: str | None = None
    is_ladder: bool = False

    @property
    def matchup(self) -> Matchup:
        pass
    
    @property
    def expansions(self) -> Expansions:
        pass
    
    @property
    def map(self) -> MapData:
        pass

    @property
    def scouting(self) -> Scouting:
        pass

    @property
    def strategy(self) -> StrategyHandler:
        pass
    
    @property
    def composition_manager(self) -> ArmyCompositionManager:
        pass

    @property
    def build_order(self) -> BuildOrderManager:
        pass

    @property
    def ghost_units(self) -> GhostUnitsManager:
        pass

    @property
    def stim_completed(self) -> bool:
        return self.already_pending_upgrade(UpgradeId.STIMPACK) == 1
    
    @property
    def stim_almost_completed(self) -> bool:
        return self.already_pending_upgrade(UpgradeId.STIMPACK) >= 0.85
    
    @property
    def orbital_tech_available(self) -> bool:
        return self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9
    
    
    @property_cache_once_per_frame
    def units_with_passengers(self) -> Units:
        units: Units = self.units.copy()
        if (units.amount == 0):
            return units
        for medivac in units(UnitTypeId.MEDIVAC):
            if (medivac.has_cargo):
                for passenger in medivac.passengers:
                    units.append(passenger)
        return units
    
    def equivalences(self, unit_type: UnitTypeId) -> List[UnitTypeId]:
        match (unit_type):
            case UnitTypeId.THOR | UnitTypeId.THORAP:
                return [UnitTypeId.THOR, UnitTypeId.THORAP]
            case UnitTypeId.HELLION | UnitTypeId.HELLIONTANK:
                return [UnitTypeId.HELLION, UnitTypeId.HELLIONTANK]
            case UnitTypeId.VIKINGFIGHTER | UnitTypeId.VIKINGASSAULT:
                return [UnitTypeId.VIKINGFIGHTER, UnitTypeId.VIKINGASSAULT]
            case UnitTypeId.SIEGETANK | UnitTypeId.SIEGETANKSIEGED:
                return [UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED]            
            case _:
                return [unit_type]

    @property
    def ordered_this_frame(self) -> Counter[UnitTypeId]:
        """
        Units ordered during the current frame. already_pending is cached once per frame,
        so these orders are only seen by it on the next frame: without this counter,
        several buildings could train the last missing unit in the same frame.
        """
        game_loop: int = self.state.game_loop
        if (getattr(self, '_ordered_frame', None) != game_loop):
            self._ordered_frame = game_loop
            self._ordered_this_frame = Counter()
        return self._ordered_this_frame

    def register_order(self, unit_type: UnitTypeId) -> None:
        self.ordered_this_frame[unit_type] += 1

    def total_unit_amount(self, unit_type: UnitTypeId) -> int:
        unit_types: List[UnitTypeId] = self.equivalences(unit_type)
        # return sum(self.units_with_passengers(u_type).amount + self.already_pending(u_type) for u_type in unit_types)
        total_amount: int = self.units_with_passengers(unit_types).amount
        ordered: Counter[UnitTypeId] = self.ordered_this_frame
        for u_type in unit_types:
            total_amount += self.already_pending(u_type) + ordered[u_type]
        return total_amount

    def already_pending(self, unit_type: UpgradeId | UnitTypeId) -> float:
        """
        Same as BotAI.already_pending, minus the structure orders whose structure is
        already ready. On the frame a structure completes, its creation order can still
        be there (the SCV's BUILD_REFINERY, the barracks' BUILD_TECHLAB...), so the
        structure was counted twice: once ready, once pending.
        """
        pending: float = super().already_pending(unit_type)
        if (
            pending == 0
            or isinstance(unit_type, UpgradeId)
            or not self.game_data.units[unit_type.value].has_attribute(Attribute.Structure)
        ):
            return pending
        creation_ability = self.game_data.units[unit_type.value].creation_ability
        if (creation_ability is None):
            return pending
        ability: AbilityId = creation_ability.exact_id
        ready: Units = self.structures.ready
        ready_tags: set[int] = ready.tags
        resolved: int = sum(
            1
            for unit in self.units + self.structures
            for order in unit.orders
            if (
                order.ability.exact_id == ability
                and self._creation_order_resolved(unit, order, unit_type, ready, ready_tags)
            )
        )
        return max(0, pending - resolved)

    def _creation_order_resolved(
        self, unit: Unit, order: UnitOrder, unit_type: UnitTypeId, ready: Units, ready_tags: set[int]
    ) -> bool:
        """True if the structure this creation order produces is already ready."""
        if (unit.is_structure):
            # morph (CC -> Orbital): the unit already is the target type
            if (unit.type_id == unit_type and unit.is_ready):
                return True
            # addon: built by its production building
            return unit.add_on_tag != 0 and unit.add_on_tag in ready_tags
        target = order.target
        if (isinstance(target, int)):
            # refinery: targets the geyser (or the refinery once started)
            if (target in ready_tags):
                return True
            geyser: Optional[Unit] = self.vespene_geyser.find_by_tag(target)
            return geyser is not None and any(s.distance_to(geyser) < 1 for s in ready)
        if (isinstance(target, Point2)):
            return any(s.distance_to(target) < 1 for s in ready)
        return False

    def upgrade_started(self, upgrade: UpgradeId) -> bool:
        """
        True if the upgrade is completed or being researched.
        Unlike already_pending_upgrade, doesn't rely on order.progress (0.0 right after the
        research starts) nor only on game_data's research_ability (wrong for some upgrades):
        any structure order matching one of the known research abilities counts.
        """
        if (upgrade in self.state.upgrades):
            return True
        abilities: set[AbilityId] = {
            researches[upgrade]["ability"]
            for researches in RESEARCH_INFO.values()
            if upgrade in researches
        }
        research_ability = self.game_data.upgrades[upgrade.value].research_ability
        if (research_ability is not None):
            abilities.add(research_ability.exact_id)
        return any(
            order.ability.exact_id in abilities
            for structure in self.structures
            for order in structure.orders
        )

    def units_produced(self, unit_type: UnitTypeId) -> int:
        """Units produced this game (popped + in production), dead ones included."""
        # units_created is tag based: morphs (hellion -> hellbat) or medivac pickups aren't counted twice
        return sum(
            self.units_created[u_type] + int(self.already_pending(u_type))
            for u_type in self.equivalences(unit_type)
        )