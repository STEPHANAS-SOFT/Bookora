"""
Review and Rating API endpoints for the Bookora application.

This module handles post-appointment reviews, ratings, and feedback
from clients about businesses and their services.

Authentication is handled by API key middleware.
Firebase UID is passed as parameter from frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.reviews import Review, ReviewHelpfulness, ReviewStatus
from app.models.appointments import Appointment, AppointmentStatus
from app.models.clients import Client
from app.models.businesses import Business
from app.schemas.reviews import (
    ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse,
    BusinessResponseCreate, ReviewSummary, ReviewHelpfulnessRequest,
    FlagReviewRequest, ModerateReviewRequest
)

router = APIRouter()


# Client Review Endpoints
@router.post("/", response_model=ReviewResponse)
async def create_review(
    review_data: ReviewCreate,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Create a review for a completed appointment.
    Client only - can only review their own appointments.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Verify appointment exists and belongs to client
    appointment = db.query(Appointment).filter(
        Appointment.id == review_data.appointment_id,
        Appointment.client_id == client.id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check if appointment is completed
    if appointment.status != AppointmentStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Can only review completed appointments"
        )
    
    # Check if review already exists
    existing_review = db.query(Review).filter(
        Review.appointment_id == review_data.appointment_id
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="Review already exists for this appointment"
        )
    
    # Create review
    review = Review(
        appointment_id=review_data.appointment_id,
        client_id=client.id,
        business_id=appointment.business_id,
        overall_rating=review_data.overall_rating,
        service_quality_rating=review_data.service_quality_rating,
        cleanliness_rating=review_data.cleanliness_rating,
        value_rating=review_data.value_rating,
        punctuality_rating=review_data.punctuality_rating,
        title=review_data.title,
        comment=review_data.comment,
        is_verified=True,
        status=ReviewStatus.APPROVED  # Auto-approve verified reviews
    )
    
    db.add(review)
    
    # Update business rating
    business = appointment.business
    business.total_reviews += 1
    
    # Calculate new average rating
    all_reviews = db.query(func.avg(Review.overall_rating)).filter(
        Review.business_id == business.id,
        Review.status == ReviewStatus.APPROVED
    ).scalar()
    
    business.average_rating = float(all_reviews) if all_reviews else review_data.overall_rating
    
    db.commit()
    db.refresh(review)
    
    return review


@router.get("/my-reviews", response_model=ReviewListResponse)
async def get_my_reviews(
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all reviews written by the current client.
    Client only.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Get reviews
    query = db.query(Review).filter(Review.client_id == client.id)
    
    total = query.count()
    
    reviews = (
        query.order_by(desc(Review.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return ReviewListResponse(
        reviews=reviews,
        total=total,
        skip=skip,
        limit=limit
    )


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: uuid.UUID,
    review_update: ReviewUpdate,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Update a review (within allowed time period).
    Client only - can only update their own reviews.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Get review
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.client_id == client.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Update fields
    update_data = review_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)
    
    review.updated_at = datetime.utcnow()
    
    # Recalculate business average rating
    business = review.business
    all_reviews = db.query(func.avg(Review.overall_rating)).filter(
        Review.business_id == business.id,
        Review.status == ReviewStatus.APPROVED
    ).scalar()
    
    business.average_rating = float(all_reviews) if all_reviews else 0.0
    
    db.commit()
    db.refresh(review)
    
    return review


@router.delete("/{review_id}")
async def delete_review(
    review_id: uuid.UUID,
    firebase_uid: str = Query(..., description="Client Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Delete a review.
    Client only - can only delete their own reviews.
    """
    # Verify client exists
    client = db.query(Client).filter(Client.firebase_uid == firebase_uid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Get review
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.client_id == client.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    business_id = review.business_id
    
    # Delete review
    db.delete(review)
    
    # Update business rating
    business = db.query(Business).filter(Business.id == business_id).first()
    if business:
        business.total_reviews = max(0, business.total_reviews - 1)
        
        # Recalculate average rating
        all_reviews = db.query(func.avg(Review.overall_rating)).filter(
            Review.business_id == business_id,
            Review.status == ReviewStatus.APPROVED
        ).scalar()
        
        business.average_rating = float(all_reviews) if all_reviews else 0.0
    
    db.commit()
    
    return {"message": "Review deleted successfully"}


# Business Review Endpoints
@router.get("/business/{business_id}", response_model=ReviewListResponse)
async def get_business_reviews(
    business_id: uuid.UUID,
    min_rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by minimum rating"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all reviews for a specific business.
    Public endpoint - shows only approved reviews.
    """
    # Build query
    query = db.query(Review).filter(
        Review.business_id == business_id,
        Review.status == ReviewStatus.APPROVED,
        Review.is_visible == True
    )
    
    # Apply rating filter
    if min_rating:
        query = query.filter(Review.overall_rating >= min_rating)
    
    # Get total count
    total = query.count()
    
    # Get reviews
    reviews = (
        query.order_by(desc(Review.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Calculate average rating
    avg_rating = db.query(func.avg(Review.overall_rating)).filter(
        Review.business_id == business_id,
        Review.status == ReviewStatus.APPROVED
    ).scalar()
    
    return ReviewListResponse(
        reviews=reviews,
        total=total,
        skip=skip,
        limit=limit,
        average_rating=float(avg_rating) if avg_rating else None
    )


@router.get("/business/{business_id}/summary", response_model=ReviewSummary)
async def get_business_review_summary(
    business_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get review summary statistics for a business.
    Public endpoint.
    """
    # Get all approved reviews for the business
    reviews = db.query(Review).filter(
        Review.business_id == business_id,
        Review.status == ReviewStatus.APPROVED
    ).all()
    
    if not reviews:
        return ReviewSummary(
            total_reviews=0,
            average_overall_rating=0.0,
            average_service_quality=0.0,
            average_cleanliness=0.0,
            average_value=0.0,
            average_punctuality=0.0,
            five_star_count=0,
            four_star_count=0,
            three_star_count=0,
            two_star_count=0,
            one_star_count=0
        )
    
    # Calculate averages
    overall_ratings = [r.overall_rating for r in reviews]
    service_ratings = [r.service_quality_rating for r in reviews if r.service_quality_rating]
    cleanliness_ratings = [r.cleanliness_rating for r in reviews if r.cleanliness_rating]
    value_ratings = [r.value_rating for r in reviews if r.value_rating]
    punctuality_ratings = [r.punctuality_rating for r in reviews if r.punctuality_rating]
    
    # Count rating distribution
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for rating in overall_ratings:
        rating_counts[rating] += 1
    
    return ReviewSummary(
        total_reviews=len(reviews),
        average_overall_rating=sum(overall_ratings) / len(overall_ratings),
        average_service_quality=sum(service_ratings) / len(service_ratings) if service_ratings else 0.0,
        average_cleanliness=sum(cleanliness_ratings) / len(cleanliness_ratings) if cleanliness_ratings else 0.0,
        average_value=sum(value_ratings) / len(value_ratings) if value_ratings else 0.0,
        average_punctuality=sum(punctuality_ratings) / len(punctuality_ratings) if punctuality_ratings else 0.0,
        five_star_count=rating_counts[5],
        four_star_count=rating_counts[4],
        three_star_count=rating_counts[3],
        two_star_count=rating_counts[2],
        one_star_count=rating_counts[1]
    )


@router.post("/{review_id}/response", response_model=ReviewResponse)
async def add_business_response(
    review_id: uuid.UUID,
    response_data: BusinessResponseCreate,
    firebase_uid: str = Query(..., description="Business Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Add a business response to a review.
    Business owner only - can only respond to their own business reviews.
    """
    # Verify business exists
    business = db.query(Business).filter(Business.firebase_uid == firebase_uid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get review
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.business_id == business.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Add business response
    review.add_business_response(response_data.business_response)
    review.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(review)
    
    return review


# Review Helpfulness
@router.post("/{review_id}/helpful", response_model=dict)
async def mark_review_helpful(
    review_id: uuid.UUID,
    helpfulness_data: ReviewHelpfulnessRequest,
    firebase_uid: str = Query(..., description="User Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Mark a review as helpful or not helpful.
    Any authenticated user can vote.
    """
    # Check if review exists
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Check if user already voted
    existing_vote = db.query(ReviewHelpfulness).filter(
        ReviewHelpfulness.review_id == review_id,
        ReviewHelpfulness.user_firebase_uid == firebase_uid
    ).first()
    
    if existing_vote:
        # Update existing vote
        if existing_vote.is_helpful != helpfulness_data.is_helpful:
            # Update counts
            if existing_vote.is_helpful:
                review.helpful_count = max(0, review.helpful_count - 1)
                review.not_helpful_count += 1
            else:
                review.not_helpful_count = max(0, review.not_helpful_count - 1)
                review.helpful_count += 1
            
            existing_vote.is_helpful = helpfulness_data.is_helpful
    else:
        # Create new vote
        vote = ReviewHelpfulness(
            review_id=review_id,
            user_firebase_uid=firebase_uid,
            is_helpful=helpfulness_data.is_helpful
        )
        db.add(vote)
        
        # Update counts
        if helpfulness_data.is_helpful:
            review.helpful_count += 1
        else:
            review.not_helpful_count += 1
    
    db.commit()
    
    return {
        "message": "Vote recorded successfully",
        "helpful_count": review.helpful_count,
        "not_helpful_count": review.not_helpful_count
    }


@router.post("/{review_id}/flag", response_model=dict)
async def flag_review(
    review_id: uuid.UUID,
    flag_data: FlagReviewRequest,
    firebase_uid: str = Query(..., description="User Firebase UID from frontend"),
    db: Session = Depends(get_db)
):
    """
    Flag a review for moderation.
    Any authenticated user can flag inappropriate reviews.
    """
    # Check if review exists
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Flag the review
    review.flag_review(flag_data.reason)
    review.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Review flagged for moderation"}


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific review by ID.
    Public endpoint.
    """
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.is_visible == True
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    return review

