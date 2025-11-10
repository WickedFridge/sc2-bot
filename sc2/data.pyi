"""Type stubs for sc2.data module

This stub provides static type information for dynamically generated enums.
The enums in sc2.data are created at runtime using enum.Enum() with protobuf
enum descriptors, which makes them invisible to static type checkers.

This stub file (PEP 561 compliant) allows type checkers like Pylance, Pyright,
and mypy to understand the structure and members of these enums.
"""

from __future__ import annotations

from enum import Enum

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
    Invalid: int

class TargetType(Enum):
    Ground: int
    Air: int
    Any: int
    Invalid: int

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
    various action results and error conditions.
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
    CantBuildTooCloseToDropOff: int
    CantBuildLocationInvalid: int
    CantSeeBuildLocation: int
    CantBuildTooCloseToCreepSource: int
    CantBuildTooCloseToResources: int
    CantBuildTooFarFromWater: int
    CantBuildTooFarFromCreepSource: int
    CantBuildTooFarFromBuildPowerSource: int
    CantBuildOnDenseTerrain: int
    CantTrainTooFarFromTrainPowerSource: int
    CantLandLocationInvalid: int
    CantSeeLandLocation: int
    CantLandTooCloseToCreepSource: int
    CantLandTooCloseToResources: int
    CantLandTooFarFromWater: int
    CantLandTooFarFromCreepSource: int
    CantLandTooFarFromBuildPowerSource: int
    CantLandTooFarFromTrainPowerSource: int
    CantLandOnDenseTerrain: int
    AddOnTooFarFromBuilding: int
    MustBuildRefineryFirst: int
    BuildingIsUnderConstruction: int
    CantFindDropOff: int
    CantLoadOtherPlayersUnits: int
    NotEnoughRoomToLoadUnit: int
    CantUnloadUnitsThere: int
    CantWarpInUnitsThere: int
    CantLoadImmobileUnits: int
    CantRechargeImmobileUnits: int
    CantRechargeUnderConstructionUnits: int
    CantLoadThatUnit: int
    NoCargoToUnload: int
    LoadAllNoTargetsFound: int
    NotWhileOccupied: int
    CantAttackWithoutAmmo: int
    CantHoldAnyMoreAmmo: int
    TechRequirementsNotMet: int
    MustLockdownUnitFirst: int
    MustTargetUnit: int
    MustTargetInventory: int
    MustTargetVisibleUnit: int
    MustTargetVisibleLocation: int
    MustTargetWalkableLocation: int
    MustTargetPawnableUnit: int
    YouCantControlThatUnit: int
    YouCantIssueCommandsToThatUnit: int
    MustTargetResources: int
    RequiresHealTarget: int
    RequiresRepairTarget: int
    NoItemsToDrop: int
    CantHoldAnyMoreItems: int
    CantHoldThat: int
    TargetHasNoInventory: int
    CantDropThisItem: int
    CantMoveThisItem: int
    CantPawnThisUnit: int
    MustTargetCaster: int
    CantTargetCaster: int
    MustTargetOuter: int
    CantTargetOuter: int
    MustTargetYourOwnUnits: int
    CantTargetYourOwnUnits: int
    MustTargetFriendlyUnits: int
    CantTargetFriendlyUnits: int
    MustTargetNeutralUnits: int
    CantTargetNeutralUnits: int
    MustTargetEnemyUnits: int
    CantTargetEnemyUnits: int
    MustTargetAirUnits: int
    CantTargetAirUnits: int
    MustTargetGroundUnits: int
    CantTargetGroundUnits: int
    MustTargetStructures: int
    CantTargetStructures: int
    MustTargetLightUnits: int
    CantTargetLightUnits: int
    MustTargetArmoredUnits: int
    CantTargetArmoredUnits: int
    MustTargetBiologicalUnits: int
    CantTargetBiologicalUnits: int
    MustTargetHeroicUnits: int
    CantTargetHeroicUnits: int
    MustTargetRoboticUnits: int
    CantTargetRoboticUnits: int
    MustTargetMechanicalUnits: int
    CantTargetMechanicalUnits: int
    MustTargetPsionicUnits: int
    CantTargetPsionicUnits: int
    MustTargetMassiveUnits: int
    CantTargetMassiveUnits: int
    MustTargetMissile: int
    CantTargetMissile: int
    MustTargetWorkerUnits: int
    CantTargetWorkerUnits: int
    MustTargetEnergyCapableUnits: int
    CantTargetEnergyCapableUnits: int
    MustTargetShieldCapableUnits: int
    CantTargetShieldCapableUnits: int
    MustTargetFlyers: int
    CantTargetFlyers: int
    MustTargetBuriedUnits: int
    CantTargetBuriedUnits: int
    MustTargetCloakedUnits: int
    CantTargetCloakedUnits: int
    MustTargetUnitsInAStasisField: int
    CantTargetUnitsInAStasisField: int
    MustTargetUnderConstructionUnits: int
    CantTargetUnderConstructionUnits: int
    MustTargetDeadUnits: int
    CantTargetDeadUnits: int
    MustTargetRevivableUnits: int
    CantTargetRevivableUnits: int
    MustTargetHiddenUnits: int
    CantTargetHiddenUnits: int
    CantRechargeOtherPlayersUnits: int
    MustTargetHallucinations: int
    CantTargetHallucinations: int
    MustTargetInvulnerableUnits: int
    CantTargetInvulnerableUnits: int
    MustTargetDetectedUnits: int
    CantTargetDetectedUnits: int
    CantTargetUnitWithEnergy: int
    CantTargetUnitWithShields: int
    MustTargetUncommandableUnits: int
    CantTargetUncommandableUnits: int
    MustTargetPreventDefeatUnits: int
    CantTargetPreventDefeatUnits: int
    MustTargetPreventRevealUnits: int
    CantTargetPreventRevealUnits: int
    MustTargetPassiveUnits: int
    CantTargetPassiveUnits: int
    MustTargetStunnedUnits: int
    CantTargetStunnedUnits: int
    MustTargetSummonedUnits: int
    CantTargetSummonedUnits: int
    MustTargetUser1: int
    CantTargetUser1: int
    MustTargetUnstoppableUnits: int
    CantTargetUnstoppableUnits: int
    MustTargetResistantUnits: int
    CantTargetResistantUnits: int
    MustTargetDazedUnits: int
    CantTargetDazedUnits: int
    CantLockdown: int
    CantMindControl: int
    MustTargetDestructibles: int
    CantTargetDestructibles: int
    MustTargetItems: int
    CantTargetItems: int
    NoCalldownAvailable: int
    WaypointListFull: int
    MustTargetRace: int
    CantTargetRace: int
    MustTargetSimilarUnits: int
    CantTargetSimilarUnits: int
    CantFindEnoughTargets: int
    AlreadySpawningLarva: int
    CantTargetExhaustedResources: int
    CantUseMinimap: int
    CantUseInfoPanel: int
    OrderQueueIsFull: int
    CantHarvestThatResource: int
    HarvestersNotRequired: int
    AlreadyTargeted: int
    CantAttackWeaponsDisabled: int
    CouldntReachTarget: int
    TargetIsOutOfRange: int
    TargetIsTooClose: int
    TargetIsOutOfArc: int
    CantFindTeleportLocation: int
    InvalidItemClass: int
    CantFindCancelOrder: int

# Module-level dictionaries
race_worker: dict[Race, UnitTypeId]
race_townhalls: dict[Race, set[UnitTypeId]]
warpgate_abilities: dict[AbilityId, AbilityId]
race_gas: dict[Race, UnitTypeId]
