"""Type stubs for sc2.data module

This stub provides static type information for dynamically generated enums.
The enums in sc2.data are created at runtime using enum.Enum() with protobuf
enum descriptors, which makes them invisible to static type checkers.

This stub file (PEP 561 compliant) allows type checkers like Pylance, Pyright,
and mypy to understand the structure and members of these enums.
"""

from enum import Enum
from typing import Dict, Set

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId

# Enums created from sc2api_pb2
class CreateGameError(Enum):
    MissingMap: int
    InvalidMapPath: int
    InvalidMapData: int
    InvalidMapName: int
    InvalidMapHandle: int
    MissingPlayerSetup: int
    InvalidPlayerSetup: int
    MultiplayerUnsupported: int

class PlayerType(Enum):
    Participant: int
    Computer: int
    Observer: int

class Difficulty(Enum):
    VeryEasy: int
    Easy: int
    Medium: int
    MediumHard: int
    Hard: int
    Harder: int
    VeryHard: int
    CheatVision: int
    CheatMoney: int
    CheatInsane: int

class AIBuild(Enum):
    RandomBuild: int
    Rush: int
    Timing: int
    Power: int
    Macro: int
    Air: int

class Status(Enum):
    launched: int
    init_game: int
    in_game: int
    in_replay: int
    ended: int
    quit: int
    unknown: int

class Result(Enum):
    Victory: int
    Defeat: int
    Tie: int
    Undecided: int

class Alert(Enum):
    AlertError: int
    AddOnComplete: int
    BuildingComplete: int
    BuildingUnderAttack: int
    LarvaHatched: int
    MergeComplete: int
    MineralsExhausted: int
    MorphComplete: int
    MothershipComplete: int
    MULEExpired: int
    NuclearLaunchDetected: int
    NukeComplete: int
    NydusWormDetected: int
    ResearchComplete: int
    TrainError: int
    TrainUnitComplete: int
    TrainWorkerComplete: int
    TransformationComplete: int
    UnitUnderAttack: int
    UpgradeComplete: int
    VespeneExhausted: int
    WarpInComplete: int

class ChatChannel(Enum):
    Broadcast: int
    Team: int

# Enums created from common_pb2
class Race(Enum):
    """StarCraft II race enum.
    
    Members:
        NoRace: No race specified
        Terran: Terran race
        Zerg: Zerg race
        Protoss: Protoss race
        Random: Random race selection
    """
    NoRace: int
    Terran: int
    Zerg: int
    Protoss: int
    Random: int

# Enums created from raw_pb2
class DisplayType(Enum):
    Visible: int
    Snapshot: int
    Hidden: int
    Placeholder: int

class Alliance(Enum):
    Self: int
    Ally: int
    Neutral: int
    Enemy: int

class CloakState(Enum):
    CloakedUnknown: int
    Cloaked: int
    CloakedDetected: int
    NotCloaked: int
    CloakedAllied: int

# Enums created from data_pb2
class Attribute(Enum):
    Light: int
    Armored: int
    Biological: int
    Mechanical: int
    Robotic: int
    Psionic: int
    Massive: int
    Structure: int
    Hover: int
    Heroic: int
    Summoned: int

class TargetType(Enum):
    Ground: int
    Air: int
    Any: int

class Target(Enum):
    # Note: The protobuf enum member 'None' is a Python keyword,
    # so at runtime it may need special handling
    Point: int
    Unit: int
    PointOrUnit: int
    PointOrNone: int

# Enums created from error_pb2
class ActionResult(Enum):
    """Action result codes from game engine.
    
    This enum contains a large number of members (~200+) representing
    various action results and error conditions. Only the most commonly
    used members are listed here. All members are available at runtime.
    """
    Success: int
    NotSupported: int
    Error: int
    CantQueueThatOrder: int
    Retry: int
    Cooldown: int
    QueueIsFull: int
    RallyQueueIsFull: int
    NotEnoughMinerals: int
    NotEnoughVespene: int
    NotEnoughTerrazine: int
    NotEnoughCustom: int
    NotEnoughFood: int
    FoodUsageImpossible: int
    NotEnoughLife: int
    NotEnoughShields: int
    NotEnoughEnergy: int
    LifeSuppressed: int
    ShieldsSuppressed: int
    EnergySuppressed: int
    NotEnoughCharges: int
    CantAddMoreCharges: int
    TooMuchMinerals: int
    TooMuchVespene: int
    TooMuchTerrazine: int
    TooMuchCustom: int
    TooMuchFood: int
    TooMuchLife: int
    TooMuchShields: int
    TooMuchEnergy: int
    MustTargetUnitWithLife: int
    MustTargetUnitWithShields: int
    MustTargetUnitWithEnergy: int
    CantTrade: int
    CantSpend: int
    CantTargetThatUnit: int
    CouldntAllocateUnit: int
    UnitCantMove: int
    TransportIsHoldingPosition: int
    BuildTechRequirementsNotMet: int
    CantFindPlacementLocation: int
    CantBuildOnThat: int
    # ... approximately 150+ more members exist at runtime

# Module-level dictionaries
race_worker: Dict[Race, UnitTypeId]
race_townhalls: Dict[Race, Set[UnitTypeId]]
warpgate_abilities: Dict[AbilityId, AbilityId]
race_gas: Dict[Race, UnitTypeId]
