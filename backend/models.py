from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    company = Column(String)
    status = Column(String, default="Active")
    account_value = Column(Float, default=0.0)
    churn_risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_contact_at = Column(DateTime, default=datetime.utcnow)

class Thread(Base):
    __tablename__ = "threads"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, unique=True, index=True)
    subject = Column(String)
    sender_email = Column(String, index=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="Open")
    assigned_to = Column(String, nullable=True)
    
    emails = relationship("Email", back_populates="thread")

class Email(Base):
    __tablename__ = "emails"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, ForeignKey("threads.thread_id"), index=True)
    message_id = Column(String, unique=True, index=True)
    sender = Column(String, index=True)
    subject = Column(String)
    body = Column(Text)
    timestamp = Column(DateTime)
    sentiment_score = Column(Float, nullable=True)
    category = Column(String, nullable=True)
    urgency = Column(String, nullable=True)
    requires_human = Column(Boolean, nullable=True)
    confidence = Column(Float, nullable=True)
    raw_entities = Column(Text, nullable=True)
    status = Column(String, default="Received")
    suggested_reply = Column(Text, nullable=True)
    escalation_reason = Column(Text, nullable=True)
    
    thread = relationship("Thread", back_populates="emails")
    actions = relationship("Action", back_populates="email")

class Action(Base):
    __tablename__ = "actions"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"))
    agent_reasoning_log = Column(Text, nullable=True)
    action_type = Column(String)
    proposed_content = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False)
    approved_by = Column(String, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    
    email = relationship("Email", back_populates="actions")

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String)
    entity_id = Column(Integer)
    action = Column(String)
    performed_by = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    diff = Column(Text, nullable=True)