-- SenAI CRM — Complete Database Schema
-- Migration v1.0 | June 2026
-- SQLite compatible (production: PostgreSQL + pgvector)

PRAGMA foreign_keys = ON;

-- ── contacts ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contacts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    email            TEXT    NOT NULL UNIQUE,
    name             TEXT,
    company          TEXT,
    status           TEXT    NOT NULL DEFAULT 'Active'
                             CHECK(status IN ('VIP','Active','Churned','Blocked')),
    account_value    REAL    NOT NULL DEFAULT 0.0,
    churn_risk_score REAL    NOT NULL DEFAULT 0.0
                             CHECK(churn_risk_score BETWEEN 0.0 AND 1.0),
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_contact_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contacts_email  ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);

-- ── threads ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS threads (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id      TEXT    NOT NULL UNIQUE,
    subject        TEXT,
    sender_email   TEXT    NOT NULL REFERENCES contacts(email),
    first_seen_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status         TEXT    NOT NULL DEFAULT 'Open'
                           CHECK(status IN ('Open','Resolved','Escalated','Ignored')),
    assigned_to    TEXT
);

CREATE INDEX IF NOT EXISTS idx_threads_thread_id    ON threads(thread_id);
CREATE INDEX IF NOT EXISTS idx_threads_sender_email ON threads(sender_email);
CREATE INDEX IF NOT EXISTS idx_threads_status       ON threads(status);

-- ── emails ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS emails (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id        TEXT    NOT NULL REFERENCES threads(thread_id),
    message_id       TEXT    NOT NULL UNIQUE,           -- deduplication key
    sender           TEXT    NOT NULL,
    subject          TEXT,
    body             TEXT,
    timestamp        DATETIME,
    sentiment_score  REAL    CHECK(sentiment_score BETWEEN -1.0 AND 1.0),
    category         TEXT    CHECK(category IN (
                         'Complaint','Inquiry','Bug Report','Feature Request',
                         'Compliance','Legal','Billing','Spam','Internal',
                         'Security','Other'
                     )),
    urgency          TEXT    CHECK(urgency IN ('Critical','High','Medium','Low')),
    requires_human   INTEGER,                           -- 0=false, 1=true (SQLite bool)
    confidence       REAL    CHECK(confidence BETWEEN 0.0 AND 1.0),
    raw_entities     TEXT,                              -- JSON string
    status           TEXT    NOT NULL DEFAULT 'Received'
                             CHECK(status IN (
                                 'Received','Processing','Replied',
                                 'Escalated','Ignored'
                             )),
    suggested_reply  TEXT,
    escalation_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_emails_thread_id   ON emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_emails_message_id  ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_emails_sender      ON emails(sender);
CREATE INDEX IF NOT EXISTS idx_emails_status      ON emails(status);
CREATE INDEX IF NOT EXISTS idx_emails_urgency     ON emails(urgency);
CREATE INDEX IF NOT EXISTS idx_emails_sentiment   ON emails(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_emails_timestamp   ON emails(timestamp);

-- ── actions ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS actions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id            INTEGER NOT NULL REFERENCES emails(id),
    agent_reasoning_log TEXT,                           -- JSON string: ReAct trace
    action_type         TEXT    NOT NULL
                                CHECK(action_type IN (
                                    'Auto-Reply','Escalate','Legal-Flag',
                                    'Ticket-Created','Ignored'
                                )),
    proposed_content    TEXT,
    is_approved         INTEGER NOT NULL DEFAULT 0,     -- 0=pending, 1=approved
    approved_by         TEXT,
    executed_at         DATETIME
);

CREATE INDEX IF NOT EXISTS idx_actions_email_id    ON actions(email_id);
CREATE INDEX IF NOT EXISTS idx_actions_action_type ON actions(action_type);
CREATE INDEX IF NOT EXISTS idx_actions_is_approved ON actions(is_approved);

-- ── audit_log ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type  TEXT    NOT NULL,                      -- 'email','action','contact'
    entity_id    INTEGER NOT NULL,
    action       TEXT    NOT NULL,
    performed_by TEXT    NOT NULL,                      -- 'agent' or user id
    timestamp    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    diff         TEXT                                   -- JSON: before/after snapshot
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts     ON audit_log(timestamp);

-- ── knowledge_chunks ─────────────────────────────────────────
-- NOTE: In SQLite, embedding stored as BLOB (base64 bytes).
-- In production PostgreSQL, use: embedding vector(384)
-- and CREATE INDEX ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source_doc TEXT    NOT NULL,                        -- e.g. 'refund_policy.md'
    chunk_text TEXT    NOT NULL,
    embedding  BLOB,                                    -- 384-dim float32 vector
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_source ON knowledge_chunks(source_doc);

-- ── web_intelligence_cache ───────────────────────────────────
CREATE TABLE IF NOT EXISTS web_intelligence_cache (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url    TEXT    NOT NULL,
    target_entity TEXT    NOT NULL,                     -- e.g. company name
    scraped_data  TEXT    NOT NULL,                     -- JSON
    scraped_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at    DATETIME NOT NULL                     -- scraped_at + 6 hours
);

CREATE INDEX IF NOT EXISTS idx_webcache_entity  ON web_intelligence_cache(target_entity);
CREATE INDEX IF NOT EXISTS idx_webcache_expires ON web_intelligence_cache(expires_at);

-- ── seed: default contacts from dataset ─────────────────────
INSERT OR IGNORE INTO contacts (email, name, company, status) VALUES
    ('alice.smith@greenlight-npo.org', 'Alice Smith',   'Greenlight NPO',   'Active'),
    ('bob.jones@enterprise.net',       'Bob Jones',     'Enterprise Corp',  'Active'),
    ('karen.w@retail-co.com',          'Karen W',       'RetailCo',         'Active'),
    ('eleanor.voss@meditrust.org',     'Eleanor Voss',  'MediTrust',        'VIP'),
    ('marcus.del@fintech-startup.co',  'Marcus Del',    'Fintech Startup',  'Active'),
    ('nadia.k@logisticspro.com',       'Nadia K',       'LogisticsPro',     'Active'),
    ('raj.p@techventures.in',          'Raj P',         'TechVentures',     'Active'),
    ('sara.m@cloudbase.io',            'Sara M',        'CloudBase',        'Active'),
    ('tom.h@retailgiant.com',          'Tom H',         'RetailGiant',      'Active'),
    ('lisa.b@startup.io',              'Lisa B',        'Startup IO',       'Active');

-- ── production migration notes ───────────────────────────────
-- When migrating to PostgreSQL:
--
-- 1. Replace INTEGER/AUTOINCREMENT with SERIAL or BIGSERIAL
-- 2. Replace TEXT with VARCHAR(255) where length is bounded
-- 3. Replace BLOB embedding with vector(384) from pgvector extension:
--      CREATE EXTENSION IF NOT EXISTS vector;
--      ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(384);
--      CREATE INDEX ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
--        WITH (lists = 100);
--
-- 4. Add connection pooling (pgbouncer or SQLAlchemy pool_size=10)
-- 5. Add composite index for sentiment trend query:
--      CREATE INDEX idx_emails_sender_ts ON emails(sender, timestamp, sentiment_score);
-- 6. Partition audit_log by month for large scale:
--      PARTITION BY RANGE (timestamp)
