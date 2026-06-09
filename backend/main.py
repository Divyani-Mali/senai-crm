from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
from database import get_db, create_tables
from models import Email, Thread, Contact, Action, AuditLog
from ingestion import ingest_email
from classifier import classify_email
from agent import run_agent
from rag_pipeline import search_knowledge_base

app = FastAPI(title="SenAI CRM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

create_tables()

# ============ SCHEMAS ============

class EmailIngest(BaseModel):
    message_id: str
    sender: str
    subject: str
    body: str
    thread_id: str
    timestamp: Optional[str] = None
    sender_name: Optional[str] = None
    company: Optional[str] = None

class ContactStatusUpdate(BaseModel):
    status: str

class DraftEdit(BaseModel):
    proposed_content: str

# ============ ENDPOINTS ============

@app.post("/api/ingest")
def ingest(email: EmailIngest, db: Session = Depends(get_db)):
    result = ingest_email(db, email.dict())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result)
    
    # Auto classify after ingest
    email_obj = db.query(Email).filter(
        Email.message_id == email.message_id
    ).first()
    if email_obj and email_obj.status not in ["Ignored", "Escalated"]:
        classify_email(db, email_obj.id)
        run_agent(db, email_obj.id)
    
    return {"success": True, "email_id": result["email_id"], "status": result["status"]}

