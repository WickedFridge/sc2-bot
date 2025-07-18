from ast import Dict
from bot.combat.combat import Combat
from bot.superbot import Superbot
from bot.units.ghost import Ghost
from bot.units.marauder import Marauder
from bot.units.marine import Marine
from bot.units.medivac import Medivac
from bot.units.scv import Scv
from bot.utils.matchup import Matchup
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Trainer:
    bot: Superbot
    combat: Combat
    scv: Scv
    medivac: Medivac
    marine: Marine
    marauder: Marauder
    ghost: Ghost
    
    def __init__(self, bot: Superbot, combat: Combat) -> None:
        self.bot = bot
        self.combat = combat
        self.scv = Scv(self)
        self.medivac = Medivac(self)
        self.marine = Marine(self)
        self.marauder = Marauder(self)
        self.ghost = Ghost(self)

    @property
    def should_train_marauders(self):
        marine_count: int = self.bot.units(UnitTypeId.MARINE).amount + self.bot.already_pending(UnitTypeId.MARINE)
        
        default_marauder_ratio: Dict[Matchup, float] = {
            Matchup.TvT: 0,
            Matchup.TvZ: 0.1,
            Matchup.TvP: 0.3,
            Matchup.TvR: 0.2,
        }
        enemy_armored_ratio: float = (
            0 if self.combat.known_enemy_army.supply == 0
            else self.combat.known_enemy_army.armored_ground_supply / self.combat.known_enemy_army.supply
        )
        armored_ratio: float = (
            0 if self.combat.army_supply == 0
            else self.combat.armored_supply / self.combat.army_supply
        )
        if (
            armored_ratio < enemy_armored_ratio or
            (armored_ratio < default_marauder_ratio[self.bot.matchup] and marine_count >= 8)
        ):
            return True
        return False
    
    @property
    def should_train_ghosts(self):
        return self.bot.structures(UnitTypeId.GHOSTACADEMY).ready.amount > 0
