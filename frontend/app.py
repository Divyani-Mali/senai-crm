import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

API = "http://localhost:8000"

st.set_page_config(
    page_title="SenAI CRM",
    page_icon="🧠",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stApp { background-color: #0f172a; }
    div[data-testid="metric-container"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
    }
    .badge-critical { background: #7f1d1d; color: #fca5a5; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
    .badge-high { background: #78350f; color: #fcd34d; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
    .badge-medium { background: #1e3a5f; color: #93c5fd; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
    .badge-low { background: #1e3a2f; color: #6ee7b7; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ============ SIDEBAR ============
st.sidebar.image("https://via.placeholder.com/200x60/1e293b/38bdf8?text=SenAI+CRM", width=200)
st.sidebar.title("Navigation")
page = st.sidebar.radio("Menu", ["📥 Mission Control", "🧵 Thread Workspace", "📊 Analytics", "🔍 RAG Debug", "🤖 Agent Dry Run"], label_visibility="collapsed")

# ============ HELPER FUNCTIONS ============
def get_stats():
    try:
        return requests.get(f"{API}/dashboard/stats").json()
    except:
        return {}

def get_sentiment_trend():
    try:
        return requests.get(f"{API}/analytics/sentiment-trend?days=365").json()
    except:
        return {}
    
def get_all_emails():
    try:
        senders = [
            "alice.smith@greenlight-npo.org",
            "bob.jones@enterprise.net", 
            "karen.w@retail-co.com",
            "eleanor.voss@meditrust.org",
            "marcus.del@fintech-startup.co",
            "nadia.k@logisticspro.com",
            "raj.p@techventures.in",
            "sara.m@cloudbase.io",
            "tom.h@retailgiant.com",
            "lisa.b@startup.io"
        ]
        all_emails = []
        for sender in senders:
            try:
                data = requests.get(f"{API}/threads/{sender}", timeout=2).json()
                emails = data.get("emails", [])
                all_emails.extend(emails)
            except:
                pass
        return all_emails
    except:
        return []

def get_category_breakdown():
    try:
        return requests.get(f"{API}/analytics/category-breakdown").json()
    except:
        return {}

def get_thread(email):
    try:
        return requests.get(f"{API}/threads/{email}").json()
    except:
        return {}

def sentiment_color(score):
    if score is None: return "⚪"
    if score > 0.2: return "🟢"
    if score < -0.2: return "🔴"
    return "🟡"

def urgency_emoji(urgency):
    map = {"Critical": "🚨", "High": "🔴", "Medium": "🟡", "Low": "🟢"}
    return map.get(urgency, "⚪")

# ============ PAGE 1: MISSION CONTROL ============
if page == "📥 Mission Control":
    st.title("🧠 SenAI CRM — Mission Control")

    # Stats
    stats = get_stats()
    if stats:
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("📧 Total", stats.get("total", 0))
        col2.metric("⏳ Pending", stats.get("pending", 0))
        col3.metric("🚨 Escalated", stats.get("escalated", 0))
        col4.metric("🔴 Critical", stats.get("critical", 0))
        col5.metric("✅ Replied", stats.get("replied", 0))
        col6.metric("🗑️ Spam", stats.get("spam", 0))

    st.divider()

    # Filters
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 Search emails", placeholder="Search by sender or subject...")
    with col2:
        filter_urgency = st.selectbox("Urgency", ["All", "Critical", "High", "Medium", "Low"])
    with col3:
        filter_category = st.selectbox("Category", ["All", "Complaint", "Inquiry", "Bug Report", 
                                                      "Billing", "Compliance", "Legal", "Security", "Spam"])

    # Get emails
    trend_data = get_sentiment_trend()
    emails = get_all_emails()

    # Apply filters
    if search:
        emails = [e for e in emails if search.lower() in e.get("sender","").lower() 
                  or search.lower() in e.get("subject","").lower()]
    if filter_urgency != "All":
        emails = [e for e in emails if e.get("urgency") == filter_urgency]
    if filter_category != "All":
        emails = [e for e in emails if e.get("category") == filter_category]

    st.markdown(f"**{len(emails)} emails**")

    #Email table
    if emails:
        for email in emails:
            score = email.get("sentiment_score")
            urgency = email.get("urgency", "Low")
            category = email.get("category", "")
            
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.markdown(f"**{email.get('sender','')}** — {email.get('subject','')[:60]}")
            with col2:
                st.markdown(f"{urgency_emoji(urgency)} `{urgency}`")
            with col3:
                st.markdown(f"`{category}`")
            with col4:
                st.markdown(f"{sentiment_color(score)} `{score}`")
            st.divider()
    else:
        st.info("No emails found")

# ============ PAGE 2: THREAD WORKSPACE ============
elif page == "🧵 Thread Workspace":
    st.title("🧵 Thread Workspace")

    KNOWN_SENDERS = [
        "alice.smith@greenlight-npo.org",
        "bob.jones@enterprise.net",
        "karen.w@retail-co.com",
        "eleanor.voss@meditrust.org",
        "marcus.del@fintech-startup.co",
        "nadia.k@logisticspro.com",
        "raj.p@techventures.in",
        "sara.m@cloudbase.io",
        "tom.h@retailgiant.com",
        "lisa.b@startup.io"
    ]

    sender = st.selectbox("Select sender", KNOWN_SENDERS)

    if sender:
        data = get_thread(sender)
        emails = data.get("emails", [])

        if not emails:
            st.warning("No emails found for this sender")
        else:
            st.success(f"Found {len(emails)} emails in thread")

            # Contact profile
            with st.expander("👤 Contact Profile", expanded=True):
                try:
                    contact = requests.get(f"{API}/contacts/{sender}").json()
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Status", contact.get("status", "Unknown"))
                    col2.metric("Account Value", f"${contact.get('account_value', 0):,.0f}")
                    col3.metric("Churn Risk", f"{contact.get('churn_risk_score', 0):.1%}")
                    col4.metric("Total Emails", contact.get("total_emails", 0))
                except:
                    st.info("Contact profile not available")

            # Thread timeline
            st.markdown("### 📨 Thread Timeline")
            for email in emails:
                score = email.get("sentiment_score")
                emoji = sentiment_color(score)
                urgency = email.get("urgency", "Low")
                urg_emoji = urgency_emoji(urgency)

                with st.expander(f"{emoji} {urg_emoji} [{email.get('timestamp','')[:10]}] {email.get('subject','')}", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**From:** {email.get('sender')}")
                        st.markdown(f"**Status:** `{email.get('status')}`")
                        st.markdown("**Body:**")
                        st.text_area("", email.get("body",""), height=120, 
                                    key=f"body_{email.get('id')}", disabled=True)

                    with col2:
                        st.markdown(f"**Category:** `{email.get('category','?')}`")
                        st.markdown(f"**Urgency:** `{urgency}`")
                        st.markdown(f"**Sentiment:** `{score}`")
                        st.markdown(f"**Confidence:** `{email.get('confidence','?')}`")
                        
                        if email.get("escalation_reason"):
                            st.error(f"⚠️ {email.get('escalation_reason')}")
                        
                        if email.get("suggested_reply"):
                            st.success("💬 Auto-reply available")

                    # Agent reasoning
                    actions = email.get("actions", [])
                    reasoning = []
                    for a in actions:
                        reasoning.extend(a.get("reasoning_log", []))
                    
                    if reasoning:
                        st.markdown("**🤖 Agent Reasoning Trace:**")
                        for step in reasoning:
                            st.markdown(f"""
> **Step {step.get('step')}**  
> 💭 *{step.get('thought','')}*  
> ⚡ `{step.get('action','')}`  
> 👁️ {step.get('observation','')[:200]}
""")

                    # Draft reply
                    draft_action = next((a for a in actions if a.get("action_type") == "Auto-Reply" 
                                        and not a.get("is_approved")), None)
                    if draft_action:
                        st.markdown("**📝 Proposed Reply:**")
                        st.info(draft_action.get("proposed_content",""))
                        
                        col_a, col_b = st.columns(2)
                        if col_a.button("✅ Approve & Send", key=f"approve_{draft_action['id']}"):
                            requests.post(f"{API}/drafts/{draft_action['id']}/approve")
                            st.success("✅ Reply approved and sent!")
                            st.rerun()
                        if col_b.button("🚨 Escalate", key=f"esc_{email.get('id')}"):
                            st.warning("Escalated to human team")

# ============ PAGE 3: ANALYTICS ============
elif page == "📊 Analytics":
    st.title("📊 Analytics Dashboard")

    col1, col2 = st.columns(2)

    # Category breakdown
    with col1:
        st.subheader("Category Breakdown")
        cat_data = get_category_breakdown()
        breakdown = cat_data.get("breakdown", [])
        if breakdown:
            df_cat = pd.DataFrame(breakdown)
            df_cat = df_cat[df_cat["category"].notna()]
            fig = px.pie(df_cat, values="count", names="category",
                        color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                            font_color="#e2e8f0")
            st.plotly_chart(fig, use_container_width=True)

    # Sentiment trend
    with col2:
        st.subheader("Sentiment Trend")
        trend = get_sentiment_trend()
        trend_data = trend.get("trend", [])
        if trend_data:
            df_trend = pd.DataFrame(trend_data)
            if "timestamp" in df_trend.columns and "sentiment_score" in df_trend.columns:
                df_trend["timestamp"] = pd.to_datetime(df_trend["timestamp"])
                fig2 = px.line(df_trend, x="timestamp", y="sentiment_score",
                              color="sender" if "sender" in df_trend.columns else None,
                              title="Sentiment Over Time")
                fig2.add_hline(y=0, line_dash="dash", line_color="gray")
                fig2.add_hline(y=-0.6, line_dash="dot", line_color="red", 
                              annotation_text="Escalation threshold")
                fig2.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                                  font_color="#e2e8f0")
                st.plotly_chart(fig2, use_container_width=True)

    # At-risk accounts
    st.subheader("⚠️ At-Risk Accounts")
    trend_data2 = get_sentiment_trend().get("trend", [])
    if trend_data2:
        df_risk = pd.DataFrame(trend_data2)
        if "sentiment_score" in df_risk.columns:
            at_risk = df_risk[df_risk["sentiment_score"] < -0.5].groupby("sender").agg(
                avg_sentiment=("sentiment_score", "mean"),
                email_count=("sender", "count")
            ).reset_index().sort_values("avg_sentiment")
            
            if not at_risk.empty:
                st.dataframe(at_risk, use_container_width=True)
            else:
                st.success("No at-risk accounts!")

# ============ PAGE 4: RAG DEBUG ============
elif page == "🔍 RAG Debug":
    st.title("🔍 RAG Knowledge Base Debug")
    
    query = st.text_input("Search knowledge base", placeholder="e.g. refund policy after 14 days")
    
    if query:
        results = requests.get(f"{API}/rag/search?q={query}").json()
        chunks = results.get("results", [])
        
        st.markdown(f"**{len(chunks)} chunks retrieved**")
        
        for i, chunk in enumerate(chunks):
            with st.expander(f"📄 [{chunk['source']}] — Score: {chunk['similarity_score']}", expanded=True):
                st.markdown(chunk["content"])

# ============ PAGE 5: AGENT DRY RUN ============
elif page == "🤖 Agent Dry Run":
    st.title("🤖 Agent Dry Run Mode")
    st.info("See what the agent WOULD do — without actually executing")
    
    email_id = st.number_input("Email ID", min_value=1, max_value=100, value=60)
    
    if st.button("▶️ Run Agent (Dry Run)"):
        with st.spinner("Agent thinking..."):
            result = requests.post(f"{API}/agent/dry-run/{email_id}").json()
        
        if "error" in result:
            st.error(result["error"])
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Final Action", result.get("final_action","?"))
            col2.metric("Tool Calls", result.get("tool_calls", 0))
            col3.metric("Steps", result.get("steps", 0))
            
            st.markdown("### 🧠 Reasoning Trace")
            for step in result.get("reasoning_log", []):
                with st.expander(f"Step {step['step']}: {step.get('action','')[:50]}", expanded=True):
                    st.markdown(f"💭 **Thought:** {step.get('thought','')}")
                    st.code(f"⚡ Action: {step.get('action','')}")
                    st.markdown(f"👁️ **Observation:** {step.get('observation','')[:400]}")

# Footer
st.sidebar.divider()
st.sidebar.markdown("**SenAI CRM v1.0**")
st.sidebar.markdown("Built with FastAPI + Groq + ChromaDB")