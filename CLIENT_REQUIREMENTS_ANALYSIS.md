# Client Requirements Analysis & Gap Assessment

**Date**: 2026-04-16  
**Source**: Client Requirements Document (received)  
**Status**: CRITICAL - New requirements change implementation order

---

## 📋 What Client Wants

### 1. Noor Allocation Request System
```
Table: noor_allocation_requests
Fields:
  - id (auto)
  - full_name
  - purpose (why they want Noor)
  - timeline (when they need it)
  - delivery_location
  - contact_method (email, phone, both)
  - contact_details
  - status (pending / approved / declined)
  - cooldown_until (date - prevent spam)
  - reviewed_at (when concierge reviewed)
  - submitted_at (when submitted)
  - internal_notes (concierge team notes)
  - source = "AI Concierge" (always)
```

**Purpose**: Noor Collection has only 143 pieces. This tracks formal requests to ensure:
- Only serious buyers request
- Prevent spam/multiple requests from same person
- Concierge can manually approve/decline
- Track timeline and delivery
- Internal notes for team context

### 2. Rate Limiting & Crash Prevention

**MANDATORY Requirements:**
```
✅ AI triggered ONLY on user message (not page load)
✅ Max 5 requests per minute per IP
✅ 15-second timeout for each request
✅ Async request handling (non-blocking)
✅ Catch API errors gracefully
✅ Fallback message: "There appears to be a temporary delay. Please try again shortly."
✅ Cap conversation history to last 10-15 messages (not full transcript)
```

**Why?** Prevents:
- Server overload
- API costs exploding
- Bad user experience (slow pages)
- System crashes from cascading requests

---

## 🔴 Gap Analysis: Current vs Required

| Requirement | Current Status | Gap | Priority |
|------------|-----------------|-----|----------|
| **User Authentication** | ✅ Designed | None | High |
| **Chat History** | ✅ Designed | None | High |
| **User Profiles** | ✅ Designed | None | High |
| **Noor Allocation Requests** | ❌ MISSING | **CRITICAL** | CRITICAL |
| **Rate Limiting** | ❌ MISSING | **CRITICAL** | CRITICAL |
| **Request Timeout (15s)** | ❌ MISSING | **CRITICAL** | CRITICAL |
| **Crash Prevention** | ⚠️ Partial | Needs hardening | High |
| **Conversation Cap (10-15)** | ⚠️ Designed but not enforced | Needs middleware | High |
| **Async Request Handling** | ✅ FastAPI built-in | None | Medium |
| **Error Graceful Handling** | ⚠️ Partial | Needs improvement | High |

---

## 🚨 Critical Missing Piece: Noor Allocation System

**What We're Missing:**
```
When user asks about Noor OR wants to request Noor:
  ❌ No formal request system
  ❌ No approval/decline workflow
  ❌ No cooldown tracking
  ❌ No concierge review process
  ❌ No status tracking
```

**What Client Needs:**
```
When user asks about Noor OR wants to request Noor:
  ✅ Bot collects: full_name, purpose, timeline, delivery_location, contact_method
  ✅ Save to noor_allocation_requests table
  ✅ Alert concierge to review
  ✅ Concierge approves/declines
  ✅ User notified of status
  ✅ Prevent re-requests for cooldown period
  ✅ Track everything in database
```

---

## 📊 Implementation Order (Revised)

**PREVIOUS ORDER** (wrong):
```
1. User database ← Start here
2. Chat history
3. Personalization
4. Appointment system
5. Rate limiting
6. Noor allocation
```

