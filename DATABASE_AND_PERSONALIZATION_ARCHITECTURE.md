# Aueshah Concierge — Database & Personalization Architecture

**Date**: 2026-04-16  
**Requirement**: User profiles + chat history + personalization + appointment tracking  
**Priority**: CRITICAL for production

---

## Executive Summary

**Recommended Approach**: **OPTION D - Complete Database + User Profile + Chat History System**

This is the ONLY approach that will deliver what your client needs:
- ✅ Bot remembers users across sessions
- ✅ Personalized recommendations based on saved profile
- ✅ Full chat history retrieval
- ✅ Appointment tracking linked to user
- ✅ Activity timeline for the client
- ✅ Proper appointment notifications

**Effort**: ~2-3 days of development  
**Complexity**: Medium (database + user management)  
**ROI**: HIGH (enables all personalization features)

---

## What You Need (Complete Picture)

### Current State ❌
```
User comes to chat → Bot has NO memory
- Doesn't know who they are
- Doesn't remember previous conversations
- Can't personalize recommendations
- Appointments lost in server logs
- No user profile data
```

### Desired State ✅
```
User comes to chat → Bot recognizes them
- Retrieves user profile (age, skin tone, style, contact info)
- Loads previous chat history
- Personalizes greetings ("Welcome back, Sarah!")
- Recommends pieces based on past preferences
- Shows appointment status
- Remembers what they discussed last time
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     USER COMES TO CHAT                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │   User Authentication/Login    │
        │  (Email + reference ID check)  │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   Load User Profile from DB    │
        │  (age, skin, style, contact)   │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  Load Chat History from DB     │
        │  (last 10-15 messages)         │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │    Bot Receives Message        │
        │  + User Profile + History      │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   Personalized Response        │
        │  (uses profile data, history)  │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   Save to Chat History DB      │
        │  (user message + bot reply)    │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  Update User Last Activity     │
        └────────────────────────────────┘
```

---

## Database Schema (Required)

