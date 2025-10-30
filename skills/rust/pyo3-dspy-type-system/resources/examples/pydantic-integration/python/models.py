"""
Pydantic models with comprehensive field validation.

Demonstrates:
- Field validators for format validation (email, URL)
- Range constraints (min/max values)
- String pattern matching
- Custom validation logic
- Model-level validators
- Enum validation with Literal types
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import re


class UserProfile(BaseModel):
    """User profile with comprehensive validation.

    Validates:
    - Email format and normalization
    - Age range constraints
    - Role enum values
    - Bio length limits
    - Website URL format
    """

    email: str = Field(
        ...,
        description="User email address",
        examples=["user@example.com"]
    )
    age: int = Field(
        ...,
        ge=13,
        le=120,
        description="User age (must be 13-120)"
    )
    role: Literal["basic", "premium", "admin"] = Field(
        default="basic",
        description="User role"
    )
    bio: Optional[str] = Field(
        None,
        max_length=500,
        description="User biography (max 500 chars)"
    )
    website: Optional[str] = Field(
        None,
        description="User website URL"
    )

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format and normalize to lowercase."""
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v.lower()

    @field_validator('website')
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        """Validate website URL format."""
        if v is None:
            return v
        if not re.match(r'^https?://', v):
            raise ValueError('Website must start with http:// or https://')
        return v

    @field_validator('bio')
    @classmethod
    def validate_bio(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace and validate bio length."""
        if v is None:
            return v
        v = v.strip()
        if len(v) == 0:
            return None
        return v

    @model_validator(mode='after')
    def validate_premium_features(self):
        """Model-level validation: premium users must have bio."""
        if self.role == 'premium' and not self.bio:
            raise ValueError('Premium users must provide a bio')
        return self

    class Config:
        str_strip_whitespace = True
        json_schema_extra = {
            "example": {
                "email": "alice@example.com",
                "age": 28,
                "role": "premium",
                "bio": "Software engineer interested in AI",
                "website": "https://alice.dev"
            }
        }


class ProductReview(BaseModel):
    """Product review with validation.

    Validates:
    - Rating range (1-5)
    - Sentiment enum
    - Review text constraints
    - Verified purchase flag
    """

    product_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Product name"
    )
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Rating from 1 to 5 stars"
    )
    review_text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Review text (10-2000 chars)"
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        ...,
        description="Overall sentiment"
    )
    verified_purchase: bool = Field(
        default=False,
        description="Whether this is a verified purchase"
    )

    @field_validator('review_text')
    @classmethod
    def validate_review_text(cls, v: str) -> str:
        """Validate review text is substantial."""
        v = v.strip()
        if len(v) < 10:
            raise ValueError('Review must be at least 10 characters')
        return v

    @model_validator(mode='after')
    def validate_sentiment_rating(self):
        """Ensure sentiment matches rating."""
        if self.rating >= 4 and self.sentiment == 'negative':
            raise ValueError('High rating inconsistent with negative sentiment')
        if self.rating <= 2 and self.sentiment == 'positive':
            raise ValueError('Low rating inconsistent with positive sentiment')
        return self

    class Config:
        str_strip_whitespace = True
        json_schema_extra = {
            "example": {
                "product_name": "Ergonomic Keyboard",
                "rating": 5,
                "review_text": "Excellent keyboard, great for typing all day",
                "sentiment": "positive",
                "verified_purchase": True
            }
        }
