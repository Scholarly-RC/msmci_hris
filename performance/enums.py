from enum import Enum


class QuestionnaireTypes(Enum):
    NEPET = "NEPET"
    NAPES = "NAPES"


class EvalutaionSection(Enum):
    SELF = "SELF"
    PEER = "PEER"
