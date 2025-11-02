from typing import Dict, List, override
from bot.buildings.building import Building
from bot.macro.resources import Resources
from bot.strategy.strategy_types import Situation
from bot.utils.matchup import Matchup, get_matchup
from sc2.game_data import Cost
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units

class BarracksAddon(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BARRACKSTECHREACTOR
        self.name = "Barracks Addon"

    @property
    def matchup(self) -> Matchup:
        return get_matchup(self.bot)

    @property
    def sequence(self) -> List[UnitTypeId]:
        match (self.matchup):
            case Matchup.TvP:        
                return [
                    UnitTypeId.BARRACKSREACTOR,
                    UnitTypeId.BARRACKSTECHLAB,
                    UnitTypeId.BARRACKSTECHLAB,
                    UnitTypeId.BARRACKSREACTOR,
                    UnitTypeId.BARRACKSTECHLAB,
                ]
            case Matchup.TvZ:        
                return [
                    UnitTypeId.BARRACKSREACTOR,
                    UnitTypeId.BARRACKSTECHLAB,
                    UnitTypeId.BARRACKSREACTOR,
                    UnitTypeId.BARRACKSTECHLAB,
                    UnitTypeId.BARRACKSTECHLAB,
                ]
            case Matchup.TvT:        
                return [
                    UnitTypeId.BARRACKSREACTOR,
                    UnitTypeId.BARRACKSTECHLAB,
                    UnitTypeId.BARRACKSREACTOR,
                ]
            case _:
                return [
                    UnitTypeId.BARRACKSREACTOR,
                    UnitTypeId.BARRACKSTECHLAB,
                    UnitTypeId.BARRACKSREACTOR,
                ]
    
    
    @property
    def barracks_without_addon(self) -> Units:
        """Returns barracks that are idle and do not have an addon."""
        return self.bot.structures(UnitTypeId.BARRACKS).ready.idle.filter(
            lambda barrack: not barrack.has_add_on and self.bot.in_placement_grid(barrack.add_on_position)
        )

    @property
    def techlab_count(self) -> int:
        return self.bot.structures(UnitTypeId.BARRACKSTECHLAB).ready.amount + self.bot.already_pending(UnitTypeId.BARRACKSTECHLAB)

    @property
    def reactor_count(self) -> int:
        return self.bot.structures(UnitTypeId.BARRACKSREACTOR).ready.amount + self.bot.already_pending(UnitTypeId.BARRACKSREACTOR)
    
    @property
    def current_addons(self) -> List[UnitTypeId]:
        return self.techlab_count * [UnitTypeId.BARRACKSTECHLAB] + self.reactor_count * [UnitTypeId.BARRACKSREACTOR]
    
    @property
    def next_addon(self) -> UnitTypeId:
        """
        Return the next addon type to build based on a repeating sequence.
        Automatically skips fulfilled steps if an addon was destroyed or delayed.
        """
        techlabs: int = self.techlab_count
        reactors: int = self.reactor_count

        for i in range(techlabs + reactors):
            if (self.sequence[i % len(self.sequence)] == UnitTypeId.BARRACKSTECHLAB):
                if (techlabs >= 1):
                    techlabs -= 1
                else:
                    return UnitTypeId.BARRACKSTECHLAB
            elif (self.sequence[i % len(self.sequence)] == UnitTypeId.BARRACKSREACTOR):
                if (reactors >= 1):
                    reactors -= 1
                else:
                    return UnitTypeId.BARRACKSREACTOR
                
        # If we reach here, we continue the sequence
        return self.sequence[(self.techlab_count + self.reactor_count) % len(self.sequence)]
    
    @override
    @property
    def conditions(self) -> bool:
        return (
            self.barracks_without_addon.amount >= 1
            and self.next_addon == self.unitId
            and not self.bot.composition_manager.should_train(UnitTypeId.REAPER)
            and self.bot.scouting.situation != Situation.UNDER_ATTACK
        )

    @override
    async def build(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        resources_updated: Resources = resources
        for barracks in self.barracks_without_addon:
            building_cost: Cost = self.bot.calculate_cost(self.unitId)
            can_build, resources_updated = resources_updated.update(building_cost)

            if (can_build == False):
                continue
            
            print(f'Reactor/Techlab count: {self.techlab_count}/{self.reactor_count}')
            print(f'Build {self.name}')
            barracks.build(self.unitId)
        return resources_updated

class BarracksReactor(BarracksAddon):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BARRACKSREACTOR
        self.name = "Barracks Reactor"

class BarracksTechlab(BarracksAddon):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BARRACKSTECHLAB
        self.name = "Barracks Techlab"