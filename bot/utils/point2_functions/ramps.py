from typing import Literal
from sc2.bot_ai import BotAI
from sc2.game_info import Ramp
from sc2.position import Point2


def find_closest_bottom_ramp(bot: BotAI, position: Point2) -> Ramp:
        return _find_closest_ramp(bot, position, "bottom")

def find_closest_top_ramp(bot: BotAI, position: Point2) -> Ramp:
    return _find_closest_ramp(bot, position, "top")

def _find_closest_ramp(bot: BotAI, position: Point2, extremity: Literal["top","bottom"]):
    closest_ramp: Ramp = bot.game_info.map_ramps[0]
    for ramp in bot.game_info.map_ramps:
        match extremity:
            case "top":
                if (ramp.top_center.distance_to(position) < closest_ramp.top_center.distance_to(position)):
                    closest_ramp = ramp
            case "bottom":
                if (ramp.bottom_center.distance_to(position) < closest_ramp.bottom_center.distance_to(position)):
                    closest_ramp = ramp
            case _:
                print("Error : specify top or bottom of the ramp")
    return closest_ramp