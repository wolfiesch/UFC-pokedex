"""Pydantic models for UFC.com data scraping.

This module defines data models for scraping UFC.com athlete profiles.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class UFCComAthleteListItem(BaseModel):
    """UFC.com athlete list item from the athletes API.

    Represents a single fighter entry from the UFC.com athletes list.
    This is scraped from the Drupal JSON API endpoint.
    """

    name: str = Field(description="Fighter full name (e.g., 'Conor McGregor')")
    slug: str = Field(description="Fighter slug for URL (e.g., 'conor-mcgregor')")
    division: str | None = Field(None, description="Weight division (e.g., 'Lightweight')")
    record: str | None = Field(None, description="Fight record (e.g., '22-6-0')")
    status: str | None = Field(None, description="Fighter status ('Active', 'Retired', etc.)")
    profile_url: HttpUrl | None = Field(None, description="Full URL to UFC.com profile page")

    # Metadata
    item_type: str = Field(
        default="ufc_com_athlete_list",
        description="Item type identifier for pipeline routing",
    )


class UFCComAthleteDetail(BaseModel):
    """UFC.com athlete detail data from individual profile pages.

    Represents complete biographical and location data for a single fighter.
    This is scraped from individual UFC.com athlete profile pages.
    """

    # Identifiers
    slug: str = Field(description="Fighter slug (e.g., 'conor-mcgregor')")
    name: str = Field(description="Fighter full name")

    # Location data - Birthplace
    birthplace: str | None = Field(
        None,
        description="Full birthplace string from UFC.com (e.g., 'Dublin, Ireland')",
    )
    birthplace_city: str | None = Field(None, description="Parsed city from birthplace")
    birthplace_country: str | None = Field(None, description="Parsed country from birthplace")

    # Location data - Training
    training_gym: str | None = Field(
        None,
        description="Training gym name (e.g., 'SBG Ireland')",
    )

    # Additional bio fields
    age: int | None = Field(None, description="Fighter age")
    height: str | None = Field(None, description="Fighter height")
    weight: str | None = Field(None, description="Fighter weight")
    status: str | None = Field(None, description="Fighter status ('Active', 'Retired', etc.)")

    # Metadata
    item_type: str = Field(
        default="ufc_com_athlete_detail",
        description="Item type identifier for pipeline routing",
    )
