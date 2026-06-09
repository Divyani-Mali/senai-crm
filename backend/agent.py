import json
from datetime import datetime
from groq import Groq
from config import GROQ_API_KEY, MODEL_NAME
from rag_pipeline import search_knowledge_base

client = Groq(api_key=GROQ_API_KEY)

# ============ AGENT TOOLS ============

def tool_search_knowledge_base(query: str) -> str:
    results = search_knowledge_base(query, k=3)
    output = ""
    for r in results:
        output += f"[{r['source']}] (score={r['similarity_score']})\n{r['content']}\n\n"
    return output or "No results found"

def tool_get_thread_history(db, sender_email: str) -> str:
    from models import Email
    emails = db.query(Email).filter(
        Email.sender == sender_email
    ).order_by(Email.timestamp).all()
    
    if not emails:
        return "No emails found for this sender"
    
    output = f"Thread history for {sender_email} ({len(emails)} emails):\n"
    for e in emails:
        output += f"\n[{e.timestamp}] {e.subject}\n{e.body[:300]}...\n"
    return output

def tool_get_contact_profile(db, email: str) -> str:
    from models import Contact
    contact = db.query(Contact).filter(Contact.email == email).first()
    if not contact:
        return f"No contact profile found for {email}"
    return json.dumps({
        "email": contact.email,
        "name": contact.name,
        "company": contact.company,
        "status": contact.status,
        "account_value": contact.account_value,
        "churn_risk_score": contact.churn_risk_score,
        "last_contact_at": str(contact.last_contact_at)
    }, indent=2)

def tool_check_account_status(db, email: str) -> str:
    from models import Contact, Email
    contact = db.query(Contact).filter(Contact.email == email).first()
    emails = db.query(Email).filter(Email.sender == email).all()
    
    escalated = sum(1 for e in emails if e.status == "Escalated")
    negative = sum(1 for e in emails if e.sentiment_score and e.sentiment_score < -0.5)
    
    return json.dumps({
        "email": email,
        "account_status": contact.status if contact else "Unknown",
        "account_value": contact.account_value if contact else 0,
        "total_emails": len(emails),
        "escalated_emails": escalated,
        "negative_sentiment_emails": negative,
        "churn_risk": contact.churn_risk_score if contact else 0
    }, indent=2)

def tool_escalate_to_human(db, email_id: int, reason: str, priority: str) -> str:
    from models import Email, Action, AuditLog
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        return "Email not found"
    
    email.status = "Escalated"
    email.escalation_reason = reason
    
    action = Action(
        email_id=email_id,
        action_type="Escalate",
        proposed_content=f"Priority: {priority}\nReason: {reason}",
        is_approved=True,
        executed_at=datetime.utcnow()
    )
    db.add(action)
    
    audit = AuditLog(
        entity_type="email",
        entity_id=email_id,
        action="escalated_to_human",
        performed_by="agent",
        timestamp=datetime.utcnow(),
        diff=json.dumps({"reason": reason, "priority": priority})
    )
    db.add(audit)
    db.commit()
    return f"✓ Escalated email {email_id} to human. Priority: {priority}"

def tool_flag_for_legal(db, email_id: int, issue_type: str) -> str:
    from models import Email, Action, AuditLog
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        return "Email not found"
    
    email.status = "Escalated"
    email.category = "Legal"
    
    action = Action(
        email_id=email_id,
        action_type="Legal-Flag",
        proposed_content=f"Issue: {issue_type}\nRoute to: legal@senai.io",
        is_approved=True,
        executed_at=datetime.utcnow()
    )
    db.add(action)
    
    audit = AuditLog(
        entity_type="email",
        entity_id=email_id,
        action="flagged_for_legal",
        performed_by="agent",
        timestamp=datetime.utcnow(),
        diff=json.dumps({"issue_type": issue_type})
    )
    db.add(audit)
    db.commit()
    return f"✓ Flagged email {email_id} for legal team. Issue: {issue_type}"

def tool_create_ticket(db, email_id: int, title: str, body: str, assignee: str) -> str:
    from models import Action, AuditLog
    action = Action(
        email_id=email_id,
        action_type="Ticket-Created",
        proposed_content=f"Title: {title}\nAssignee: {assignee}\n\n{body}",
        is_approved=True,
        executed_at=datetime.utcnow()
    )
    db.add(action)
    
    audit = AuditLog(
        entity_type="email",
        entity_id=email_id,
        action="ticket_created",
        performed_by="agent",
        timestamp=datetime.utcnow(),
        diff=json.dumps({"title": title, "assignee": assignee})
    )
    db.add(audit)
    db.commit()
    return f"✓ Ticket created: '{title}' assigned to {assignee}"

