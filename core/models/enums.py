import enum


class RunStatus(str, enum.Enum):
    pending = "pending"
    interpreting = "interpreting"
    planning = "planning"
    discovering = "discovering"
    retrieving = "retrieving"
    extracting = "extracting"
    validating = "validating"
    evaluating = "evaluating"
    reasoning = "reasoning"
    storing = "storing"
    alerting = "alerting"
    verified = "verified"
    failed = "failed"


class StageType(str, enum.Enum):
    interpretation = "interpretation"
    discovery = "discovery"
    retrieval = "retrieval"
    extraction = "extraction"
    validation = "validation"
    condition = "condition"
    reasoning = "reasoning"


class Frequency(str, enum.Enum):
    once = "once"
    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
