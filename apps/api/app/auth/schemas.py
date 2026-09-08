from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SSOExchangeRequest(BaseModel):
    ticket: str = Field(min_length=1, max_length=512)


class PlatformExchange(BaseModel):
    access_token: str = Field(min_length=1)


class PlatformClaims(BaseModel):
    model_config = ConfigDict(extra="ignore")

    iss: str
    aud: str
    sub: UUID
    product_id: UUID
    entitlement_id: UUID
    iat: int
    exp: int
    jti: str = Field(min_length=1, max_length=64)