def tool_draft_reply(context: str, tone: str, policy_refs: list) -> str:
    prompt = f"""Draft a professional email reply for SenAI support team.

Context: {context}
Tone: {tone}
Policy references: {', '.join(policy_refs)}

Write a helpful, empathetic reply. Do not admit legal liability. Be concise (max 150 words)."""
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=300
    )
    return response.choices[0].message.content.strip()

# ============ MAIN AGENT ============

def run_agent(db, email_id: int, dry_run: bool = False) -> dict:
    """Main agent loop - ReAct pattern"""
    from models import Email, Action
    
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        return {"error": "Email not found"}

    reasoning_log = []
    tool_calls = 0
    MAX_TOOLS = 6

    def log(thought: str, action: str, observation: str):
        entry = {
            "step": len(reasoning_log) + 1,
            "thought": thought,
            "action": action,
            "observation": observation[:500]
        }
        reasoning_log.append(entry)
        print(f"\n[Step {entry['step']}]")
        print(f"  Thought: {thought}")
        print(f"  Action: {action}")
        print(f"  Observation: {observation[:200]}")

    print(f"\n{'='*50}")
    print(f"AGENT RUNNING for: {email.message_id}")
    print(f"Subject: {email.subject}")
    print(f"Dry run: {dry_run}")
    print(f"{'='*50}")

    # Step 1: Get thread history
    thought = f"I need to understand the full context. Let me get the thread history for {email.sender}"
    action = f"get_thread_history({email.sender})"
    obs = tool_get_thread_history(db, email.sender)
    log(thought, action, obs)
    tool_calls += 1

    # Step 2: Get contact profile
    thought = "Let me check who this person is and their account status"
    action = f"get_contact_profile({email.sender})"
    obs = tool_get_contact_profile(db, email.sender)
    log(thought, action, obs)
    tool_calls += 1

    # Step 3: Search knowledge base based on email content
    thought = f"Let me search for relevant policies for: {email.subject}"
    search_q = f"{email.subject} {email.body[:150]}"
    action = f"search_knowledge_base('{search_q[:80]}')"
    obs = tool_search_knowledge_base(search_q)
    log(thought, action, obs)
    tool_calls += 1

    # Step 4: Decision logic based on category/urgency
    final_action = "none"
    reply_draft = None

    # SECURITY THREAT - never auto reply
    if email.category == "Security" or (email.urgency == "Critical" and "ransomware" in email.body.lower()):
        thought = "This is a security threat. Must escalate immediately. NEVER auto-reply."
        action = "flag_for_legal + escalate_to_human"
        if not dry_run:
            obs1 = tool_flag_for_legal(db, email_id, "Security threat / ransomware")
            obs2 = tool_escalate_to_human(db, email_id, "SECURITY THREAT - ransomware detected", "Critical")
            obs = f"{obs1}\n{obs2}"
        else:
            obs = "[DRY RUN] Would flag for security + escalate"
        log(thought, action, obs)
        final_action = "security_escalated"

    # LEGAL / GDPR
    elif email.category in ["Legal", "Compliance"] and email.urgency in ["Critical", "High"]:
        thought = "This is a legal/compliance issue. Must flag for legal team and create ticket."
        action = "flag_for_legal + create_ticket + escalate_to_human"
        
        # Search compliance docs
        obs_rag = tool_search_knowledge_base("GDPR legal compliance escalation")
        log("Searching compliance policies", "search_knowledge_base('GDPR legal')", obs_rag)
        tool_calls += 1
        
        if not dry_run:
            obs1 = tool_flag_for_legal(db, email_id, "Legal/Compliance - " + email.subject)
            obs2 = tool_create_ticket(db, email_id, f"Compliance: {email.subject}", 
                                      email.body[:500], "compliance@senai.io")
            obs3 = tool_escalate_to_human(db, email_id, 
                                          "Legal/Compliance requires human review", "High")
            obs = f"{obs1}\n{obs2}\n{obs3}"
        else:
            obs = "[DRY RUN] Would flag legal + create compliance ticket + escalate"
        log(thought, action, obs)
        final_action = "legal_escalated"

    # CRITICAL URGENCY - always escalate
    elif email.urgency == "Critical":
        thought = "Critical urgency - must escalate to human, no auto-reply allowed"
        action = f"escalate_to_human({email_id})"
        if not dry_run:
            obs = tool_escalate_to_human(db, email_id, 
                                         f"Critical urgency: {email.category}", "Critical")
        else:
            obs = "[DRY RUN] Would escalate to human"
        log(thought, action, obs)
        final_action = "critical_escalated"

    # COMPLAINT with negative sentiment
    elif email.category == "Complaint" and email.sentiment_score and email.sentiment_score < -0.5:
        thought = "Negative complaint - search retention playbook and draft empathetic reply"
        obs_rag = tool_search_knowledge_base("complaint retention churn refund")
        log(thought, "search_knowledge_base('complaint retention')", obs_rag)
        tool_calls += 1
        
        if tool_calls < MAX_TOOLS:
            context = f"Customer complaint from {email.sender}: {email.body[:300]}"
            thought = "Drafting empathetic reply based on retention playbook"
            action = "draft_reply(empathetic)"
            if not dry_run:
                reply_draft = tool_draft_reply(context, "empathetic", ["refund_policy.md"])
                obs = f"Draft created: {reply_draft[:200]}"
                
                # Save draft
                action_obj = Action(
                    email_id=email_id,
                    action_type="Auto-Reply",
                    proposed_content=reply_draft,
                    is_approved=False
                )
                db.add(action_obj)
                db.commit()
            else:
                obs = "[DRY RUN] Would draft empathetic reply"
            log(thought, action, obs)
            final_action = "draft_created"

    # REQUIRES HUMAN
    elif email.requires_human:
        thought = "Email requires human review based on classification"
        action = f"escalate_to_human({email_id})"
        if not dry_run:
            obs = tool_escalate_to_human(db, email_id,
                                         email.escalation_reason or "Requires human review", "Medium")
        else:
            obs = "[DRY RUN] Would escalate to human"
        log(thought, action, obs)
        final_action = "human_escalated"

    # AUTO-REPLY possible
    elif email.suggested_reply and not email.requires_human:
        thought = "Low risk email - can use suggested reply from classifier"
        action = "use_classifier_suggested_reply"
        reply_draft = email.suggested_reply
        if not dry_run:
            action_obj = Action(
                email_id=email_id,
                action_type="Auto-Reply",
                proposed_content=reply_draft,
                is_approved=False
            )
            db.add(action_obj)
            db.commit()
            obs = f"Draft saved for approval: {reply_draft[:200]}"
        else:
            obs = "[DRY RUN] Would save suggested reply as draft"
        log(thought, action, obs)
        final_action = "draft_created"

    else:
        thought = "No clear action needed - marking for human review"
        action = "escalate_to_human"
        if not dry_run:
            obs = tool_escalate_to_human(db, email_id, "No clear action determined", "Low")
        else:
            obs = "[DRY RUN] Would escalate"
        log(thought, action, obs)
        final_action = "escalated"

    # Save reasoning log
    if not dry_run:
        existing_action = db.query(Action).filter(
            Action.email_id == email_id,
            Action.action_type == "Escalate"
        ).first()
        
        if existing_action:
            existing_action.agent_reasoning_log = json.dumps(reasoning_log)
            db.commit()

    result = {
        "email_id": email_id,
        "message_id": email.message_id,
        "final_action": final_action,
        "steps": len(reasoning_log),
        "tool_calls": tool_calls,
        "reasoning_log": reasoning_log,
        "dry_run": dry_run
    }

    print(f"\n✓ Agent complete: {final_action} ({tool_calls} tool calls)")
    return result


if __name__ == "__main__":
    from database import SessionLocal
    db = SessionLocal()
    
    # Test with bob's escalation email (msg_060)
    from models import Email
    email = db.query(Email).filter(Email.message_id == "msg_060").first()
    if email:
        print("Testing Bob's escalation case...")
        result = run_agent(db, email.id, dry_run=False)
    else:
        print("msg_060 not found, testing with first email...")
        email = db.query(Email).first()
        result = run_agent(db, email.id, dry_run=True)
    
    db.close()