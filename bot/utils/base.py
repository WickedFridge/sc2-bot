from bot.combat.threats import Threat
from bot.superbot import Superbot
from sc2.position import Point2
from sc2.unit import Unit


class Base:
    bot: Superbot
    cc: Unit
    threat: Threat

    def __init__(self, bot: Superbot, cc: Unit, threat: Threat) -> None:
        self.bot = bot
        self.cc = cc
        self.threat = threat
        
    @property
    def position(self) -> Point2:
        return self.cc.position