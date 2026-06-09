import json
import re
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from models import Email, Thread, Contact
from config import URGENCY_KEYWORDS, SPAM_KEYWORDS, SECURITY_KEYWORDS, LEGAL_KEYWORDS, SPAM_DOMAINS

def clean_body(body: str) -> str:
    """Clean email body - remove HTML, extra whitespace"""
    if not body:
        return ""
    # Remove HTML tags
    body = re.sub(r'<[^>]+>', '', body)
    # Remove extra whitespace
    body = re.sub(r'\s+', ' ', body).strip()
    # Truncate if too long
    if len(body) > 10000:
        body = body[:10000] + "... [truncated]"
    return body

def heuristic_filter(email: dict) -> dict:
    """Fast pre-filter - runs in <10ms"""
    body = (email.get("body", "") or "").lower()
    subject = (email.get("subject", "") or "").lower()
    sender = (email.get("sender", "") or "").lower()
    combined = f"{subject} {body}"

    flags = {
        "is_spam": False,
        "is_security": False,
        "is_legal": False,
        "is_internal": False,
        "initial_urgency": "Low",
        "flag_reasons": []
    }

    # Internal email check
    if any(domain in sender for domain in ["@internal.com", "@mycompany.com", "@senai.io"]):
        flags["is_internal"] = True
        flags["flag_reasons"].append("Internal email")
        return flags

    # Spam check
    spam_hits = [kw for kw in SPAM_KEYWORDS if kw in combined]
    if spam_hits:
        flags["is_spam"] = True
        flags["flag_reasons"].append(f"Spam keywords: {spam_hits}")

    # Security check
    security_hits = [kw for kw in SECURITY_KEYWORDS if kw in combined]
    if security_hits:
        flags["is_security"] = True
        flags["initial_urgency"] = "Critical"
        flags["flag_reasons"].append(f"Security keywords: {security_hits}")

    # Legal check
    legal_hits = [kw for kw in LEGAL_KEYWORDS if kw in combined]
    if legal_hits:
        flags["is_legal"] = True
        flags["initial_urgency"] = "Critical"
        flags["flag_reasons"].append(f"Legal keywords: {legal_hits}")

    # Urgency check
    urgency_hits = [kw for kw in URGENCY_KEYWORDS if kw in combined]
    if urgency_hits and not flags["is_security"]:
        flags["initial_urgency"] = "High"
        flags["flag_reasons"].append(f"Urgency keywords: {urgency_hits}")

    return flags

def get_or_create_contact(db: Session, email_addr: str, name: str = None, company: str = None):
    """Get existing contact or create new one"""
    contact = db.query(Contact).filter(Contact.email == email_addr).first()
    if not contact:
        contact = Contact(
            email=email_addr,
            name=name or email_addr.split("@")[0],
            company=company or email_addr.split("@")[-1].split(".")[0],
            status="Active"
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
    return contact

def get_or_create_thread(db: Session, thread_id: str, subject: str, sender_email: str):
    """Get existing thread or create new one"""
    thread = db.query(Thread).filter(Thread.thread_id == thread_id).first()
    if not thread:
        thread = Thread(
            thread_id=thread_id,
            subject=subject,
            sender_email=sender_email,
            first_seen_at=datetime.utcnow(),
            last_updated_at=datetime.utcnow(),
            status="Open"
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)
    else:
        thread.last_updated_at = datetime.utcnow()
        db.commit()
    return thread

def ingest_email(db: Session, email_data: dict) -> dict:
    """Main ingestion function"""

    # Validate required fields
    required = ["message_id", "sender", "subject", "body", "thread_id"]
    missing = [f for f in required if not email_data.get(f)]
    if missing:
        return {"success": False, "error": f"Missing fields: {missing}"}

    # Deduplication check
    existing = db.query(Email).filter(
        Email.message_id == email_data["message_id"]
    ).first()
    if existing:
        return {"success": False, "error": "Duplicate message_id", "email_id": existing.id}

    # Clean body
    email_data["body"] = clean_body(email_data.get("body", ""))

    # Empty body check
    if not email_data["body"].strip():
        email_data["body"] = "[Empty body]"

    # Run heuristic filter
    flags = heuristic_filter(email_data)

    # Parse timestamp
    try:
        ts = datetime.fromisoformat(email_data.get("timestamp", "").replace("Z", "+00:00"))
    except:
        ts = datetime.utcnow()

    # Get or create contact
    get_or_create_contact(
        db,
        email_data["sender"],
        email_data.get("sender_name"),
        email_data.get("company")
    )

    # Get or create thread
    get_or_create_thread(
        db,
        email_data["thread_id"],
        email_data["subject"],
        email_data["sender"]
    )

    # Determine initial status
    if flags["is_spam"]:
        status = "Ignored"
        urgency = "Low"
        category = "Spam"
    elif flags["is_security"]:
        status = "Escalated"
        urgency = "Critical"
        category = "Security"
    elif flags["is_legal"]:
        status = "Escalated"
        urgency = "Critical"
        category = "Legal"
    else:
        status = "Received"
        urgency = flags["initial_urgency"]
        category = None

    # Save email to DB
    email_obj = Email(
        thread_id=email_data["thread_id"],
        message_id=email_data["message_id"],
        sender=email_data["sender"],
        subject=email_data["subject"],
        body=email_data["body"],
        timestamp=ts,
        status=status,
        urgency=urgency,
        category=category
    )
    db.add(email_obj)
    db.commit()
    db.refresh(email_obj)

    return {
        "success": True,
        "email_id": email_obj.id,
        "message_id": email_obj.message_id,
        "status": status,
        "urgency": urgency,
        "flags": flags
    }

def load_json_and_ingest(db: Session, json_path: str = "../email-data-advanced.json"):
    """Load all emails from JSON file and ingest them"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    emails = data if isinstance(data, list) else data.get("emails", [])
    print(f"Found {len(emails)} emails to ingest")

    results = {"success": 0, "duplicate": 0, "error": 0}

    for email in emails:
        result = ingest_email(db, email)
        if result["success"]:
            results["success"] += 1
            print(f"✓ Ingested: {email.get('message_id')} | {result['urgency']} | {result['status']}")
        elif "Duplicate" in result.get("error", ""):
            results["duplicate"] += 1
            print(f"⟳ Duplicate: {email.get('message_id')}")
        else:
            results["error"] += 1
            print(f"✗ Error: {email.get('message_id')} - {result.get('error')}")

    print(f"\nDone! Success: {results['success']} | Duplicates: {results['duplicate']} | Errors: {results['error']}")
    return results

if __name__ == "__main__":
    from database import SessionLocal, create_tables
    create_tables()
    db = SessionLocal()
    load_json_and_ingest(db)
    db.close()