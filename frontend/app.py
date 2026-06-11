import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import json

API = "http://localhost:8000"

st.set_page_config(
    page_title="SenAI CRM",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Base */
    .stApp { background-color: #0a0f1e; }
    section[data-testid="stSidebar"] { background-color: #0d1526; border-right: 1px solid #1e3a5f; }

    /* Metrics */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #0d1f3c, #1a2d4f);
        border: 1px solid #1e3a5f;
        border-radius: 12px;
        padding: 16px 20px;
        transition: border-color 0.2s;
    }
    div[data-testid="metric-container"]:hover { border-color: #38bdf8; }
    div[data-testid="metric-container"] label { color: #64748b !important; font-size: 12px !important; text-transform: uppercase; letter-spacing: 1px; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #e2e8f0 !important; font-size: 32px !important; font-weight: 700 !important; }

    /* Email cards */
    .email-card {
        background: #0d1526;
        border: 1px solid #1e3a5f;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
        transition: border-color 0.2s, background 0.2s;
    }
    .email-card:hover { border-color: #38bdf8; background: #111f38; }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        margin-right: 4px;
    }
    .badge-critical { background: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; }
    .badge-high     { background: #431407; color: #fed7aa; border: 1px solid #7c2d12; }
    .badge-medium   { background: #0c1a2e; color: #93c5fd; border: 1px solid #1e3a5f; }
    .badge-low      { background: #052e16; color: #86efac; border: 1px solid #14532d; }
    .badge-complaint   { background: #2e1065; color: #c4b5fd; }
    .badge-inquiry     { background: #0c1a2e; color: #67e8f9; }
    .badge-legal       { background: #450a0a; color: #fca5a5; }
    .badge-billing     { background: #052e16; color: #86efac; }
    .badge-bug         { background: #431407; color: #fdba74; }
    .badge-spam        { background: #1c1917; color: #a8a29e; }
    .badge-security    { background: #450a0a; color: #fca5a5; }
    .badge-compliance  { background: #1e1b4b; color: #a5b4fc; }
    .badge-other       { background: #1e293b; color: #94a3b8; }

    /* Section headers */
    .section-header {
        font-size: 11px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin: 24px 0 12px 0;
    }

    /* Reasoning step */
    .reasoning-step {
        background: #050d1a;
        border-left: 3px solid #38bdf8;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .reasoning-thought { color: #94a3b8; font-size: 13px; font-style: italic; }
    .reasoning-action  { color: #fbbf24; font-size: 13px; font-family: monospace; margin-top: 4px; }
    .reasoning-obs     { color: #34d399; font-size: 13px; margin-top: 4px; }

    /* Divider */
    hr { border-color: #1e3a5f; margin: 8px 0; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: #0a0f1e; }
    ::-webkit-scrollbar-thumb { background: #1e3a5f; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #38bdf8; }

    /* Plotly chart background fix */
    .js-plotly-plot { border-radius: 10px; }

    /* Streamlit overrides */
    .stMarkdown p { color: #cbd5e1; }
    .stTextInput input { background: #0d1526 !important; border-color: #1e3a5f !important; color: #e2e8f0 !important; }
    .stSelectbox div[data-baseweb="select"] { background: #0d1526 !important; border-color: #1e3a5f !important; }
    .stExpander { background: #0d1526 !important; border-color: #1e3a5f !important; border-radius: 10px !important; }
    .stButton button { background: #1e3a5f; color: #e2e8f0; border: 1px solid #38bdf8; border-radius: 8px; }
    .stButton button:hover { background: #38bdf8; color: #0a0f1e; }
    .stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────
st.sidebar.markdown("""
<div style='text-align:center; padding: 16px 0 8px 0;'>
    <span style='font-size:32px;'>🧠</span>
    <div style='font-size:20px; font-weight:700; color:#38bdf8; letter-spacing:1px; margin-top:4px;'>SenAI CRM</div>
    <div style='font-size:11px; color:#64748b; letter-spacing:2px; text-transform:uppercase;'>Intelligence Platform</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.divider()

page = st.sidebar.radio(
    "Menu",
    ["📥 Mission Control", "🧵 Thread Workspace", "📊 Analytics", "🔍 RAG Debug", "🤖 Agent Dry Run"],
    label_visibility="collapsed"
)

st.sidebar.divider()
st.sidebar.markdown("<div style='font-size:11px; color:#64748b;'>v1.0 · FastAPI · Groq · ChromaDB</div>", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────
SENDERS = [
    "alice.smith@greenlight-npo.org",
    "bob.jones@enterprise.net",
    "karen.w@retail-co.com",
    "eleanor.voss@meditrust.org",
    "marcus.del@fintech-startup.co",
    "nadia.k@logisticspro.com",
    "raj.p@techventures.in",
    "sara.m@cloudbase.io",
    "tom.h@retailgiant.com",
    "lisa.b@startup.io",
]

def api(path, method="get", **kw):
    try:
        fn = getattr(requests, method)
        r = fn(f"{API}{path}", timeout=5, **kw)
        return r.json()
    except:
        return {}

def all_emails():
    out = []
    for s in SENDERS:
        d = api(f"/threads/{s}")
        out.extend(d.get("emails", []))
    return out

def sentiment_dot(score):
    if score is None: return "⚪"
    if score > 0.2:   return "🟢"
    if score < -0.2:  return "🔴"
    return "🟡"

def urgency_icon(u):
    return {"Critical":"🚨","High":"🔴","Medium":"🟡","Low":"🟢"}.get(u,"⚪")

def badge(label, kind=None):
    if not label: return ""
    cls = kind or label.lower().replace(" ","").replace("report","")
    return f'<span class="badge badge-{cls}">{label}</span>'

# ── PAGE 1 : MISSION CONTROL ──────────────────────────────────
if page == "📥 Mission Control":

    st.markdown("<h2 style='color:#e2e8f0; margin-bottom:4px;'>📥 Mission Control</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748b; font-size:13px; margin-bottom:20px;'>Real-time email triage · AI-classified · Agent-processed</div>", unsafe_allow_html=True)

    stats = api("/dashboard/stats")
    if stats:
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("📧 Total",     stats.get("total",0))
        c2.metric("⏳ Pending",   stats.get("pending",0))
        c3.metric("🚨 Escalated", stats.get("escalated",0))
        c4.metric("🔴 Critical",  stats.get("critical",0))
        c5.metric("✅ Replied",   stats.get("replied",0))
        c6.metric("🗑️ Spam",      stats.get("spam",0))

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # Filters row
    fc1, fc2, fc3, fc4 = st.columns([3,1,1,1])
    with fc1:
        search = st.text_input("", placeholder="🔍  Search by sender or subject…", label_visibility="collapsed")
    with fc2:
        f_urg = st.selectbox("Urgency", ["All","Critical","High","Medium","Low"], label_visibility="collapsed")
    with fc3:
        f_cat = st.selectbox("Category", ["All","Complaint","Inquiry","Bug Report","Billing","Compliance","Legal","Security","Spam","Other"], label_visibility="collapsed")
    with fc4:
        f_status = st.selectbox("Status", ["All","Received","Escalated","Processing","Ignored"], label_visibility="collapsed")

    with st.spinner("Loading emails…"):
        emails = all_emails()

    # Apply filters
    if search:
        q = search.lower()
        emails = [e for e in emails if q in e.get("sender","").lower() or q in e.get("subject","").lower()]
    if f_urg != "All":
        emails = [e for e in emails if e.get("urgency") == f_urg]
    if f_cat != "All":
        emails = [e for e in emails if e.get("category") == f_cat]
    if f_status != "All":
        emails = [e for e in emails if e.get("status") == f_status]

    st.markdown(f"<div class='section-header'>{len(emails)} emails</div>", unsafe_allow_html=True)

    if not emails:
        st.info("No emails match the current filters.")
    else:
        # Header row
        hc1,hc2,hc3,hc4,hc5 = st.columns([3,2,1,1,1])
        hc1.markdown("<span style='color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>From / Subject</span>", unsafe_allow_html=True)
        hc2.markdown("<span style='color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Category</span>", unsafe_allow_html=True)
        hc3.markdown("<span style='color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Urgency</span>", unsafe_allow_html=True)
        hc4.markdown("<span style='color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Sentiment</span>", unsafe_allow_html=True)
        hc5.markdown("<span style='color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Status</span>", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

        for e in emails:
            score   = e.get("sentiment_score")
            urgency = e.get("urgency","Low")
            cat     = e.get("category","")
            status  = e.get("status","")
            cat_cls = cat.lower().replace(" ","").replace("report","") if cat else "other"

            ec1,ec2,ec3,ec4,ec5 = st.columns([3,2,1,1,1])
            with ec1:
                st.markdown(f"<div style='font-weight:600;color:#e2e8f0;font-size:13px;'>{e.get('sender','')}</div>"
                            f"<div style='color:#64748b;font-size:12px;'>{e.get('subject','')[:55]}{'…' if len(e.get('subject',''))>55 else ''}</div>",
                            unsafe_allow_html=True)
            with ec2:
                st.markdown(badge(cat, cat_cls), unsafe_allow_html=True)
            with ec3:
                st.markdown(f"{urgency_icon(urgency)} <span style='font-size:12px;color:#94a3b8;'>{urgency}</span>", unsafe_allow_html=True)
            with ec4:
                s_val = f"{score:.1f}" if score is not None else "—"
                color = "#34d399" if score and score>0.2 else ("#f87171" if score and score<-0.2 else "#94a3b8")
                st.markdown(f"{sentiment_dot(score)} <span style='font-size:12px;color:{color};'>{s_val}</span>", unsafe_allow_html=True)
            with ec5:
                st_color = {"Escalated":"#f87171","Received":"#94a3b8","Processing":"#fbbf24","Ignored":"#64748b","Replied":"#34d399"}.get(status,"#94a3b8")
                st.markdown(f"<span style='font-size:12px;color:{st_color};font-weight:600;'>● {status}</span>", unsafe_allow_html=True)
            st.markdown("<hr>", unsafe_allow_html=True)

# ── PAGE 2 : THREAD WORKSPACE ─────────────────────────────────
elif page == "🧵 Thread Workspace":

    st.markdown("<h2 style='color:#e2e8f0; margin-bottom:4px;'>🧵 Thread Workspace</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748b; font-size:13px; margin-bottom:20px;'>Full conversation history · Agent reasoning · Draft approvals</div>", unsafe_allow_html=True)

    sender = st.selectbox("Select a sender to inspect", SENDERS)

    if sender:
        data   = api(f"/threads/{sender}")
        emails = data.get("emails", [])

        if not emails:
            st.warning("No emails found for this sender.")
        else:
            # Contact card
            contact = api(f"/contacts/{sender}")
            if contact and not contact.get("detail"):
                status_color = {"VIP":"#fbbf24","Active":"#34d399","Churned":"#f87171","Blocked":"#94a3b8"}.get(contact.get("status","Active"),"#34d399")
                st.markdown(f"""
                <div style='background:#0d1526;border:1px solid #1e3a5f;border-radius:12px;padding:16px 20px;margin-bottom:16px;'>
                    <div style='display:flex;align-items:center;gap:12px;margin-bottom:12px;'>
                        <div style='font-size:28px;'>👤</div>
                        <div>
                            <div style='font-weight:700;color:#e2e8f0;font-size:15px;'>{contact.get('name','')}</div>
                            <div style='color:#64748b;font-size:12px;'>{contact.get('email','')} · {contact.get('company','')}</div>
                        </div>
                        <div style='margin-left:auto;'>
                            <span style='background:#0a0f1e;border:1px solid {status_color};color:{status_color};padding:3px 12px;border-radius:20px;font-size:12px;font-weight:700;'>{contact.get('status','Active')}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                mc1,mc2,mc3,mc4 = st.columns(4)
                mc1.metric("Account Value",  f"${contact.get('account_value',0):,.0f}")
                mc2.metric("Churn Risk",     f"{contact.get('churn_risk_score',0):.0%}")
                mc3.metric("Total Emails",   contact.get("total_emails",0))
                mc4.metric("Negative Emails",contact.get("negative_emails",0))

            st.markdown(f"<div class='section-header'>Thread Timeline — {len(emails)} emails</div>", unsafe_allow_html=True)

            for email in emails:
                score   = email.get("sentiment_score")
                urgency = email.get("urgency","Low")
                label   = f"{sentiment_dot(score)} {urgency_icon(urgency)}  [{email.get('timestamp','')[:10]}]  {email.get('subject','')}"

                with st.expander(label, expanded=False):
                    left, right = st.columns([2,1])

                    with left:
                        st.markdown(f"<span style='color:#64748b;font-size:12px;'>FROM</span> <span style='color:#38bdf8;font-size:13px;font-weight:600;'>{email.get('sender','')}</span>", unsafe_allow_html=True)
                        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                        st.text_area("Body", email.get("body",""), height=130, key=f"body_{email.get('id')}", disabled=True, label_visibility="collapsed")

                    with right:
                        cat = email.get("category","")
                        cat_cls = cat.lower().replace(" ","").replace("report","") if cat else "other"
                        st.markdown(badge(cat, cat_cls), unsafe_allow_html=True)
                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

                        conf = email.get("confidence")
                        conf_color = "#34d399" if conf and conf>=0.8 else ("#fbbf24" if conf and conf>=0.6 else "#f87171")
                        rows = [
                            ("Urgency",    urgency),
                            ("Sentiment",  f"{score:.2f}" if score is not None else "—"),
                            ("Confidence", f"{conf:.0%}" if conf else "—"),
                            ("Status",     email.get("status","?")),
                        ]
                        for k,v in rows:
                            st.markdown(f"<div style='display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e3a5f;'>"
                                        f"<span style='color:#64748b;font-size:12px;'>{k}</span>"
                                        f"<span style='color:#e2e8f0;font-size:12px;font-weight:600;'>{v}</span></div>",
                                        unsafe_allow_html=True)

                        if email.get("escalation_reason"):
                            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                            st.error(f"⚠️ {email.get('escalation_reason')}")

                    # Reasoning trace
                    actions   = email.get("actions",[])
                    reasoning = [step for a in actions for step in a.get("reasoning_log",[])]
                    if reasoning:
                        st.markdown("<div class='section-header'>🤖 Agent Reasoning Trace</div>", unsafe_allow_html=True)
                        for step in reasoning:
                            st.markdown(f"""
<div class='reasoning-step'>
  <div style='color:#38bdf8;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;'>Step {step.get('step')}</div>
  <div class='reasoning-thought'>💭 {step.get('thought','')}</div>
  <div class='reasoning-action'>⚡ {step.get('action','')}</div>
  <div class='reasoning-obs'>👁️ {step.get('observation','')[:250]}</div>
</div>""", unsafe_allow_html=True)

                    # Draft
                    draft = next((a for a in actions if a.get("action_type")=="Auto-Reply" and not a.get("is_approved")), None)
                    if draft:
                        st.markdown("<div class='section-header'>📝 Proposed Reply</div>", unsafe_allow_html=True)
                        st.info(draft.get("proposed_content",""))
                        ba, bb = st.columns(2)
                        if ba.button("✅ Approve & Send", key=f"app_{draft['id']}"):
                            api(f"/drafts/{draft['id']}/approve", method="post")
                            st.success("Sent!"); st.rerun()
                        if bb.button("🚨 Escalate", key=f"esc_{email.get('id')}"):
                            st.warning("Escalated to human team.")

# ── PAGE 3 : ANALYTICS ────────────────────────────────────────
elif page == "📊 Analytics":

    st.markdown("<h2 style='color:#e2e8f0; margin-bottom:4px;'>📊 Analytics Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748b; font-size:13px; margin-bottom:20px;'>Sentiment trends · Category breakdown · At-risk accounts</div>", unsafe_allow_html=True)

    CHART_LAYOUT = dict(paper_bgcolor="#0d1526", plot_bgcolor="#0d1526",
                        font_color="#e2e8f0", font_family="Arial",
                        margin=dict(t=30,b=20,l=20,r=20))

    col1, col2 = st.columns(2)

    with col1:
        cat_data  = api("/analytics/category-breakdown")
        breakdown = cat_data.get("breakdown",[])
        if breakdown:
            df_cat = pd.DataFrame(breakdown).dropna(subset=["category"])
            fig = px.pie(df_cat, values="count", names="category",
                         color_discrete_sequence=["#38bdf8","#818cf8","#34d399","#fbbf24","#f87171","#a78bfa","#67e8f9","#86efac","#fcd34d","#fca5a5"],
                         hole=0.45)
            fig.update_traces(textfont_size=12, marker=dict(line=dict(color="#0a0f1e", width=2)))
            fig.update_layout(title="Category Breakdown", **CHART_LAYOUT,
                              legend=dict(bgcolor="#0d1526", bordercolor="#1e3a5f", borderwidth=1))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        trend_raw = api("/analytics/sentiment-trend?days=365")
        trend_pts = trend_raw.get("trend",[])
        if trend_pts:
            df_t = pd.DataFrame(trend_pts)
            df_t["timestamp"] = pd.to_datetime(df_t["timestamp"])
            fig2 = px.line(df_t, x="timestamp", y="sentiment_score",
                           color="sender" if "sender" in df_t.columns else None,
                           title="Sentiment Over Time")
            fig2.add_hline(y=0,    line_dash="dash", line_color="#64748b", line_width=1)
            fig2.add_hline(y=-0.6, line_dash="dot",  line_color="#f87171", line_width=1,
                           annotation_text="Escalation threshold", annotation_font_color="#f87171")
            fig2.update_layout(**CHART_LAYOUT)
            st.plotly_chart(fig2, use_container_width=True)

    # At-risk
    st.markdown("<div class='section-header'>⚠️ At-Risk Accounts</div>", unsafe_allow_html=True)
    if trend_pts:
        df_r = pd.DataFrame(trend_pts)
        if "sentiment_score" in df_r.columns:
            at_risk = (df_r[df_r["sentiment_score"] < -0.5]
                       .groupby("sender")
                       .agg(avg_sentiment=("sentiment_score","mean"), emails=("sender","count"))
                       .reset_index()
                       .sort_values("avg_sentiment"))
            if not at_risk.empty:
                at_risk.columns = ["Sender","Avg Sentiment","Negative Emails"]
                st.dataframe(at_risk, use_container_width=True, hide_index=True)
            else:
                st.success("✅ No at-risk accounts right now.")

    # Urgency bar
    st.markdown("<div class='section-header'>Urgency Distribution</div>", unsafe_allow_html=True)
    emails_all = all_emails()
    if emails_all:
        df_urg = pd.DataFrame(emails_all)
        if "urgency" in df_urg.columns:
            urg_counts = df_urg["urgency"].value_counts().reset_index()
            urg_counts.columns = ["Urgency","Count"]
            color_map = {"Critical":"#f87171","High":"#fbbf24","Medium":"#38bdf8","Low":"#34d399"}
            fig3 = px.bar(urg_counts, x="Urgency", y="Count",
                          color="Urgency", color_discrete_map=color_map,
                          title="Emails by Urgency Level")
            fig3.update_layout(**CHART_LAYOUT, showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

# ── PAGE 4 : RAG DEBUG ────────────────────────────────────────
elif page == "🔍 RAG Debug":

    st.markdown("<h2 style='color:#e2e8f0; margin-bottom:4px;'>🔍 RAG Knowledge Base</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748b; font-size:13px; margin-bottom:20px;'>Query the vector store · See retrieved chunks · Inspect similarity scores</div>", unsafe_allow_html=True)

    # Quick queries
    st.markdown("<div class='section-header'>Quick Queries</div>", unsafe_allow_html=True)
    qc1,qc2,qc3,qc4 = st.columns(4)
    quick = None
    if qc1.button("💰 Refund policy"):     quick = "refund policy 14 days"
    if qc2.button("📋 SLA breach"):        quick = "SLA breach legal escalation"
    if qc3.button("🔒 GDPR Article 20"):   quick = "GDPR Article 20 data portability"
    if qc4.button("📈 Pricing non-profit"): quick = "non-profit discount pricing"

    query = st.text_input("", placeholder="Type your query here…", value=quick or "", label_visibility="collapsed")

    if query:
        with st.spinner("Searching knowledge base…"):
            res = api(f"/rag/search?q={requests.utils.quote(query)}")
        chunks = res.get("results",[])

        st.markdown(f"<div class='section-header'>{len(chunks)} chunks retrieved for: <span style='color:#38bdf8;'>'{query}'</span></div>", unsafe_allow_html=True)

        for i, chunk in enumerate(chunks):
            score = chunk.get("similarity_score", 0)
            bar_w = max(5, int(score * 100)) if score > 0 else 5
            bar_color = "#34d399" if score > 0.3 else ("#fbbf24" if score > 0.1 else "#f87171")

            with st.expander(f"📄  Chunk {i+1} — {chunk.get('source','?')}  ·  Score: {score:.3f}", expanded=True):
                st.markdown(f"""
<div style='margin-bottom:8px;'>
  <div style='background:#050d1a;border-radius:4px;height:6px;width:100%;'>
    <div style='background:{bar_color};border-radius:4px;height:6px;width:{bar_w}%;'></div>
  </div>
  <div style='color:{bar_color};font-size:11px;margin-top:2px;'>Similarity: {score:.3f}</div>
</div>""", unsafe_allow_html=True)
                st.markdown(f"<div style='color:#cbd5e1;font-size:13px;line-height:1.7;background:#050d1a;padding:12px;border-radius:8px;'>{chunk.get('content','').replace(chr(10),'<br>')}</div>", unsafe_allow_html=True)

# ── PAGE 5 : AGENT DRY RUN ────────────────────────────────────
elif page == "🤖 Agent Dry Run":

    st.markdown("<h2 style='color:#e2e8f0; margin-bottom:4px;'>🤖 Agent Dry Run</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748b; font-size:13px; margin-bottom:20px;'>Simulate agent reasoning — no actions executed · Full ReAct trace visible</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>Test Scenarios</div>", unsafe_allow_html=True)
    sc1,sc2,sc3 = st.columns(3)
    preset = None
    if sc1.button("🚨 Bob — SLA Breach (ID 60)"):   preset = 60
    if sc2.button("😤 Karen — Churn (ID 33)"):       preset = 33
    if sc3.button("⚖️ Marcus — GDPR (ID 52)"):       preset = 52

    email_id = st.number_input("Email ID", min_value=1, max_value=200, value=preset or 60, label_visibility="collapsed")

    if st.button("▶️  Run Agent (Dry Run)", use_container_width=True):
        with st.spinner("Agent reasoning…"):
            result = api(f"/agent/dry-run/{email_id}", method="post")

        if "error" in result:
            st.error(result["error"])
        else:
            # Summary cards
            rc1,rc2,rc3,rc4 = st.columns(4)
            rc1.metric("Final Action", result.get("final_action","?"))
            rc2.metric("Tool Calls",   result.get("tool_calls",0))
            rc3.metric("Steps",        result.get("steps",0))
            rc4.metric("Mode",         "DRY RUN")

            st.markdown("<div class='section-header'>🧠 Full Reasoning Trace</div>", unsafe_allow_html=True)

            for step in result.get("reasoning_log",[]):
                st.markdown(f"""
<div class='reasoning-step'>
  <div style='color:#38bdf8;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>
    Step {step['step']} of {result.get('steps',0)}
  </div>
  <div class='reasoning-thought'>💭 Thought: {step.get('thought','')}</div>
  <div class='reasoning-action'>⚡ Action: {step.get('action','')}</div>
  <div class='reasoning-obs'>👁️ Observation: {step.get('observation','')[:400]}</div>
</div>""", unsafe_allow_html=True)

            final = result.get("final_action","")
            final_color = {"security_escalated":"#f87171","legal_escalated":"#fbbf24","draft_created":"#34d399"}.get(final,"#94a3b8")
            st.markdown(f"""
<div style='background:#0d1526;border:1px solid {final_color};border-radius:10px;padding:16px;margin-top:12px;text-align:center;'>
  <div style='color:{final_color};font-size:18px;font-weight:700;'>Final Decision: {final.upper().replace("_"," ")}</div>
  <div style='color:#64748b;font-size:12px;margin-top:4px;'>{result.get("tool_calls",0)} tool calls · Dry run — no changes made</div>
</div>""", unsafe_allow_html=True)
