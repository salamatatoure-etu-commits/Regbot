import enum

class MessageTypeEnum(str, enum.Enum):
    user = "user"
    bot  = "bot"
