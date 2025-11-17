"""
Pydantic schemas for review and rating API endpoints.

This module contains request and response schemas for managing
reviews, ratings, and review helpfulness tracking.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.reviews import ReviewStatus


class ReviewCreate(BaseModel):
    """Schema for creating a new review."""
    appointment_id: uuid.UUID
    
    # Ratings (1-5 stars)
    overall_rating: int = Field(..., ge=1, le=5, description="Overall rating (1-5 stars)")
    service_quality_rating: Optional[int] = Field(None, ge=1, le=5)
    cleanliness_rating: Optional[int] = Field(None, ge=1, le=5)
    value_rating: Optional[int] = Field(None, ge=1, le=5)
    punctuality_rating: Optional[int] = Field(None, ge=1, le=5)
    
    # Review content
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None


class ReviewUpdate(BaseModel):
    """Schema for updating a review."""
    # Ratings
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    service_quality_rating: Optional[int] = Field(None, ge=1, le=5)
    cleanliness_rating: Optional[int] = Field(None, ge=1, le=5)
    value_rating: Optional[int] = Field(None, ge=1, le=5)
    punctuality_rating: Optional[int] = Field(None, ge=1, le=5)
    
    # Review content
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None


class BusinessResponseCreate(BaseModel):
    """Schema for business response to a review."""
    business_response: str = Field(..., min_length=1, max_length=2000)


class ReviewResponse(BaseModel):
    """Response schema for review data."""
    id: uuid.UUID
    
    # Relationships
    appointment_id: uuid.UUID
    client_id: uuid.UUID
    business_id: uuid.UUID
    
    # Ratings
    overall_rating: int
    service_quality_rating: Optional[int]
    cleanliness_rating: Optional[int]
    value_rating: Optional[int]
    punctuality_rating: Optional[int]
    average_detailed_rating: float
    
    # Review content
    title: Optional[str]
    comment: Optional[str]
    
    # Status
    status: ReviewStatus
    is_verified: bool
    is_visible: bool
    
    # Business response
    business_response: Optional[str]
    business_response_date: Optional[datetime]
    
    # Moderation
    flagged_reason: Optional[str]
    moderated_by: Optional[str]
    moderated_at: Optional[datetime]
    
    # Helpfulness
    helpful_count: int
    not_helpful_count: int
    helpfulness_score: float
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    """Response schema for paginated review list."""
    reviews: List[ReviewResponse]
    total: int
    skip: int
    limit: int
    average_rating: Optional[float] = None


class ReviewSummary(BaseModel):
    """Summary statistics for reviews."""
    total_reviews: int
    average_overall_rating: float
    average_service_quality: float
    average_cleanliness: float
    average_value: float
    average_punctuality: float
    
    # Rating distribution
    five_star_count: int
    four_star_count: int
    three_star_count: int
    two_star_count: int
    one_star_count: int


class ReviewHelpfulnessRequest(BaseModel):
    """Schema for marking review as helpful/not helpful."""
    is_helpful: bool = Field(..., description="True=helpful, False=not helpful")


class FlagReviewRequest(BaseModel):
    """Schema for flagging a review."""
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for flagging")


class ModerateReviewRequest(BaseModel):
    """Schema for moderating a review (admin only)."""
    action: str = Field(..., description="Action: 'approve' or 'reject'")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for moderation decision")
    moderated_by: str = Field(..., max_length=200)
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        """Validate action is either approve or reject."""
        if v.lower() not in ['approve', 'reject']:
            raise ValueError('Action must be either "approve" or "reject"')
        return v.lower()