### Table 1: Users
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  phone VARCHAR(20),
  created_at TIMESTAMP,
  last_activity_at TIMESTAMP,
  
  -- Profile (collected during first chat)
  age_range VARCHAR(50),           -- "30s", "40s", etc
  skin_tone VARCHAR(50),            -- "cool", "warm", "neutral"
  style_preference VARCHAR(100),    -- "minimalist", "statement", etc
  
  -- Preferences (learned from interactions)
  preferred_collection VARCHAR(100), -- "Noor", "Empire", "Velvet", etc
  favorite_metals TEXT[],           -- ["white gold", "rose gold"]
  favorite_styles TEXT[],           -- ["heritage", "minimalist"]
  
  -- Activity tracking
  total_messages INTEGER DEFAULT 0,
  last_message_date TIMESTAMP,
  conversation_count INTEGER DEFAULT 0,
  
  -- Status
  status VARCHAR(50) DEFAULT 'active'  -- "active", "inactive", "blocked"
);
```

### Table 2: Chat History
```sql
CREATE TABLE chat_history (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  message_type VARCHAR(50),      -- "user", "assistant"
  content TEXT,
  
  -- Metadata
  intent VARCHAR(100),           -- "product", "noor", "general", etc
  skill_used VARCHAR(100),       -- which agent handled it
  latency_ms INTEGER,
  
  created_at TIMESTAMP,
  conversation_session_id UUID   -- group messages by session
);
```

### Table 3: Appointments
```sql
CREATE TABLE appointments (
  id UUID PRIMARY KEY,
  reference_id VARCHAR(50) UNIQUE, -- APT-XXXXXXXX
  user_id UUID REFERENCES users(id),
  
  -- Request details
  appointment_type VARCHAR(100),   -- "virtual", "in-person", "bespoke"
  preferred_date VARCHAR(100),
  notes TEXT,
  
  -- Status
  status VARCHAR(50) DEFAULT 'requested',  -- "requested", "confirmed", "scheduled", "completed"
  
  -- Concierge updates
  confirmed_by VARCHAR(100),
  confirmed_date TIMESTAMP,
  scheduled_date TIMESTAMP,
  scheduled_time VARCHAR(50),
  meeting_link VARCHAR(500),       -- Zoom/Meet link
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Table 4: User Activity Log
```sql
CREATE TABLE user_activity (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  activity_type VARCHAR(100),    -- "viewed_collection", "asked_about_noor", "scheduled_appointment"
  details JSONB,
  created_at TIMESTAMP
);
```

---

## Implementation Steps

### Phase 1: Database Setup (1 day)

**Step 1.1: Choose Database**
```
Option A: PostgreSQL (RECOMMENDED)
- Mature, reliable
- JSONB support
- Great for complex queries
- Good for production

Option B: MongoDB
- Flexible schema
- Good for chat history (document storage)
- But more complex relationships

RECOMMENDATION: PostgreSQL + SQLAlchemy ORM
```

**Step 1.2: Add Dependencies**
```bash
pip install sqlalchemy psycopg2-binary alembic
```

**Step 1.3: Create Models**
```python
# app/models/database.py

from sqlalchemy import Column, String, Integer, DateTime, Text, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    age_range = Column(String(50))
    skin_tone = Column(String(50))
    style_preference = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    message_type = Column(String(50))  # "user" or "assistant"
    content = Column(Text)
    intent = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_id = Column(String(50), unique=True)
    user_id = Column(String(36), nullable=False)
    appointment_type = Column(String(100))
    status = Column(String(50), default="requested")
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Step 1.4: Setup Database Connection**
```python
# app/config/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/aueshah")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### Phase 2: User Authentication (1 day)

**Step 2.1: Add Login Endpoint**
```python
# app/api/auth.py

@router.post("/login")
async def login(email: str, db=Depends(get_db)):
    """
    Simple email-based login (no password for MVP).
    Client provides email, we check if user exists.
    If new user, create profile.
    Return user ID + session token.
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # New user - create profile
        user = User(email=email)
        db.add(user)
        db.commit()
    
    # Generate session token
    session_token = generate_token(user.id)
    
    return {
        "user_id": user.id,
        "session_token": session_token,
        "is_new_user": not user.age_range  # Profile incomplete
    }
```

**Step 2.2: Update Chat Endpoint**
```python
# app/api/routes.py

@router.post("/chat")
async def chat(
    request: ChatRequest,
    user_id: str = Header(...),  # Require user_id in header
    db=Depends(get_db),
    orchestrator=Depends(get_orchestrator)
):
    """Chat endpoint now requires authentication"""
    
    # Load user profile
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Load chat history (last 10 messages)
    chat_history = db.query(ChatMessage)\
        .filter(ChatMessage.user_id == user_id)\
        .order_by(ChatMessage.created_at.desc())\
        .limit(10)\
        .all()
    
    # Prepare context for bot
    system_context = f"""
    User Profile:
    - Age: {user.age_range}
    - Skin Tone: {user.skin_tone}
    - Style: {user.style_preference}
    - Previous conversations: {len(chat_history)}
    """
    
    # Call bot with context
    response = await orchestrator.handle_chat(request, system_context)
    
    # Save chat to history
    user_msg = ChatMessage(user_id=user_id, message_type="user", content=request.message)
    bot_msg = ChatMessage(user_id=user_id, message_type="assistant", content=response.reply)
    
    db.add(user_msg)
    db.add(bot_msg)
    db.commit()
    
    # Update last activity
    user.last_activity_at = datetime.utcnow()
    db.commit()
    
    return response
```

---

### Phase 3: Personalization (1 day)

**Step 3.1: Update System Prompt with User Context**
```python
def build_personalized_prompt(user: User, chat_history: List[ChatMessage]) -> str:
    """Build system prompt that includes user profile + history"""
    
    return f"""
    IDENTITY:
    You are the Aueshah Concierge...
    
    CURRENT USER CONTEXT:
    Name/Email: {user.email}
    Age: {user.age_range}
    Skin Tone: {user.skin_tone}
    Style Preference: {user.style_preference}
    Last Visit: {user.last_activity_at.strftime('%B %d, %Y')}
    
    PREVIOUS CONVERSATION SUMMARY:
    {summarize_chat_history(chat_history)}
    
    PERSONALIZATION TIPS:
    - Greet by name if known
    - Reference previous discussions
    - Recommend based on stated preferences
    - Remember past appointments/requests
    """
```

**Step 3.2: Personalized Greeting**
```python
def get_personalized_greeting(user: User) -> str:
    """Generate greeting based on user history"""
    
    if user.last_activity_at == user.created_at:
        # First visit
        return "Welcome to Aueshah! I'm delighted to meet you."
    
    else:
        # Returning user
        days_since = (datetime.utcnow() - user.last_activity_at).days
        
        if days_since == 0:
            return f"Welcome back! Good to see you again today."
        elif days_since == 1:
            return f"Welcome back! We missed you yesterday."
        elif days_since < 7:
            return f"Welcome back! It's been {days_since} days."
        else:
            return f"Welcome back! We haven't seen you in {days_since} days. How have you been?"
```

**Step 3.3: Smart Recommendations**
```python
def recommend_based_on_profile(user: User, db) -> str:
    """Recommend pieces based on saved preferences"""
    
    recommendations = []
    
    if user.skin_tone == "cool" and user.style_preference == "heritage":
        # Recommend cool-tone heritage pieces
        recs = db.query(Product)\
            .filter(Product.metal_tone == "cool")\
            .filter(Product.style == "heritage")\
            .limit(3)\
            .all()
        recommendations.extend(recs)
    
    return format_recommendations(recommendations)
```

---

### Phase 4: Appointment Integration (1 day)

**Step 4.1: Update Appointment Endpoint**
```python
@router.post("/appointment-request")
async def request_appointment(
    request: AppointmentRequest,
    user_id: str = Header(...),
    db=Depends(get_db)
):
    """Appointment request now links to user"""
    
    reference_id = f"APT-{uuid.uuid4().hex[:8].upper()}"
    
    # Save appointment to database
    appointment = Appointment(
        reference_id=reference_id,
        user_id=user_id,
        appointment_type=request.appointment_type,
        preferred_date=request.preferred_date,
        notes=request.notes,
        status="requested"
    )
    db.add(appointment)
    db.commit()
    
    # ✅ NOW: Send email to concierge
    await send_email_to_concierge(appointment)
    
    # ✅ NOW: Send confirmation email to user
    await send_confirmation_email_to_user(appointment)
    
    # ✅ NOW: Send Slack notification
    await notify_concierge_slack(appointment)
    
    return AppointmentResponse(
        status="success",
        message=f"Your appointment request ({reference_id}) has been submitted.",
        reference_id=reference_id
    )
```

**Step 4.2: Check Appointment Status**
```python
@router.get("/appointment-status/{reference_id}")
async def check_appointment_status(
    reference_id: str,
    user_id: str = Header(...),
    db=Depends(get_db)
):
    """User can check their appointment status"""
    
    appointment = db.query(Appointment)\
        .filter(Appointment.reference_id == reference_id)\
        .filter(Appointment.user_id == user_id)\
        .first()
    
    if not appointment:
        return {"status": "not_found"}
    
    return {
        "reference_id": reference_id,
        "status": appointment.status,  # "requested", "confirmed", "scheduled"
        "created_at": appointment.created_at,
        "confirmed_at": appointment.confirmed_date,
        "scheduled_date": appointment.scheduled_date,
        "meeting_link": appointment.meeting_link
    }
```

---

## Complete Data Flow Example

### User Journey:

```
FIRST VISIT:
═══════════════════════════════════════════

1. User goes to Aueshah website
2. Clicks "Chat with Concierge"
3. Enters email: "sarah@example.com"
4. System checks database:
   - User not found → Create new user record
   - Generate user_id: "uuid-123"
   - Return session_token
5. Bot greets: "Welcome to Aueshah! I'm delighted to meet you."
6. Bot asks profiling questions (age → tone → style)
7. User answers all questions
8. System saves profile to database:
   - age_range: "30s"
   - skin_tone: "cool"
   - style_preference: "heritage"
9. Bot recommends heritage pieces with cool-tone metals
10. User asks about Noor Collection
11. Chat saved to chat_history table
12. User asks for appointment
13. Appointment saved with user_id linked


SECOND VISIT (1 week later):
═══════════════════════════════════════════

1. User returns to website
2. Enters email: "sarah@example.com"
3. System checks database:
   - User found! Load profile
4. System loads chat_history (last 10 messages)
5. Bot greets personalized:
   "Welcome back, Sarah! It's been 7 days. 
    Last time you were interested in the Noor Collection. 
    Would you like to continue exploring those?"
6. Bot uses saved profile to recommend:
   - Cool-tone metals (not warm)
   - Heritage style (not modern)
   - Similar to pieces discussed last time
7. User asks about previous appointment
8. System queries appointments table:
   - Shows status: "confirmed"
   - Shows scheduled date: "2026-04-23 at 2:00 PM"
   - Shows meeting link: "https://zoom.us/..."
9. User continues conversation
10. All new messages saved to chat_history
```

---

## Benefits of Complete Solution

### For Users ✅
- Bot remembers who they are
- Personalized recommendations
- Appointment status tracking
- Full conversation history
- Faster service (no re-profiling needed)

### For Concierge Team ✅
- Appointment notifications (email + Slack)
- User profiles with preferences
- Conversation context before calling
- Activity timeline per user
- Follow-up reminders

### For Business ✅
- Increased conversion (personalization)
- Better customer insights
- Improved retention (remembers users)
- Operational efficiency (chat history)
- Appointment tracking (no lost requests)

---

## Tech Stack (Recommended)

```
Backend Database: PostgreSQL
  - install: apt-get install postgresql
  - or use managed service: AWS RDS, Google Cloud SQL, DigitalOcean

ORM: SQLAlchemy
  - install: pip install sqlalchemy psycopg2-binary

Migrations: Alembic
  - install: pip install alembic
  - reason: manage schema changes safely

Caching (optional): Redis
  - reason: cache user profiles + chat history
  - improves latency for returning users

Email Service: Resend
  - reason: send appointment + Noor confirmations and concierge alerts
  - simple signup (single API key), 3,000 emails/month free, async-friendly

Slack Integration: slack-sdk
  - reason: notify concierge team
  - real-time alerts
```

---

## Timeline & Effort

| Phase | Component | Effort | Timeline |
|-------|-----------|--------|----------|
| 1 | Database Setup + Schema | 1 day | Day 1 |
| 2 | User Authentication | 1 day | Day 2 |
| 3 | Chat History + Personalization | 1 day | Day 3 |
| 4 | Appointment Integration | 0.5 days | Day 3.5 |
| 5 | Testing + Documentation | 0.5 days | Day 4 |
| **Total** | **Complete System** | **~3.5 days** | **~1 week** |

---

## Implementation Order

1. ✅ Setup PostgreSQL database
2. ✅ Create SQLAlchemy models (User, ChatMessage, Appointment)
3. ✅ Add authentication endpoint (/login)
4. ✅ Update /chat to require user_id + load profile
5. ✅ Save chat history to database
6. ✅ Build personalization logic (greeting, recommendations)
7. ✅ Add appointment to database + notifications
8. ✅ Create appointment status endpoint
9. ✅ Integration testing
10. ✅ Deploy to staging

---

## Cost Estimate

| Component | Monthly Cost |
|-----------|--------------|
| PostgreSQL (AWS RDS) | $20–50 |
| Resend (emails) | $0–20 |
| Slack integration | Free |
| Server (backend) | $20–50 |
| **Total** | **~$50–100/month** |

---

## Conclusion

**This is the ONLY approach that will deliver what your client wants:**

✅ User profiles + personalization  
✅ Chat history retrieval  
✅ Appointment tracking  
✅ Returning user recognition  
✅ Professional notifications  

**Other options (email-only, simple database) won't meet these needs.**

**Recommendation: Implement OPTION D (Complete System) - It's worth the effort and will unlock all personalization features your client requires.**

