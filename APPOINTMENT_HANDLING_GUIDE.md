# Aueshah Concierge — Appointment Handling Guide

**Date**: 2026-04-16  
**Purpose**: Clarify how the bot handles appointment requests from clients

---

## 🚨 CRITICAL RULE

**The bot CANNOT book or arrange appointments itself.**

The bot has NO access to:
- Calendar systems
- Email servers
- CRM/booking databases
- Confirmation systems

Therefore, the bot must NOT say:
- ❌ "I'll book your appointment"
- ❌ "Let me arrange a meeting for you"
- ❌ "I'll send you a calendar invite"
- ❌ "You're booked for 3pm tomorrow"

---

## ✅ CORRECT APPOINTMENT FLOW

### Step 1: Client Expresses Interest
```
Client: "I'd love to have a virtual appointment with your team"
```

### Step 2: Bot Acknowledges (Warmly, No Promise)
```
Bot: "I'd be delighted to help arrange that for you. To get you connected with our concierge team, 
I'll need your email address. What's the best email to reach you?"
```

**Key phrases (CORRECT)**:
- "I'd be happy to have our team reach out"
- "Our concierge will contact you"
- "I'll make sure our team knows you're interested"
- "Let me get your contact info so our team can follow up"

**Key phrases (WRONG - DON'T USE)**:
- "I'll book your appointment" ❌
- "I'm arranging that for you" ❌
- "You're scheduled for..." ❌
- "I'm sending you a confirmation" ❌

### Step 3: Bot Collects Contact Info
```
Bot: "What's the best email to reach you?"

Client: "my.email@example.com"

Bot: "Perfect! And would you like to provide a phone number as well?"

Client: "555-123-4567"

Bot: "Great! Is there a preferred date or time you'd like to meet?"

Client: "Next Tuesday afternoon"
```

### Step 4: Bot Confirms and Sets Expectations
```
Bot: "Wonderful! I've captured your information. Our concierge team will reach out 
to you at my.email@example.com within 24 hours to confirm your appointment. 
Thank you for choosing Aueshah!"
```

### Step 5: Backend Captures Request
- Endpoint: `POST /appointment-request`
- Data collected: email, phone, appointment_type, preferred_date, notes
- System logs request with unique reference ID
- Response to client includes reference ID for tracking

### Step 6: Behind the Scenes
```
Concierge team receives:
- Reference ID: APT-A1B2C3D4
- Client email: my.email@example.com
- Client phone: 555-123-4567
- Appointment type: virtual
- Preferred date: Next Tuesday afternoon
- Timestamp: 2026-04-16 15:32:00 UTC

Action: Concierge team contacts client within 24 hours to:
- Confirm availability
- Finalize date/time
- Send calendar invite
- Answer any questions
```

---

## 📋 APPOINTMENT TYPES

When capturing appointment requests, classify into one of these types:

| Type | Description | Example |
|------|-------------|---------|
| **virtual** | Remote video/phone consultation | "I'd like a video call" |
| **in-person** | Private salon appointment | "Can I visit your salon?" |
| **bespoke** | Custom design consultation | "I want to create a custom ring" |
| **general** | General inquiry/support | "I have questions about warranty" |

---

## 🔧 HOW THE SYSTEM WORKS

### For the Bot
1. When client requests appointment, bot recognizes keyword ("meet", "appointment", "virtual call", "visit")
2. Bot offers to "connect" them with concierge (no booking promise)
3. Bot asks for contact info (email required, phone optional)
4. Bot calls backend endpoint `/appointment-request` with collected info
5. Backend returns confirmation with reference ID
6. Bot shows confirmation to client

### For the Concierge Team
1. Appointment request appears in system (logged to database/Slack/CRM)
2. Concierge team manually reaches out within 24 hours
3. Confirms availability and schedules
4. Sends calendar invite (via email, Calendly, Google Meet, Zoom, etc.)
5. Updates CRM with appointment details

### For the Client
1. Gets warm acknowledgment from bot
2. Provided with reference ID (APT-XXXXXXXX) for tracking
3. Receives email from concierge team within 24 hours
4. Gets calendar invite and meeting link

---

## 💬 CONVERSATION TEMPLATES

### Template 1: Virtual Appointment Request

```
Client: "Can I schedule a virtual meeting?"

Bot: "Absolutely! I'd love to arrange that for you. Our concierge team conducts virtual 
appointments at your convenience. To get you connected, I'll need a couple of details. 
What's your email address?"

Client: "sarah@email.com"

Bot: "Perfect, Sarah! And if you'd like, a phone number where we can reach you?"

Client: "I'll just use email for now"

Bot: "Great! Is there a preferred day or time?"

Client: "Sometime next week, weekday afternoon"

Bot: "Wonderful. I've got everything I need. Your appointment request (Ref: APT-X7K9P2M1) 
has been submitted. Our concierge team will reach out to sarah@email.com within 24 hours 
to confirm the best time for your virtual meeting. Thank you!"
```

### Template 2: Bespoke Design Consultation

```
Client: "I want to create a custom piece"

Bot: "How wonderful! Custom design is one of our most cherished services. Our atelier team 
will work with you personally to bring your vision to life. I'd like to connect you with 
our concierge so they can schedule a consultation. What's the best email to reach you?"

Client: "michael@company.com"

Bot: "Thank you! And your phone number, if you have one?"

Client: "555-987-6543"

Bot: "Perfect! Any specific thoughts about what you'd like to create?"

Client: "A diamond engagement ring in white gold"

Bot: "Beautiful! I've submitted your bespoke design inquiry (Ref: APT-K8L2N5P0). 
Our atelier concierge will contact you within 24 hours to discuss your vision and 
schedule a detailed consultation. We're excited to create something extraordinary for you!"
```

### Template 3: In-Person Salon Visit

```
Client: "Can I visit your salon?"

Bot: "Of course! We'd love to welcome you to our private salon. You can experience 
our pieces in person and consult with our team. To arrange a visit, I'll need your 
contact information. What's your email?"

Client: "visit@myemail.com"

Bot: "Perfect! And a phone number?"

Client: "+1-555-123-4567"

Bot: "Lovely! When were you thinking of visiting?"

Client: "Friday or Saturday next week"

Bot: "Wonderful. Your salon visit request (Ref: APT-M3N6Q9T1) has been registered. 
Our concierge team will call you at +1-555-123-4567 within 24 hours to confirm your 
preferred date and time. We look forward to meeting you!"
```

---

## 🚀 API Usage

### Endpoint: POST /appointment-request

**Request Example**:
```json
{
  "email": "client@example.com",
  "phone": "+1-555-123-4567",
  "appointment_type": "virtual",
  "preferred_date": "Next Tuesday afternoon",
  "notes": "Interested in Noor Collection, have some questions about sizing"
}
```

**Response Example**:
```json
{
  "status": "success",
  "message": "Thank you! We've received your request (Ref: APT-A1B2C3D4). Our concierge team will contact you at client@example.com within 24 hours to confirm your appointment.",
  "reference_id": "APT-A1B2C3D4"
}
```

---

## ⚠️ WHAT NOT TO DO

### ❌ Broken Promises
```
DON'T SAY: "I'm booking you for Tuesday at 2pm"
BOT CANNOT: Access calendar, send invites, confirm availability

DO SAY: "Our concierge will contact you within 24 hours to find the perfect time"
```

### ❌ Over-Committing
```
DON'T SAY: "I'll have the atelier prepare samples for you"
BOT CANNOT: Arrange production, curate samples, set expectations

DO SAY: "Our atelier will discuss options when they contact you"
```

### ❌ Partial Information
```
DON'T SAY: "You're all set for Tuesday"
BOT SHOULD: Collect both email AND appointment type

ALWAYS: Get email (required), phone (optional), appointment type, notes
```

---

## 🎯 SUCCESS CRITERIA

An appointment request is handled correctly when:

✅ Bot acknowledges interest warmly (no hard promise)  
✅ Bot collects email address (required)  
✅ Bot collects optional details (phone, date, notes)  
✅ Bot provides reference ID to client  
✅ Client is told concierge will contact within 24 hours  
✅ Backend logs appointment request  
✅ Concierge team receives notification  
✅ Concierge contacts client within 24 hours  

---

## 🔄 FLOW DIAGRAM

```
User Expression of Interest
        ↓
Bot Recognizes Appointment Intent
        ↓
Bot Offers to Connect (Warm, No Promise)
        ↓
Bot Asks for Email (Required)
        ↓
Bot Asks for Phone (Optional)
        ↓
Bot Asks for Preferred Date/Time (Optional)
        ↓
Bot Asks for Additional Notes (Optional)
        ↓
Bot Calls /appointment-request Endpoint
        ↓
Backend Logs Request + Generates Reference ID
        ↓
Backend Returns Confirmation
        ↓
Bot Shows Confirmation to Client
        ↓
Concierge Team Receives Notification
        ↓
Concierge Contacts Client Within 24 Hours
        ↓
Appointment Confirmed & Scheduled
```

---

## 📞 CONTACT INFO FOR CONCIERGE

When giving clients fallback contact info:

```
Email: service@aueshah.com
Phone: +1 (937) 909-1432
Website: https://aueshah.com/virtual-appointments
```

---

## 🆘 TROUBLESHOOTING

### Issue: Client Says "The Bot Promised Me an Appointment"
**Response**: "I apologize for any confusion. Our concierge team will still reach out within 24 hours. 
I should have been clearer that I was having them contact you to schedule (not booking directly). 
Is there anything else I can help clarify?"

### Issue: Client Never Hears from Concierge
**Cause**: Appointment request not logged, or concierge missed notification  
**Fix**: 
1. Verify `/appointment-request` endpoint logged the request
2. Check concierge notification system (Slack, email, CRM)
3. Have concierge manually search for client email
4. Concierge proactively reaches out

### Issue: Bot Tries to Book Direct
**Cause**: Bot prompt is incorrectly written  
**Fix**: Review bot prompts in `prompts.py`, ensure language says "I'll have our team contact you"

---

## Summary

**The Golden Rule**: The bot is a warm, knowledgeable guide who recognizes when a client wants to meet the team. The bot's job is to **hand off gracefully** by collecting contact information and connecting the client with the concierge team—never to book appointments itself.

