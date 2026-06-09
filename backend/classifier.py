import json
from groq import Groq
from config import GROQ_API_KEY, MODEL_NAME
from rag_pipeline import search_knowledge_base

client = Groq(api_key=GROQ_API_KEY)

def get_thread_context(db, thread_id: str) -> str:
    """Get full thread history as formatted string"""
    from models import Email
    emails = db.query(Email).filter(
        Email.thread_id == thread_id
    ).order_by(Email.timestamp).all()
    
    context = ""
    for e in emails:
        context += f"\n---\nFrom: {e.sender}\nSubject: {e.subject}\nDate: {e.timestamp}\n{e.body}\n"
    return context

def classify_email(db, email_id: int) -> dict:
    """Classify a single email using Groq LLM + RAG context"""
    from models import Email
    
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        return {"error": "Email not found"}

    # Skip spam and already escalated
    if email.status == "Ignored":
        return {"skipped": True, "reason": "Spam/Ignored"}

    # Get thread history
    thread_context = get_thread_context(db, email.thread_id)

    # Get RAG context
    search_query = f"{email.subject} {email.body[:200]}"
    rag_results = search_knowledge_base(search_query, k=3)
    rag_context = ""
    for r in rag_results:
        rag_context += f"\n[{r['source']}]:\n{r['content']}\n"

    # Build prompt
    prompt = f"""You are an AI email triage assistant for SenAI, a B2B SaaS company.

FULL THREAD HISTORY:
{thread_context}

RELEVANT POLICY CONTEXT (from knowledge base):
{rag_context}

LATEST EMAIL TO CLASSIFY:
From: {email.sender}
Subject: {email.subject}
Body: {email.body}

Classify this email and respond ONLY with a valid JSON object (no markdown, no explanation):
{{
  "category": "Complaint|Inquiry|Bug Report|Feature Request|Compliance|Legal|Billing|Spam|Internal|Security|Other",
  "sentiment": "Positive|Neutral|Negative|Mixed",
  "sentiment_score": 0.0,
  "urgency": "Critical|High|Medium|Low",
  "requires_human": true,
  "escalation_reason": "string or null",
  "suggested_reply": "string or null",
  "confidence": 0.0,
  "detected_entities": {{
    "order_ids": [],
    "ticket_ids": [],
    "monetary_amounts": [],
    "deadlines": [],
    "products_mentioned": []
  }},
  "policy_refs": []
}}

Rules:
- sentiment_score: -1.0 (very negative) to +1.0 (very positive)
- confidence: 0.0 to 1.0
- If confidence < 0.70, set requires_human to true
- NEVER suggest auto-reply for: ransomware, legal threats, GDPR requests, security threats
- For GDPR Article 20 requests: category must be "Compliance", requires_human must be true
- escalation_reason: fill if requires_human is true, else null
- suggested_reply: fill if requires_human is false, else null
- policy_refs: list which knowledge base documents informed your decision
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        raw = response.choices[0].message.content.strip()
        
        # Clean JSON
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        
        result = json.loads(raw)
        
        # Update email in DB
        email.category = result.get("category")
        email.sentiment_score = result.get("sentiment_score")
        email.urgency = result.get("urgency")
        email.requires_human = result.get("requires_human")
        email.confidence = result.get("confidence")
        email.suggested_reply = result.get("suggested_reply")
        email.escalation_reason = result.get("escalation_reason")
        email.raw_entities = json.dumps(result.get("detected_entities", {}))
        
        if result.get("requires_human"):
            email.status = "Escalated"
        elif result.get("suggested_reply"):
            email.status = "Processing"
            
        db.commit()
        
        print(f"✓ Classified {email.message_id}: {result.get('category')} | {result.get('urgency')} | sentiment={result.get('sentiment_score')}")
        return result
        
    except json.JSONDecodeError as e:
        print(f"✗ JSON parse error for {email.message_id}: {e}")
        return {"error": f"JSON parse error: {e}", "raw": raw}
    except Exception as e:
        print(f"✗ Error classifying {email.message_id}: {e}")
        return {"error": str(e)}

def classify_all_pending(db):
    """Classify all unclassified emails"""
    from models import Email
    
    pending = db.query(Email).filter(
        Email.category == None,
        Email.status != "Ignored"
    ).all()
    
    print(f"Found {len(pending)} emails to classify...")
    results = {"success": 0, "error": 0, "skipped": 0}
    
    for email in pending:
        result = classify_email(db, email.id)
        if "error" in result:
            results["error"] += 1
        elif "skipped" in result:
            results["skipped"] += 1
        else:
            results["success"] += 1
    
    print(f"\nDone! Success: {results['success']} | Errors: {results['error']} | Skipped: {results['skipped']}")
    return results

if __name__ == "__main__":
    from database import SessionLocal, create_tables
    create_tables()
    db = SessionLocal()
    classify_all_pending(db)
    db.close()