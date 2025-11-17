"""
Review and Rating models for the Bookora application.

This module contains models for the post-appointment review and rating system,
allowing clients to rate businesses and leave feedback.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Enum as SQLEnum, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from datetime import datetime
import uuid

from app.models.base import BaseModel


class ReviewStatus(str, Enum):
    """Enumeration for review status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class Review(BaseModel):
    """
    Model representing a review from a client about a business.
    
    Reviews are tied to completed appointments and include ratings
    for various aspects of the service.
    """
    __tablename__ = "reviews"
    
    # Relationships
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=False, unique=True, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    
    # Rating (1-5 stars)
    overall_rating = Column(Integer, nullable=False, comment="Overall rating (1-5)")
    service_quality_rating = Column(Integer, nullable=True, comment="Service quality rating (1-5)")
    cleanliness_rating = Column(Integer, nullable=True, comment="Cleanliness rating (1-5)")
    value_rating = Column(Integer, nullable=True, comment="Value for money rating (1-5)")
    punctuality_rating = Column(Integer, nullable=True, comment="Punctuality rating (1-5)")
    
    # Review Content
    title = Column(String(200), nullable=True, comment="Review title/headline")
    comment = Column(Text, nullable=True, comment="Detailed review comment")
    
    # Review Status
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, index=True)
    is_verified = Column(Boolean, default=True, nullable=False, comment="True if from verified appointment")
    
    # Business Response
    business_response = Column(Text, nullable=True, comment="Business owner's response to review")
    business_response_date = Column(DateTime(timezone=True), nullable=True)
    
    # Moderation
    is_visible = Column(Boolean, default=True, nullable=False, comment="Whether review is visible to public")
    flagged_reason = Column(String(500), nullable=True, comment="Reason for flagging/rejection")
    moderated_by = Column(String(200), nullable=True, comment="Admin who moderated")
    moderated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Helpful votes
    helpful_count = Column(Integer, default=0, nullable=False, comment="Number of helpful votes")
    not_helpful_count = Column(Integer, default=0, nullable=False, comment="Number of not helpful votes")
    
    # Add check constraints for ratings
    __table_args__ = (
        CheckConstraint('overall_rating >= 1 AND overall_rating <= 5', name='check_overall_rating_range'),
        CheckConstraint('service_quality_rating IS NULL OR (service_quality_rating >= 1 AND service_quality_rating <= 5)', name='check_service_quality_rating_range'),
        CheckConstraint('cleanliness_rating IS NULL OR (cleanliness_rating >= 1 AND cleanliness_rating <= 5)', name='check_cleanliness_rating_range'),
        CheckConstraint('value_rating IS NULL OR (value_rating >= 1 AND value_rating <= 5)', name='check_value_rating_range'),
        CheckConstraint('punctuality_rating IS NULL OR (punctuality_rating >= 1 AND punctuality_rating <= 5)', name='check_punctuality_rating_range'),
    )
    
    # Relationships
    appointment = relationship("Appointment", foreign_keys=[appointment_id])
    client = relationship("Client", foreign_keys=[client_id])
    business = relationship("Business", foreign_keys=[business_id])
    
    @property
    def average_detailed_rating(self) -> float:
        """Calculate average of detailed ratings (excluding overall)."""
        ratings = [
            r for r in [
                self.service_quality_rating,
                self.cleanliness_rating,
                self.value_rating,
                self.punctuality_rating
            ] if r is not None
        ]
        
        if not ratings:
            return self.overall_rating
        
        return sum(ratings) / len(ratings)
    
    @property
    def helpfulness_score(self) -> float:
        """Calculate helpfulness score (percentage of helpful votes)."""
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0.0
        return (self.helpful_count / total_votes) * 100
    
    def add_business_response(self, response: str):
        """Add business response to the review."""
        self.business_response = response
        self.business_response_date = func.now()
    
    def mark_as_helpful(self):
        """Increment helpful count."""
        self.helpful_count += 1
    
    def mark_as_not_helpful(self):
        """Increment not helpful count."""
        self.not_helpful_count += 1
    
    def flag_review(self, reason: str):
        """Flag review for moderation."""
        self.status = ReviewStatus.FLAGGED
        self.flagged_reason = reason
        self.is_visible = False
    
    def approve_review(self):
        """Approve review after moderation."""
        self.status = ReviewStatus.APPROVED
        self.is_visible = True
        self.moderated_at = func.now()
    
    def reject_review(self, reason: str):
        """Reject review after moderation."""
        self.status = ReviewStatus.REJECTED
        self.is_visible = False
        self.flagged_reason = reason
        self.moderated_at = func.now()
    
    def __repr__(self):
        client_name = self.client.full_name if self.client else "Unknown"
        business_name = self.business.name if self.business else "Unknown"
        return f"<Review(client='{client_name}', business='{business_name}', rating={self.overall_rating})>"


class ReviewHelpfulness(BaseModel):
    """
    Model to track which users found a review helpful.
    
    Prevents duplicate votes and allows tracking of user engagement.
    """
    __tablename__ = "review_helpfulness"
    
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False, index=True)
    user_firebase_uid = Column(String(128), nullable=False, index=True)
    is_helpful = Column(Boolean, nullable=False, comment="True=helpful, False=not helpful")
    
    # Relationships
    review = relationship("Review")
    
    def __repr__(self):
        return f"<ReviewHelpfulness(review_id={self.review_id}, helpful={self.is_helpful})>"

