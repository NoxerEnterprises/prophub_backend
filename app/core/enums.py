from enum import StrEnum


class UserRole(StrEnum):
    USER = "USER"
    AGENT = "AGENT"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class AgentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISABLED = "DISABLED"


class AdminAction(StrEnum):
    AGENT_APPROVED = "AGENT_APPROVED"
    AGENT_REJECTED = "AGENT_REJECTED"
    AGENT_DISABLED = "AGENT_DISABLED"
    AGENT_ENABLED = "AGENT_ENABLED"
    ADMIN_CREATED = "ADMIN_CREATED"
    PROPERTY_CREATED = "PROPERTY_CREATED"
    PROPERTY_UPDATED = "PROPERTY_UPDATED"
    PROPERTY_DELETED = "PROPERTY_DELETED"
    PROPERTY_MEDIA_UPLOADED = "PROPERTY_MEDIA_UPLOADED"
    PROPERTY_MEDIA_DELETED = "PROPERTY_MEDIA_DELETED"
    PROPERTY_HIDDEN = "PROPERTY_HIDDEN"
    PROPERTY_RESTORED = "PROPERTY_RESTORED"
    PROPERTY_ADMIN_DELETED = "PROPERTY_ADMIN_DELETED"
    TRANSACTION_VERIFIED = "TRANSACTION_VERIFIED"
    AGENT_MARKED_PAID = "AGENT_MARKED_PAID"


class PropertyCategory(StrEnum):
    LAND = "LAND"
    HOUSE = "HOUSE"
    APARTMENT = "APARTMENT"
    COMMERCIAL = "COMMERCIAL"
    OFFICE = "OFFICE"
    SHOP = "SHOP"
    WAREHOUSE = "WAREHOUSE"


class ListingType(StrEnum):
    SALE = "SALE"
    RENT = "RENT"
    SHORTLET = "SHORTLET"


class PropertyStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    SOLD = "SOLD"
    RENTED = "RENTED"
    PENDING = "PENDING"
    HIDDEN = "HIDDEN"


class PropertySort(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"


class MediaType(StrEnum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class TransactionProvider(StrEnum):
    PAYSTACK = "PAYSTACK"


class TransactionType(StrEnum):
    AGENT_VERIFICATION = "AGENT_VERIFICATION"


class TransactionStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"
    ONGOING = "ONGOING"
    CANCELLED = "CANCELLED"


class ChatType(StrEnum):
    PRIVATE = "PRIVATE"
    GROUP = "GROUP"


class ChatParticipantRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class MessageType(StrEnum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    SYSTEM = "SYSTEM"
