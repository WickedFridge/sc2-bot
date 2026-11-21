from __future__ import annotations
from dataclasses import dataclass, field, fields
from typing import Any, Callable, Dict, List

# Bump only when an existing field is renamed or changes meaning, and add the matching migration.
# Adding a new field (with a default value) does NOT require a bump.
CURRENT_SCHEMA_VERSION: int = 1

# MIGRATIONS[n] converts a raw dict from schema version n to version n + 1
MIGRATIONS: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

RESULT_CRASH: str = "Crash"
RESULT_UNKNOWN: str = "Unknown"

# trigger of a build switch made by hand through the debug chat commands
TRIGGER_DEBUG: str = "DEBUG"


@dataclass
class BuildUsage:
    name: str = ""
    start_time: float = 0.0
    # why we switched to this build: a Situation name, TRIGGER_DEBUG, or None for the opening (and unknown for old matches)
    trigger: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "start_time": self.start_time, "trigger": self.trigger}

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> BuildUsage:
        trigger = raw.get("trigger")
        return BuildUsage(
            name=str(raw.get("name", "")),
            start_time=float(raw.get("start_time", 0.0)),
            trigger=None if trigger is None else str(trigger),
        )


@dataclass
class CheeseDetection:
    name: str = ""
    time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "time": self.time}

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> CheeseDetection:
        return CheeseDetection(
            name=str(raw.get("name", "")),
            time=float(raw.get("time", 0.0)),
        )


@dataclass
class MatchRecord:
    """
    One played match. Every field must have a default value,
    so that records written by older versions can still be loaded.
    Unknown keys (written by newer versions) are kept in `extra`.
    """
    schema_version: int = CURRENT_SCHEMA_VERSION
    bot_version: str = ""
    date: str = ""
    source: str = ""
    opponent_id: str = ""
    opponent_race_requested: str = ""
    opponent_race: str = ""
    map: str = ""
    matchup: str = ""
    builds: List[BuildUsage] = field(default_factory=list)
    # cheeses detected during the match, each one once. None means not tracked (matches played before this field existed)
    cheeses: List[CheeseDetection] | None = None
    result: str = RESULT_UNKNOWN
    duration: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for f in fields(self):
            if (f.name == "extra"):
                continue
            value = getattr(self, f.name)
            if (f.name == "builds"):
                value = [build.to_dict() for build in value]
            if (f.name == "cheeses" and value is not None):
                value = [cheese.to_dict() for cheese in value]
            data[f.name] = value
        # unknown keys from newer versions are written back untouched
        for key, value in self.extra.items():
            data.setdefault(key, value)
        return data

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> MatchRecord:
        raw = dict(raw)
        version: int = int(raw.get("schema_version", 1))
        while (version < CURRENT_SCHEMA_VERSION):
            raw = MIGRATIONS[version](raw)
            version += 1
        raw["schema_version"] = max(version, CURRENT_SCHEMA_VERSION)

        known_fields = {f.name for f in fields(MatchRecord)} - {"extra"}
        kwargs: Dict[str, Any] = {key: raw[key] for key in known_fields if key in raw}
        kwargs["builds"] = [BuildUsage.from_dict(build) for build in raw.get("builds", [])]
        raw_cheeses: List[Dict[str, Any]] | None = raw.get("cheeses")
        kwargs["cheeses"] = None if raw_cheeses is None else [CheeseDetection.from_dict(cheese) for cheese in raw_cheeses]
        extra: Dict[str, Any] = dict(raw.get("extra", {}))
        extra.update({key: value for key, value in raw.items() if key not in known_fields and key != "extra"})
        return MatchRecord(**kwargs, extra=extra)
