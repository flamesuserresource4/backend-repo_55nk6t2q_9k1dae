"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Sankalp Cricket Club Schemas

class Player(BaseModel):
    """Players collection schema (collection name: "player")"""
    name: str = Field(..., description="Player full name")
    role: str = Field(..., description="Batting/Bowling/All-rounder/Wicket-keeper")
    batting_style: Optional[str] = Field(None, description="Batting style, e.g., RHB/LHB")
    bowling_style: Optional[str] = Field(None, description="Bowling style, e.g., RMF/OS/LS")
    photo_url: Optional[HttpUrl] = Field(None, description="Public URL to player photo")
    matches: Optional[int] = Field(0, ge=0)
    runs: Optional[int] = Field(0, ge=0)
    wickets: Optional[int] = Field(0, ge=0)
    catches: Optional[int] = Field(0, ge=0)

class Founder(BaseModel):
    """Founding members collection schema (collection name: "founder")"""
    name: str
    role: Optional[str] = Field(None, description="Role in club founding")
    bio: Optional[str] = None
    photo_url: Optional[HttpUrl] = None
    year: Optional[int] = Field(None, description="Year involved/founded")

class ClubConfig(BaseModel):
    """Configuration for external integrations (collection name: "clubconfig")"""
    club_name: str = Field("Sankalp")
    play_cricket_club_id: Optional[str] = Field(None, description="ECB Play-Cricket club ID")
    play_cricket_team_id: Optional[str] = Field(None, description="ECB Play-Cricket team ID")
    play_cricket_api_key: Optional[str] = Field(None, description="ECB Play-Cricket API key if available")

# You can add more schemas like Match, Sponsor, News if needed.
