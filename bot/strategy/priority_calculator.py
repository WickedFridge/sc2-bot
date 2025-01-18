from typing import List
from bot.strategy.strategy_types import Priority, Strategy


def get_priorities(strategy: Strategy) -> List[Priority]:
    match(strategy):
        case Strategy.MACRO_SAFE:
            return [
                Priority.ECONOMY,
                Priority.BUILD_DEFENSE,
                Priority.TECH,
                Priority.BUILD_ARMY,
            ]
        case Strategy.MACRO_GREEDY:
            return [
                Priority.ECONOMY,
                Priority.TECH,
                Priority.BUILD_ARMY,
                Priority.BUILD_DEFENSE,
            ]
        case Strategy.TURTLE_ECO:
            return [
                Priority.BUILD_DEFENSE,
                Priority.BUILD_ARMY,
                Priority.ECONOMY,
                Priority.TECH,
            ]
        case Strategy.TURTLE_TECH:
            return [
                Priority.BUILD_DEFENSE,
                Priority.BUILD_ARMY,
                Priority.TECH,
                Priority.ECONOMY,
            ]
        case Strategy.RUSH_TECH_GREEDY:
            return [
                Priority.TECH,
                Priority.ECONOMY,
                Priority.BUILD_DEFENSE,
                Priority.BUILD_ARMY,
            ]
        case Strategy.RUSH_TECH_SAFE:
            return [
                Priority.TECH,
                Priority.BUILD_DEFENSE,
                Priority.ECONOMY,
                Priority.BUILD_ARMY,
            ]