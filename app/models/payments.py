"""
Payment models for the Bookora application.

This module contains models for managing client payment methods,
payment processing, and transaction history with Stripe integration.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Enum as SQLEnum, DateTime, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from datetime import datetime
import uuid

from app.models.base import BaseModel


class PaymentMethodType(str, Enum):
    """Enumeration for payment method types."""
    CARD = "card"
    BANK_ACCOUNT = "bank_account"
    DIGITAL_WALLET = "digital_wallet"  # Apple Pay, Google Pay, etc.


class PaymentStatus(str, Enum):
    """Enumeration for payment transaction status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELLED = "cancelled"


class PaymentMethod(BaseModel):
    """
    Model representing a client's saved payment method.
    
    Stores tokenized payment information from Stripe for secure
    future transactions without storing sensitive card data.
    """
    __tablename__ = "payment_methods"
    
    # Owner
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    
    # Payment method type
    payment_type = Column(SQLEnum(PaymentMethodType), nullable=False)
    
    # Stripe integration
    stripe_payment_method_id = Column(String(255), nullable=False, unique=True, comment="Stripe PaymentMethod ID")
    stripe_customer_id = Column(String(255), nullable=True, comment="Stripe Customer ID")
    
    # Card details (for display purposes only - never store actual card numbers)
    card_brand = Column(String(50), nullable=True, comment="Card brand (Visa, Mastercard, etc.)")
    card_last_four = Column(String(4), nullable=True, comment="Last 4 digits of card")
    card_exp_month = Column(Integer, nullable=True, comment="Card expiration month")
    card_exp_year = Column(Integer, nullable=True, comment="Card expiration year")
    
    # Bank account details (for display)
    bank_name = Column(String(200), nullable=True, comment="Bank name")
    account_last_four = Column(String(4), nullable=True, comment="Last 4 digits of account")
    
    # Digital wallet
    wallet_type = Column(String(50), nullable=True, comment="Apple Pay, Google Pay, etc.")
    
    # Status
    is_default = Column(Boolean, default=False, nullable=False, comment="Default payment method")
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Billing address
    billing_name = Column(String(200), nullable=True)
    billing_email = Column(String(255), nullable=True)
    billing_phone = Column(String(20), nullable=True)
    billing_address = Column(String(255), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(100), nullable=True)
    billing_postal_code = Column(String(20), nullable=True)
    billing_country = Column(String(100), nullable=True)
    
    # Relationships
    client = relationship("Client", backref="payment_methods")
    transactions = relationship("PaymentTransaction", back_populates="payment_method")
    
    @property
    def display_name(self) -> str:
        """Get a user-friendly display name for the payment method."""
        if self.payment_type == PaymentMethodType.CARD:
            return f"{self.card_brand} ****{self.card_last_four}"
        elif self.payment_type == PaymentMethodType.BANK_ACCOUNT:
            return f"{self.bank_name} ****{self.account_last_four}"
        elif self.payment_type == PaymentMethodType.DIGITAL_WALLET:
            return f"{self.wallet_type}"
        return "Unknown Payment Method"
    
    @property
    def is_expired(self) -> bool:
        """Check if card is expired."""
        if self.payment_type == PaymentMethodType.CARD and self.card_exp_month and self.card_exp_year:
            now = datetime.now()
            if self.card_exp_year < now.year:
                return True
            if self.card_exp_year == now.year and self.card_exp_month < now.month:
                return True
        return False
    
    def __repr__(self):
        return f"<PaymentMethod(client='{self.client.full_name if self.client else 'Unknown'}', type={self.payment_type}, display='{self.display_name}')>"


class PaymentTransaction(BaseModel):
    """
    Model representing a payment transaction.
    
    Tracks all payment attempts, successes, and failures for appointments
    including deposits and full payments.
    """
    __tablename__ = "payment_transactions"
    
    # Relationships
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    payment_method_id = Column(UUID(as_uuid=True), ForeignKey("payment_methods.id"), nullable=True, index=True)
    
    # Transaction details
    amount = Column(DECIMAL(10, 2), nullable=False, comment="Transaction amount")
    currency = Column(String(3), default="USD", nullable=False)
    
    # Transaction type
    is_deposit = Column(Boolean, default=False, nullable=False, comment="True if this is a deposit payment")
    
    # Status
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    
    # Stripe integration
    stripe_payment_intent_id = Column(String(255), nullable=True, unique=True, comment="Stripe PaymentIntent ID")
    stripe_charge_id = Column(String(255), nullable=True, comment="Stripe Charge ID")
    
    # Transaction timestamps
    processed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Refund details
    refund_amount = Column(DECIMAL(10, 2), nullable=True, comment="Amount refunded")
    refund_reason = Column(String(500), nullable=True, comment="Reason for refund")
    stripe_refund_id = Column(String(255), nullable=True, comment="Stripe Refund ID")
    
    # Error handling
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Additional data
    extra_data = Column(JSON, nullable=True, comment="Additional transaction data")
    
    # Fee information (for business accounting)
    platform_fee = Column(DECIMAL(10, 2), nullable=True, comment="Platform fee amount")
    stripe_fee = Column(DECIMAL(10, 2), nullable=True, comment="Stripe processing fee")
    net_amount = Column(DECIMAL(10, 2), nullable=True, comment="Amount after fees")
    
    # Relationships
    appointment = relationship("Appointment", foreign_keys=[appointment_id])
    client = relationship("Client", foreign_keys=[client_id])
    business = relationship("Business", foreign_keys=[business_id])
    payment_method = relationship("PaymentMethod", back_populates="transactions")
    
    def mark_as_succeeded(self, stripe_charge_id: str):
        """Mark transaction as successful."""
        self.status = PaymentStatus.SUCCEEDED
        self.stripe_charge_id = stripe_charge_id
        self.processed_at = func.now()
    
    def mark_as_failed(self, error_code: str, error_message: str):
        """Mark transaction as failed."""
        self.status = PaymentStatus.FAILED
        self.error_code = error_code
        self.error_message = error_message
        self.failed_at = func.now()
    
    def process_refund(self, refund_amount: float, reason: str, stripe_refund_id: str):
        """Process a refund for this transaction."""
        self.refund_amount = refund_amount
        self.refund_reason = reason
        self.stripe_refund_id = stripe_refund_id
        self.refunded_at = func.now()
        
        if refund_amount >= self.amount:
            self.status = PaymentStatus.REFUNDED
        else:
            self.status = PaymentStatus.PARTIALLY_REFUNDED
    
    def __repr__(self):
        return f"<PaymentTransaction(appointment_id={self.appointment_id}, amount=${self.amount}, status={self.status})>"

