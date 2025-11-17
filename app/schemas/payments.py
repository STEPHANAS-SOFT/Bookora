"""
Pydantic schemas for payment API endpoints.

This module contains request and response schemas for managing
payment methods, transactions, and Stripe integration.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import uuid

from app.models.payments import PaymentMethodType, PaymentStatus


class PaymentMethodCreate(BaseModel):
    """Schema for adding a new payment method."""
    payment_type: PaymentMethodType
    stripe_payment_method_id: str = Field(..., description="Stripe PaymentMethod ID")
    stripe_customer_id: Optional[str] = None
    
    # Card details (for display - never store actual numbers)
    card_brand: Optional[str] = Field(None, max_length=50)
    card_last_four: Optional[str] = Field(None, max_length=4, min_length=4)
    card_exp_month: Optional[int] = Field(None, ge=1, le=12)
    card_exp_year: Optional[int] = Field(None, ge=2024)
    
    # Bank account details (for display)
    bank_name: Optional[str] = Field(None, max_length=200)
    account_last_four: Optional[str] = Field(None, max_length=4, min_length=4)
    
    # Digital wallet
    wallet_type: Optional[str] = Field(None, max_length=50)
    
    # Billing address
    billing_name: Optional[str] = Field(None, max_length=200)
    billing_email: Optional[str] = Field(None, max_length=255)
    billing_phone: Optional[str] = Field(None, max_length=20)
    billing_address: Optional[str] = Field(None, max_length=255)
    billing_city: Optional[str] = Field(None, max_length=100)
    billing_state: Optional[str] = Field(None, max_length=100)
    billing_postal_code: Optional[str] = Field(None, max_length=20)
    billing_country: Optional[str] = Field(None, max_length=100)
    
    is_default: bool = False


class PaymentMethodUpdate(BaseModel):
    """Schema for updating payment method."""
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    
    # Billing address updates
    billing_name: Optional[str] = Field(None, max_length=200)
    billing_email: Optional[str] = Field(None, max_length=255)
    billing_phone: Optional[str] = Field(None, max_length=20)
    billing_address: Optional[str] = Field(None, max_length=255)
    billing_city: Optional[str] = Field(None, max_length=100)
    billing_state: Optional[str] = Field(None, max_length=100)
    billing_postal_code: Optional[str] = Field(None, max_length=20)
    billing_country: Optional[str] = Field(None, max_length=100)


class PaymentMethodResponse(BaseModel):
    """Response schema for payment method data."""
    id: uuid.UUID
    client_id: uuid.UUID
    
    # Payment method type
    payment_type: PaymentMethodType
    
    # Stripe integration
    stripe_payment_method_id: str
    stripe_customer_id: Optional[str]
    
    # Card details (display only)
    card_brand: Optional[str]
    card_last_four: Optional[str]
    card_exp_month: Optional[int]
    card_exp_year: Optional[int]
    
    # Bank account details (display)
    bank_name: Optional[str]
    account_last_four: Optional[str]
    
    # Digital wallet
    wallet_type: Optional[str]
    
    # Display name
    display_name: str
    is_expired: bool
    
    # Status
    is_default: bool
    is_active: bool
    is_verified: bool
    
    # Billing address
    billing_name: Optional[str]
    billing_email: Optional[str]
    billing_phone: Optional[str]
    billing_address: Optional[str]
    billing_city: Optional[str]
    billing_state: Optional[str]
    billing_postal_code: Optional[str]
    billing_country: Optional[str]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class PaymentTransactionCreate(BaseModel):
    """Schema for creating a payment transaction."""
    appointment_id: uuid.UUID
    payment_method_id: Optional[uuid.UUID] = None
    
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    is_deposit: bool = False
    
    # Stripe payment intent ID (if already created)
    stripe_payment_intent_id: Optional[str] = None
    
    # Additional data
    extra_data: Optional[Dict[str, Any]] = None


class PaymentTransactionResponse(BaseModel):
    """Response schema for payment transaction."""
    id: uuid.UUID
    
    # Relationships
    appointment_id: uuid.UUID
    client_id: uuid.UUID
    business_id: uuid.UUID
    payment_method_id: Optional[uuid.UUID]
    
    # Transaction details
    amount: Decimal
    currency: str
    is_deposit: bool
    
    # Status
    status: PaymentStatus
    
    # Stripe integration
    stripe_payment_intent_id: Optional[str]
    stripe_charge_id: Optional[str]
    
    # Timestamps
    processed_at: Optional[datetime]
    failed_at: Optional[datetime]
    refunded_at: Optional[datetime]
    
    # Refund details
    refund_amount: Optional[Decimal]
    refund_reason: Optional[str]
    stripe_refund_id: Optional[str]
    
    # Error handling
    error_code: Optional[str]
    error_message: Optional[str]
    
    # Fee information
    platform_fee: Optional[Decimal]
    stripe_fee: Optional[Decimal]
    net_amount: Optional[Decimal]
    
    # Additional data
    extra_data: Optional[Dict[str, Any]]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class RefundRequest(BaseModel):
    """Schema for requesting a refund."""
    refund_amount: Decimal = Field(..., ge=0, decimal_places=2)
    reason: str = Field(..., min_length=1, max_length=500)


class PaymentIntentCreate(BaseModel):
    """Schema for creating a Stripe payment intent."""
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    payment_method_id: str
    appointment_id: uuid.UUID


class PaymentIntentResponse(BaseModel):
    """Response schema for Stripe payment intent."""
    payment_intent_id: str
    client_secret: str
    status: str
    amount: Decimal
    currency: str


class PaymentMethodListResponse(BaseModel):
    """Response schema for paginated payment method list."""
    payment_methods: List[PaymentMethodResponse]
    total: int


class TransactionListResponse(BaseModel):
    """Response schema for paginated transaction list."""
    transactions: List[PaymentTransactionResponse]
    total: int
    skip: int
    limit: int