@app.get("/api/status/{message_id}")
def get_status(message_id: str, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.message_id == message_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return {
        "message_id": email.message_id,
        "status": email.status,
        "category": email.category,
        "urgency": email.urgency,
        "sentiment_score": email.sentiment_score
    }

@app.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(Email).count()
    pending = db.query(Email).filter(Email.status == "Received").count()
    escalated = db.query(Email).filter(Email.status == "Escalated").count()
    replied = db.query(Email).filter(Email.status == "Replied").count()
    spam = db.query(Email).filter(Email.category == "Spam").count()
    critical = db.query(Email).filter(Email.urgency == "Critical").count()
    processing = db.query(Email).filter(Email.status == "Processing").count()
    
    return {
        "total": total,
        "pending": pending,
        "escalated": escalated,
        "replied": replied,
        "spam": spam,
        "critical": critical,
        "processing": processing
    }

@app.get("/threads/{contact_email}")
def get_thread(contact_email: str, db: Session = Depends(get_db)):
    emails = db.query(Email).filter(
        Email.sender == contact_email
    ).order_by(Email.timestamp).all()
    
    if not emails:
        raise HTTPException(status_code=404, detail="No emails found")
    
    result = []
    for e in emails:
        actions = db.query(Action).filter(Action.email_id == e.id).all()
        result.append({
            "id": e.id,
            "message_id": e.message_id,
            "subject": e.subject,
            "body": e.body,
            "timestamp": str(e.timestamp),
            "status": e.status,
            "category": e.category,
            "urgency": e.urgency,
            "sentiment_score": e.sentiment_score,
            "requires_human": e.requires_human,
            "confidence": e.confidence,
            "suggested_reply": e.suggested_reply,
            "escalation_reason": e.escalation_reason,
            "entities": json.loads(e.raw_entities) if e.raw_entities else {},
            "actions": [{
                "id": a.id,
                "action_type": a.action_type,
                "proposed_content": a.proposed_content,
                "is_approved": a.is_approved,
                "reasoning_log": json.loads(a.agent_reasoning_log) if a.agent_reasoning_log else []
            } for a in actions]
        })
    return {"sender": contact_email, "email_count": len(result), "emails": result}

@app.post("/respond/{email_id}")
def respond(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    email.status = "Replied"
    db.commit()
    return {"success": True, "message": f"Email {email_id} marked as replied"}

@app.patch("/drafts/{action_id}")
def edit_draft(action_id: int, edit: DraftEdit, db: Session = Depends(get_db)):
    action = db.query(Action).filter(Action.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Draft not found")
    action.proposed_content = edit.proposed_content
    db.commit()
    return {"success": True, "draft_id": action_id}

@app.post("/drafts/{action_id}/approve")
def approve_draft(action_id: int, db: Session = Depends(get_db)):
    from datetime import datetime
    action = db.query(Action).filter(Action.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    action.is_approved = True
    action.approved_by = "human"
    action.executed_at = datetime.utcnow()
    
    email = db.query(Email).filter(Email.id == action.email_id).first()
    if email:
        email.status = "Replied"
    
    audit = AuditLog(
        entity_type="action",
        entity_id=action_id,
        action="draft_approved",
        performed_by="human",
        diff=json.dumps({"action_id": action_id})
    )
    db.add(audit)
    db.commit()
    return {"success": True, "message": "Draft approved and sent"}

@app.get("/analytics/sentiment-trend")
def sentiment_trend(sender: Optional[str] = None, days: int = 30, db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Email).filter(
        Email.timestamp >= since,
        Email.sentiment_score != None
    )
    if sender:
        query = query.filter(Email.sender == sender)
    
    emails = query.order_by(Email.timestamp).all()
    
    data = [{
        "timestamp": str(e.timestamp),
        "sender": e.sender,
        "sentiment_score": e.sentiment_score,
        "subject": e.subject
    } for e in emails]
    
    avg = sum(e.sentiment_score for e in emails) / len(emails) if emails else 0
    
    return {
        "sender": sender or "all",
        "days": days,
        "average_sentiment": round(avg, 3),
        "data_points": len(data),
        "trend": data
    }

@app.get("/analytics/category-breakdown")
def category_breakdown(db: Session = Depends(get_db)):
    from sqlalchemy import func
    results = db.query(
        Email.category, func.count(Email.id)
    ).group_by(Email.category).all()
    
    return {"breakdown": [{"category": r[0] or "Unclassified", "count": r[1]} for r in results]}

@app.get("/rag/search")
def rag_search(q: str, db: Session = Depends(get_db)):
    results = search_knowledge_base(q, k=3)
    return {"query": q, "results": results}

@app.get("/contacts/{email}")
def get_contact(email: str, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.email == email).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    threads = db.query(Thread).filter(Thread.sender_email == email).all()
    emails = db.query(Email).filter(Email.sender == email).all()
    negative = sum(1 for e in emails if e.sentiment_score and e.sentiment_score < -0.5)
    
    return {
        "email": contact.email,
        "name": contact.name,
        "company": contact.company,
        "status": contact.status,
        "account_value": contact.account_value,
        "churn_risk_score": contact.churn_risk_score,
        "total_emails": len(emails),
        "negative_emails": negative,
        "open_threads": sum(1 for t in threads if t.status == "Open")
    }

@app.patch("/contacts/{email}/status")
def update_contact_status(email: str, update: ContactStatusUpdate, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.email == email).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact.status = update.status
    db.commit()
    return {"success": True, "email": email, "new_status": update.status}

@app.post("/agent/dry-run/{email_id}")
def agent_dry_run(email_id: int, db: Session = Depends(get_db)):
    result = run_agent(db, email_id, dry_run=True)
    return result

@app.get("/audit/{entity_type}/{entity_id}")
def get_audit(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).filter(
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id
    ).order_by(AuditLog.timestamp).all()
    
    return {"logs": [{
        "id": l.id,
        "action": l.action,
        "performed_by": l.performed_by,
        "timestamp": str(l.timestamp),
        "diff": json.loads(l.diff) if l.diff else {}
    } for l in logs]}

@app.get("/intelligence/reputation")
def get_reputation():
    return {
        "source": "mock_data",
        "g2_rating": 4.2,
        "trustpilot_rating": 4.0,
        "recent_reviews": 127,
        "common_complaints": ["slow support", "pricing", "api limits"],
        "sentiment": "Mixed",
        "last_updated": "2026-06-09"
    }