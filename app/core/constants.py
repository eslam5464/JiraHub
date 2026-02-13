from enum import StrEnum


class FieldSizes:
    TINY = 20
    SHORT = 50
    MEDIUM = 255
    LONG = 500
    TEXT = 2000


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class UserStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class JiraIssueStatus(StrEnum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"
    CLOSED = "Closed"


class TeamLabel(StrEnum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    QA = "qa"
    PM = "pm"
    DESIGN = "design"
    MOBILE = "mobile"
    DATA = "data"
