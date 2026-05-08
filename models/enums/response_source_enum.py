import enum


class ResponseSourceEnum(str, enum.Enum):
    ia     = "ia"
    agent  = "agent"
    hybrid = "hybrid"