**CORRECT ORDER** (from client requirements):
```
PHASE 1: Foundation (Days 1-2)
├─ User database + authentication
├─ Rate limiting middleware (CRITICAL)
├─ Request timeout (15s)
└─ Error handling improvements

PHASE 2: Core Features (Days 3-4)
├─ Chat history
├─ Personalization engine
└─ Conversation history capping

PHASE 3: Business Logic (Days 5-6)
├─ Noor Allocation Request table
├─ Noor request workflow
├─ Concierge approval/decline
└─ Cooldown tracking

PHASE 4: Operational (Days 7-8)
├─ Appointment system (now with Noor integration)
├─ Notification system
└─ Status tracking endpoints

PHASE 5: Testing & Deployment (Days 9)
├─ Load testing
├─ Stress testing (rate limits)
├─ Error scenario testing
└─ Production deployment
```

---

## 🔧 Database Schema: Complete Picture

### Table 1: Users
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  phone VARCHAR(20),
  
  -- Profile (from profiling questions)
  age_range VARCHAR(50),
  skin_tone VARCHAR(50),
  style_preference VARCHAR(100),
  
  -- Preferences (learned)
  preferred_collection VARCHAR(100),
  favorite_metals TEXT[],
  favorite_styles TEXT[],
  
  -- Status
  status VARCHAR(50) DEFAULT 'active',
  created_at TIMESTAMP,
  last_activity_at TIMESTAMP
);
```

### Table 2: Chat History
```sql
CREATE TABLE chat_history (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  message_type VARCHAR(50),      -- "user", "assistant"
  content TEXT,
  intent VARCHAR(100),           -- "product", "noor", "general"
  skill_used VARCHAR(100),
  latency_ms INTEGER,
  
  conversation_session_id UUID,
  created_at TIMESTAMP
);
```

### Table 3: Appointments
```sql
CREATE TABLE appointments (
  id UUID PRIMARY KEY,
  reference_id VARCHAR(50) UNIQUE,
  user_id UUID REFERENCES users(id),
  
  appointment_type VARCHAR(100),
  preferred_date VARCHAR(100),
  notes TEXT,
  status VARCHAR(50),
  
  confirmed_by VARCHAR(100),
  confirmed_date TIMESTAMP,
  scheduled_date TIMESTAMP,
  meeting_link VARCHAR(500),
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Table 4: **NOOR ALLOCATION REQUESTS** (NEW - CRITICAL)
```sql
CREATE TABLE noor_allocation_requests (
  id UUID PRIMARY KEY,
  
  -- User who requested
  user_id UUID REFERENCES users(id),
  full_name VARCHAR(255),
  
  -- Request details
  purpose TEXT,                    -- Why they want Noor
  timeline VARCHAR(100),           -- When they need it
  delivery_location VARCHAR(255),  -- Where to ship
  
  -- Contact info
  contact_method VARCHAR(50),      -- "email", "phone", "both"
  contact_details VARCHAR(255),    -- email@example.com or phone number
  
  -- Status & tracking
  status VARCHAR(50) DEFAULT 'pending',  -- "pending", "approved", "declined"
  cooldown_until TIMESTAMP,        -- Can't request again until this date
  reviewed_at TIMESTAMP,           -- When concierge reviewed
  submitted_at TIMESTAMP,          -- When user submitted
  
  -- Internal
  internal_notes TEXT,
  reviewed_by VARCHAR(100),        -- Concierge team member
  source VARCHAR(50) DEFAULT 'AI Concierge',
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Table 5: User Activity Log
```sql
CREATE TABLE user_activity (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  activity_type VARCHAR(100),
  details JSONB,
  created_at TIMESTAMP
);
```

---

## ⚙️ Rate Limiting Implementation

### Middleware Required:

```python
# app/middleware/rate_limiter.py

from fastapi import Request, HTTPException
from datetime import datetime, timedelta
import redis

redis_client = redis.Redis(host='localhost', port=6379)

MAX_REQUESTS_PER_MINUTE = 5
REQUEST_TIMEOUT_SECONDS = 15

async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiter: Max 5 requests per minute per IP
    """
    if request.method != "POST" or "/chat" not in request.url.path:
        return await call_next(request)
    
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    # Check current request count
    current = redis_client.get(key)
    if current and int(current) >= MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment."
        )
    
    # Increment counter
    redis_client.incr(key)
    redis_client.expire(key, 60)  # Reset every minute
    
    # Call endpoint with timeout
    try:
        response = await asyncio.wait_for(
            call_next(request),
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        return response
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=408,
            content={
                "error": "There appears to be a temporary delay. Please try again shortly."
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "There appears to be a temporary delay. Please try again shortly."
            }
        )
```

### Conversation History Capping:

```python
# In /chat endpoint

def cap_conversation_history(history: List[ContextMessage], max_messages=15) -> List[ContextMessage]:
    """Keep only last 10-15 messages to avoid token overflow"""
    if len(history) <= max_messages:
        return history
    
    # Keep last N messages
    return history[-max_messages:]

# Usage:
@router.post("/chat")
async def chat(request: ChatRequest, user_id: str):
    # Load chat history
    chat_history = db.query(ChatMessage)\
        .filter(ChatMessage.user_id == user_id)\
        .order_by(ChatMessage.created_at.desc())\
        .limit(50)\
        .all()
    
    # CAP IT at 15 messages
    capped_history = cap_conversation_history(chat_history, max_messages=15)
    
    # Never send full transcript
    assert len(capped_history) <= 15, "History not capped!"
    
    # Use capped history...
```

---

## 🎯 Noor Allocation Workflow

### Step 1: User Expresses Interest
```
User: "I'm interested in the Noor Collection"
Bot: "The Noor Collection is our most exclusive offering.
     To request access, I'll need a few details..."
```

### Step 2: Bot Collects Information
```
Bot: "What's your full name?"
User: "Sarah Johnson"

Bot: "What's your purpose for requesting a Noor piece?
     (e.g., engagement ring, anniversary gift, personal collection)"
User: "Anniversary gift for my wife"

Bot: "When do you need it by?"
User: "Within 3 months"

Bot: "Where should we deliver it?"
User: "New York, NY"

Bot: "Best way to contact you - email, phone, or both?"
User: "Email please"

Bot: "Perfect! sarah@example.com?"
User: "Yes"
```

### Step 3: Save to Database
```python
noor_request = NoorAllocationRequest(
    user_id=user_id,
    full_name="Sarah Johnson",
    purpose="Anniversary gift",
    timeline="Within 3 months",
    delivery_location="New York, NY",
    contact_method="email",
    contact_details="sarah@example.com",
    status="pending",
    source="AI Concierge",
    submitted_at=datetime.utcnow()
)
db.add(noor_request)
db.commit()
```

### Step 4: Alert Concierge
```python
# Email to concierge team
send_email(
    to="concierge@aueshah.com",
    subject="New Noor Collection Request - Sarah Johnson",
    body=f"""
    New Noor Allocation Request:
    
    Name: Sarah Johnson
    Purpose: Anniversary gift
    Timeline: Within 3 months
    Delivery: New York, NY
    Contact: sarah@example.com
    Status: PENDING REVIEW
    
    Please approve or decline in the admin panel.
    """
)

# Slack notification
notify_slack(
    channel="noor-requests",
    message="New Noor request: Sarah Johnson (Anniversary gift)"
)
```

### Step 5: Concierge Reviews & Approves
```python
# Concierge uses admin panel to approve/decline
PUT /admin/noor-requests/{request_id}
{
    "status": "approved",  # or "declined"
    "internal_notes": "Perfect client, high budget, will reach out with options",
    "reviewed_by": "Concierge Team"
}
```

### Step 6: User Notified
```python
# Send email to user
send_email(
    to="sarah@example.com",
    subject="Your Noor Collection Request - APPROVED",
    body=f"""
    Great news, Sarah!
    
    Your request for a Noor Collection piece has been APPROVED.
    
    Our concierge team will contact you shortly at 
    sarah@example.com to discuss options.
    
    Reference ID: NOR-SARAH-001
    """
)

# Update user's appointment/activity status
update_user_activity(
    user_id=user_id,
    activity_type="noor_request_approved",
    details={"request_id": request_id}
)
```

### Step 7: Cooldown Period
```python
# Set cooldown so user can't spam requests
UPDATE noor_allocation_requests
SET cooldown_until = NOW() + INTERVAL '90 days'
WHERE user_id = user_id AND status = 'approved'

# Next time user tries to request Noor:
if user_has_active_noor_request():
    bot_says: "You already have an active Noor request in progress. 
              Our concierge team will contact you shortly."
```

---

## 📋 Implementation Checklist

### Phase 1: Foundation (CRITICAL - DO FIRST)
- [ ] Add Redis for rate limiting
- [ ] Implement rate_limit_middleware (5 req/min, 15s timeout)
- [ ] Add error handling wrapper
- [ ] Test timeout scenarios
- [ ] Add conversation history capping (10-15 messages)

### Phase 2: User System
- [ ] Create users table
- [ ] Implement authentication (/login)
- [ ] Update /chat endpoint
- [ ] Load user profiles
- [ ] Load chat history

### Phase 3: Noor Allocation
- [ ] Create noor_allocation_requests table
- [ ] Build /noor-request endpoint
- [ ] Create admin approval panel
- [ ] Add cooldown tracking
- [ ] Implement notifications (email + Slack)
- [ ] Create /noor-request-status endpoint

### Phase 4: Appointments & Notifications
- [ ] Create appointments table
- [ ] Update /appointment-request endpoint
- [ ] Add email notifications
- [ ] Add Slack notifications
- [ ] Create status tracking endpoint

### Phase 5: Testing
- [ ] Load test (5 req/min enforcement)
- [ ] Timeout test (15s cutoff)
- [ ] Error scenario tests
- [ ] Database tests
- [ ] End-to-end flow tests

---

## 🚀 Next Steps (Recommended)

**IMMEDIATE (This Week):**
1. ✅ Implement rate limiting (CRITICAL)
2. ✅ Add request timeout (CRITICAL)
3. ✅ Create noor_allocation_requests table (CRITICAL)
4. ✅ Build Noor request workflow

**NEXT WEEK:**
5. ✅ User authentication system
6. ✅ Chat history + personalization
7. ✅ Appointment system
8. ✅ Notification system

**WEEK 3:**
9. ✅ Admin panel (for concierge to approve/decline)
10. ✅ Cooldown tracking
11. ✅ Testing & QA
12. ✅ Production deployment

---

## ⚠️ Why Rate Limiting is CRITICAL

**Without rate limiting:**
```
Attacker or buggy client:
  → Sends 100 requests in 10 seconds
  → Each request calls OpenAI API ($$)
  → Server gets overloaded
  → Service crashes
  → Legitimate users can't access
  → Cost: $1000+ in API bills

With rate limiting:
  → Max 5 requests per minute per IP
  → 15-second timeout
  → Graceful error message
  → Server stays healthy
  → Cost controlled
  → Users protected
```

---

## Summary

**Client provided requirements that are STRICTER than what we designed:**

1. ✅ Rate limiting (max 5 req/min) - WE NEED TO ADD THIS
2. ✅ Noor allocation system - WE NEED TO ADD THIS
3. ✅ Conversation history capping - WE NEED TO ENFORCE THIS
4. ✅ 15-second timeout - WE NEED TO ADD THIS
5. ✅ Crash prevention - WE NEED TO HARDEN THIS

**These are non-negotiable. Client is being smart - they want a ROBUST system.**

**Recommendation: Implement in this order:**
1. Rate limiting + timeout (THIS WEEK - can't wait)
2. Noor allocation system (NEXT WEEK - core business logic)
3. User authentication (NEXT WEEK - personalization)
4. Everything else (WEEK 3)

