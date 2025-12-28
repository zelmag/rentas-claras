# 📞 CitaYa — Product Requirements Document

> **"La IA que agenda por ti"**
>
> An Elite AI Concierge for Appointments & Reservations in Monterrey's Premium Market

---

## Document Information

| Field | Value |
|-------|-------|
| **Product Name** | CitaYa |
| **Version** | 1.0 |
| **Last Updated** | December 25, 2024 |
| **Author** | Zelma Garza |
| **Status** | Draft |
| **Target Market** | San Pedro Garza García / Monterrey Metropolitan Area |

---

## 📋 Executive Summary

### The Opportunity

**CitaYa** is an elite AI-powered concierge service designed for the high-paced, high-service environment of San Pedro Garza García and greater Monterrey. In a market where time is the ultimate luxury, CitaYa eliminates the friction of booking appointments by making phone calls and sending WhatsApp messages on behalf of users.

### The Problem

Monterrey's affluent professionals face a paradox: they demand premium services but lack time to book them. Many high-end establishments in San Pedro—from exclusive restaurants in Centrito Valle to luxury spas in Valle Oriente—still operate via phone reservations or WhatsApp. This creates friction:

- **45-second to 5-minute phone calls** for a simple reservation
- **Back-and-forth WhatsApp threads** negotiating availability
- **Missed calls and voicemails** during business hours
- **Language switching** between staff who speak Spanish, English, or both

### The Solution

CitaYa is an AI voice agent that:
1. **Calls businesses** on the user's behalf using natural Mexican Spanish
2. **Negotiates availability** ("¿A las 3? No hay. ¿A las 4? Perfecto.")
3. **Confirms via WhatsApp** sending the user an instant confirmation
4. **Syncs to calendar** adding the appointment to Google Calendar

### Why Now?

| Factor | Opportunity |
|--------|-------------|
| **ElevenLabs maturity** | Conversational AI now supports natural Mexican Spanish with low latency |
| **WhatsApp penetration** | 95%+ of MTY businesses use WhatsApp; API now accessible |
| **Post-COVID behavior** | Users accustomed to digital-first interactions |
| **Market gap** | No localized solution exists for Mexican market |

### Success Metrics (North Star)

| Metric | Target (6 months) |
|--------|------------------|
| **Successful bookings/month** | 1,000+ |
| **Booking success rate** | >85% |
| **User retention (monthly)** | >60% |
| **NPS** | >50 |

---

## 👥 User Personas

### Persona 1: The Busy Consultant ("El Consultor")

> *"No tengo tiempo ni para hacer una llamada de 2 minutos."*

| Attribute | Description |
|-----------|-------------|
| **Name** | Rodrigo, 34 |
| **Occupation** | Strategy Consultant at McKinsey/Deloitte |
| **Location** | Lives in Valle Poniente, works in Valle Oriente |
| **Income** | $80,000+ MXN/month |
| **Tech Savvy** | High — uses Notion, Calendly, multiple productivity apps |
| **Language** | Bilingual (Spanish/English), code-switches constantly |

**A Day in Rodrigo's Life:**
- 7:00 AM — Gym at Sports World (needs to book personal trainer)
- 8:30 AM — Back-to-back client calls until 1pm
- 1:30 PM — Lunch at Sonora Grill (needs reservation)
- 2:30 PM — Meetings until 7pm
- 7:30 PM — Dinner with wife at Pangea (needs reservation)
- 9:00 PM — Finally has time to call the barbershop... but it's closed

**Pain Points:**
- Never has time during business hours to make personal calls
- Forgets to book things until it's too late
- Hates the inefficiency of phone tag
- Wife asks him to book things, he forgets, domestic tension ensues

**Jobs to Be Done:**
- Book restaurant reservations for client dinners
- Schedule personal grooming (barber, car detailing)
- Manage family appointments (pediatrician, vet)

**Quote:**
> "If I could delegate every phone call in my life, I would. That's what assistants are for—but my company doesn't give me one for personal stuff."

---

### Persona 2: The Sanpetrino Family Coordinator ("La Coordinadora")

> *"Soy la que organiza todo para toda la familia."*

| Attribute | Description |
|-----------|-------------|
| **Name** | Mariana, 42 |
| **Occupation** | CFO at family business / Full-time family manager |
| **Location** | Lives in Carrizalejo, kids go to school in San Pedro |
| **Income** | Household $200,000+ MXN/month |
| **Tech Savvy** | Medium — WhatsApp power user, less comfortable with new apps |
| **Language** | Spanish-dominant, comfortable in English |

**Mariana's Coordination Load:**
- Husband's medical appointments (cardiólogo, dentista)
- 3 kids' activities (ballet, fútbol, tutoring)
- Household services (plumber, electrician, fumigation)
- Personal care (salón, spa, dermatólogo)
- Social obligations (restaurant reservations for family gatherings)

**Pain Points:**
- Spends 30+ minutes/week on phone calls for appointments
- Keeps track of everything in WhatsApp chats (chaos)
- Family members ask her to book things constantly
- Some businesses don't answer, require multiple attempts

**Jobs to Be Done:**
- Book all family medical/dental appointments
- Coordinate household maintenance services
- Reserve restaurants for extended family gatherings (10+ people)
- Schedule personal wellness appointments

**Quote:**
> "Todo mundo me pregunta '¿ya hiciste la cita?' como si fuera mi única responsabilidad. Pues sí, pero tengo 50 citas que hacer."

---

### Persona 3: The Regio Abroad ("La Diaspora")

> *"Quiero mantener mi vida en Monterrey aunque vivo en Londres."*

| Attribute | Description |
|-----------|-------------|
| **Name** | Zelma, 29 |
| **Occupation** | Software Engineer at Big Tech |
| **Location** | Lives in London, family in San Pedro |
| **Income** | £80,000+ GBP/year |
| **Tech Savvy** | Very high — early adopter |
| **Language** | Fully bilingual, thinks in Spanglish |

**Pain Points:**
- Can't call Monterrey businesses during UK business hours (time zone)
- Wants to book things for visits home (salon, restaurants, doctor)
- Parents need help booking things (tech-averse)
- WhatsApp threads with businesses get lost

**Jobs to Be Done:**
- Book appointments for when she visits home
- Help parents book their appointments remotely
- Reserve restaurants for family gatherings during visits

---

## 🗣️ Language & Localization (Critical)

### Bilingual Capability

CitaYa must handle the **Spanglish reality** of San Pedro Garza García, where code-switching between Spanish and English is the norm.

| Scenario | Example | AI Behavior |
|----------|---------|-------------|
| **User speaks Spanish** | "Agenda una cita para el sábado" | Respond in Spanish, call in Spanish |
| **User speaks English** | "Book me a haircut Saturday" | Respond in English, call in Spanish (businesses speak Spanish) |
| **User code-switches** | "Agenda un appointment para Saturday" | Understand both, respond in user's dominant language |
| **Business speaks English** | High-end restaurants may answer in English | AI adapts to business's language |

### Tone & Register

| Context | Register | Example |
|---------|----------|---------|
| **Calling businesses** | Formal (Usted) | "Buenas tardes, ¿tendría disponibilidad para el sábado?" |
| **High-end restaurants** | Formal + Elevated | "Buenas noches, llamo para solicitar una reservación..." |
| **Casual businesses** | Formal but warm | "Buenas tardes, ¿me podría agendar un corte para el sábado?" |
| **Responding to user** | Friendly, efficient | "Listo, te agendé a las 4pm. ¿Te mando el recordatorio?" |

**Key Linguistic Guidelines:**

1. **Always use "Usted" with businesses** — Never "tú" on first contact
2. **Avoid Peninsular Spanish** — No "vale", "tío", "vosotros"
3. **Avoid Caribbean accent** — No heavy Dominican/Cuban inflection
4. **Embrace Regiomontano markers** — Natural "ándale", "órale", "mande" where appropriate
5. **Handle "¿Mande?"** — Common in Mexico, means "pardon?" — AI should repeat naturally

### Regional Formats

| Format | Standard | Example |
|--------|----------|---------|
| **Time** | 12-hour with AM/PM | "4:30 PM" not "16:30" |
| **Date** | DD/MM/YYYY | "25/12/2024" not "12/25/2024" |
| **Phone** | +52 81 XXXX XXXX | Ten digits with 81 area code |
| **Currency** | MXN with $ | "$500 pesos" |
| **Address** | Colonia-centric | "En la colonia Del Valle" |

### Voice Profile Requirements (ElevenLabs)

| Parameter | Requirement |
|-----------|-------------|
| **Accent** | Neutral Latin American Spanish or light Northern Mexico (Regiomontano) |
| **Gender** | Offer both masculine and feminine voice options |
| **Tone** | Professional, warm, confident—like a high-end concierge |
| **Avoid** | Peninsular Spanish (Spain), heavy Caribbean, robotic monotone |
| **Model** | `eleven_multilingual_v2` |
| **Stability** | 0.5 (natural variation) |
| **Similarity Boost** | 0.75 (consistent but not rigid) |

**Voice Selection Criteria:**
- Test with native Regiomontanos for authenticity
- Should sound like a well-educated young professional from San Pedro
- Friendly but not overly casual

---

## ⚙️ Functional Requirements

### FR-1: Core Booking Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER JOURNEY                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. USER REQUEST                                                │
│     "Reserva en Pangea para el sábado a las 8, somos 4"        │
│                           │                                     │
│                           ▼                                     │
│  2. AI PARSES INTENT                                           │
│     • Venue: Pangea (lookup phone number)                      │
│     • Date: Saturday (resolve to DD/MM/YYYY)                   │
│     • Time: 8:00 PM                                            │
│     • Party size: 4 people                                     │
│     • Name: [User's name from profile]                         │
│                           │                                     │
│                           ▼                                     │
│  3. AI CALLS BUSINESS                                          │
│     📞 Calling +52 81 8356 7890...                             │
│     "Buenas noches, llamo para hacer una reservación           │
│      para el sábado a las 8 de la noche, somos 4 personas,     │
│      a nombre de Rodrigo Garza."                               │
│                           │                                     │
│                           ▼                                     │
│  4. NEGOTIATION (if needed)                                    │
│     Business: "A las 8 ya está lleno, ¿le parece a las 8:30?" │
│     AI: "Déjeme confirmar... Sí, 8:30 está bien."             │
│                           │                                     │
│                           ▼                                     │
│  5. CONFIRMATION                                                │
│     AI reports to user: "Listo, te reservé a las 8:30pm.       │
│     ¿Te mando confirmación por WhatsApp?"                      │
│                           │                                     │
│                           ▼                                     │
│  6. WHATSAPP CONFIRMATION                                      │
│     📱 WhatsApp message sent to user with:                     │
│     • Venue name, address, phone                               │
│     • Date/time confirmed                                      │
│     • Party size                                               │
│     • "Responde CANCELAR para cancelar"                        │
│                           │                                     │
│                           ▼                                     │
│  7. CALENDAR SYNC                                              │
│     📅 Google Calendar event created                           │
│     • Title: "Cena en Pangea"                                  │
│     • Time: 8:30 PM                                            │
│     • Location: Address with Google Maps link                  │
│     • Reminder: 2 hours before                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### FR-2: Supported Booking Types

| Type | Priority | Complexity | Data Required |
|------|----------|------------|---------------|
| **Restaurant reservation** | P0 (MVP) | Low | Date, time, party size, name |
| **Haircut/Barbershop** | P0 (MVP) | Low | Date, time, service type, stylist (optional) |
| **Spa/Facial/Massage** | P1 | Medium | Date, time, service type, therapist (optional) |
| **Doctor/Dentist** | P1 | Medium | Date, time, reason for visit, insurance |
| **Car service (detailing, wash)** | P1 | Medium | Date, time, service type, car model |
| **Vet appointment** | P2 | Medium | Date, time, pet name, reason |
| **Household services** | P2 | High | Date, time window, service description, address |

### FR-3: WhatsApp Integration

**Post-Call Confirmation Message:**

```
📅 *Cita Confirmada*

📍 *Pangea*
🗓️ Sábado 28/12/2024
🕐 8:30 PM
👥 4 personas
📞 +52 81 8356 7890
📍 Calzada del Valle 400, Del Valle, San Pedro

Responde:
• CANCELAR - para cancelar la cita
• CAMBIAR - para modificar fecha/hora

— CitaYa 🤖
```

**Technical Implementation:**
- Use Twilio WhatsApp Business API or official WhatsApp Business API
- Fallback to SMS if WhatsApp delivery fails
- Support inbound messages (CANCELAR, CAMBIAR) for modifications

### FR-4: Favorite Venues ("Mis Lugares")

Users can save frequently visited businesses:

| Field | Required | Example |
|-------|----------|---------|
| **Name** | Yes | "Mi barbero" |
| **Business Name** | Yes | "Barbería Don Pepe" |
| **Phone Number** | Yes | +52 81 1234 5678 |
| **Category** | Yes | Barbershop |
| **Default preferences** | No | "Siempre con Carlos", "Corte clásico" |
| **Address** | No | Av. Vasconcelos 456, Del Valle |

### FR-5: Smart Scheduling

| Feature | Description |
|---------|-------------|
| **Relative dates** | "el sábado", "mañana", "la próxima semana" → resolve to DD/MM/YYYY |
| **Time preferences** | "en la tarde" → 2-6 PM, "en la mañana" → 9 AM-12 PM |
| **Availability windows** | "entre 3 y 5" → AI negotiates within window |
| **Recurring bookings** | "cada 3 semanas" → schedule series (P2) |

### FR-6: Call Recording & Transcription

| Feature | Purpose |
|---------|---------|
| **Full call recording** | Quality assurance, dispute resolution |
| **Real-time transcription** | Show user what's being said |
| **Summary generation** | "Llamé a Pangea. Reservé para 4 personas el sábado 28 a las 8:30pm." |
| **Failure logging** | If booking fails, log reason for improvement |

---

## 🎯 Use Cases

### UC-1: Restaurant Reservation at High-End Venue

**Scenario:** Rodrigo wants to book dinner at Sonora Grill Prime in Centrito Valle for a client dinner.

**User Input:**
> "Reserva en Sonora Grill Prime para el jueves a las 2pm, somos 6, es comida de negocios"

**AI Actions:**
1. Look up Sonora Grill Prime (Centrito Valle location)
2. Call +52 81 XXXX XXXX
3. Request: "Buenas tardes, quisiera hacer una reservación para el jueves a las 2 de la tarde. Somos 6 personas y es una comida de negocios, si fuera posible una mesa privada o en zona tranquila."
4. Negotiate if needed (time, availability)
5. Confirm name: "A nombre de Rodrigo Garza"
6. Report back + WhatsApp confirmation

**Success Criteria:**
- Reservation confirmed within single call
- Special request (quiet table) communicated
- User receives confirmation within 2 minutes

---

### UC-2: Haircut at Preferred Barbershop

**Scenario:** Rodrigo needs a haircut but his barber is in high demand.

**User Input:**
> "Agenda corte con Carlos en Don Pepe para el sábado, cualquier hora en la mañana"

**AI Actions:**
1. Look up "Don Pepe" from user's favorites
2. Call barbershop
3. Request: "Buenos días, llamo para agendar un corte con Carlos para el sábado en la mañana. ¿Qué horarios tiene disponibles?"
4. Business: "Con Carlos tengo 10:30 o 12"
5. AI: "El de las 10:30 por favor. A nombre de Rodrigo."
6. Confirm + WhatsApp + Calendar

**Success Criteria:**
- AI knows to ask for specific stylist (Carlos)
- Negotiates within "mañana" window
- Confirms preferred option

---

### UC-3: Service Appointment (Car Detailing)

**Scenario:** Mariana needs to schedule car detailing at a shop in Valle Oriente.

**User Input:**
> "Agenda detallado completo para mi camioneta en Car Wash Premium, el lunes que tengo libre"

**AI Actions:**
1. Look up Car Wash Premium
2. Call business
3. Request: "Buenos días, quisiera agendar un detallado completo para una camioneta el lunes. ¿Qué horarios manejan?"
4. Business: "¿Qué modelo de camioneta? El detallado completo toma como 4 horas"
5. AI: "Es una Suburban. ¿A qué hora me recomiendan llegar?"
6. Negotiate time, confirm

**Complexity:** Business asks clarifying questions → AI must handle multi-turn conversation

---

### UC-4: Doctor Appointment with Insurance

**Scenario:** Mariana needs to book a cardiology appointment for her husband.

**User Input:**
> "Agenda con el cardiólogo Dr. Martínez para mi esposo Roberto, tiene GNP, para revisión anual"

**AI Actions:**
1. Look up Dr. Martínez (from favorites or directory)
2. Call medical office
3. Request: "Buenos días, llamo para agendar una cita con el Dr. Martínez para revisión cardiológica. El paciente es Roberto Garza, maneja seguro GNP."
4. Handle: "¿Es primera vez?" → "No, es paciente recurrente, revisión anual."
5. Handle: "¿Qué día le acomoda?" → Negotiate availability
6. Confirm appointment details

**Complexity:**
- Third-party booking (for husband)
- Insurance information required
- Medical context requires professionalism

---

### UC-5: Group Restaurant Reservation (Extended Family)

**Scenario:** Mariana is organizing Sunday lunch for 15 family members.

**User Input:**
> "Reserva para 15 personas el domingo a las 2 en El Gran Pastor, es cumpleaños de mi suegra, si tienen salón privado mejor"

**AI Actions:**
1. Look up El Gran Pastor
2. Call restaurant
3. Request: "Buenas tardes, llamo para hacer una reservación para 15 personas el domingo a las 2 de la tarde. Es un cumpleaños, entonces si tuvieran algún salón privado o área especial sería ideal."
4. Handle: "Para 15 personas necesito cobrar un mínimo de consumo" → Report to user
5. Handle: "¿Van a querer pastel?" → "Déjeme confirmar con la familia"
6. Partial confirmation, flag follow-up needed

**Complexity:**
- Large party requires special handling
- Multiple questions from business
- May require user input before final confirmation

---

## ⚠️ Edge Cases

### EC-1: Loud Background Noise

**Scenario:** Business answers but there's loud noise (traffic, kitchen, music)

| Situation | AI Behavior |
|-----------|-------------|
| Can't hear response | "Disculpe, no le escuché bien. ¿Me podría repetir?" |
| Partial understanding | "¿Me dijo que a las 4 sí hay espacio?" (confirm understanding) |
| Persistent noise | Speak slightly slower, clearer; increase volume |
| Complete failure | "Hay mucha interferencia, ¿le puedo llamar en 5 minutos?" |

### EC-2: Interrupted/Dropped Calls

**Scenario:** Call drops mid-conversation

| Situation | AI Behavior |
|-----------|-------------|
| Call drops before confirmation | Retry call immediately (max 2 retries) |
| Call drops after apparent confirmation | Call back to verify: "Disculpe, se cortó la llamada. ¿Me confirma que quedó la reservación para las 8?" |
| Business puts on hold then drops | Wait 30 seconds, retry, report to user if fails |
| User gets notification | "La llamada se cortó. Volviendo a llamar..." |

### EC-3: Business Says "Call Back Later"

**Scenario:** "Ahorita estamos muy ocupados, ¿puede llamar en una hora?"

| AI Behavior |
|-------------|
| "Claro, le llamo en una hora. Gracias." |
| Schedule retry for 1 hour later |
| Notify user: "El restaurante está ocupado, volveré a llamar a las 3pm" |

### EC-4: No Answer / Voicemail

**Scenario:** Business doesn't pick up after 5 rings

| Attempt | AI Behavior |
|---------|-------------|
| 1st no answer | Retry in 15 minutes |
| 2nd no answer | Retry in 30 minutes |
| 3rd no answer | Notify user: "No contestan en Pangea. ¿Quieres que intente por WhatsApp?" |
| Voicemail | Leave message: "Buenas tardes, llamo para hacer una reservación para el sábado. Por favor, si me pueden confirmar disponibilidad al [callback number]. Gracias." |

### EC-5: Business Asks Unexpected Questions

**Scenario:** Questions AI wasn't prepared for

| Question | AI Response |
|----------|-------------|
| "¿Mesa adentro o en terraza?" | "Adentro, por favor" (default) OR ask user in real-time |
| "¿Van a querer valet parking?" | "Sí, por favor" (default) OR "Déjeme confirmar" |
| "¿Tiene el número del paciente?" | "El teléfono es [user's phone]" |
| "¿De parte de quién?" | "[User's name]" |
| Unknown question | "Déjeme confirmar eso y le llamo de regreso" |

### EC-6: Booking Fails

**Scenario:** No availability for requested time/date

| Situation | AI Behavior |
|-----------|-------------|
| No availability at requested time | "¿Qué otros horarios tienen disponibles?" → Offer alternatives |
| Fully booked that day | Report to user: "No hay disponibilidad el sábado. ¿Quieres que intente el domingo?" |
| Business is closed | Report: "Pangea está cerrado los lunes. ¿Otro día?" |
| Requires deposit | Report: "Piden un depósito de $500 para grupos grandes. ¿Procedo?" |

---

## 🔐 Security & Privacy

### Compliance: Ley Federal de Protección de Datos Personales (LFPDPPP)

CitaYa must comply with Mexico's federal data protection law.

| Requirement | Implementation |
|-------------|----------------|
| **Aviso de Privacidad** | Clear privacy notice at signup, explaining data usage |
| **Consent** | Explicit consent before making calls on user's behalf |
| **Data minimization** | Only collect necessary data (name, phone, preferences) |
| **Access rights** | Users can request all their data (ARCO rights) |
| **Deletion rights** | Users can delete account and all associated data |
| **Data security** | Encryption at rest and in transit |
| **Third-party disclosure** | Clear about data shared with ElevenLabs, Twilio, etc. |

### Call Recording Consent

| Party | Consent Mechanism |
|-------|-------------------|
| **User** | Agrees at signup that calls are recorded |
| **Business** | AI announces at start: "Esta llamada puede ser grabada para calidad del servicio" |

**Note:** Under Mexican law, one-party consent is generally sufficient, but disclosure is best practice.

### Data Stored

| Data Type | Retention | Encryption |
|-----------|-----------|------------|
| User profile | Until deletion | AES-256 |
| Call recordings | 30 days | AES-256 |
| Transcripts | 90 days | AES-256 |
| Booking history | 1 year | AES-256 |
| Payment info | PCI compliant, tokenized | Stripe/PayPal |

### Security Measures

| Measure | Description |
|---------|-------------|
| **Authentication** | OAuth (Google, Apple) + optional phone verification |
| **API security** | Rate limiting, JWT tokens, HTTPS only |
| **Phone number verification** | Verify user owns the phone number before calling on their behalf |
| **Abuse prevention** | Limit calls per user per day, detect spam patterns |

---

## 🏗️ Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CITAYA ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         CLIENT LAYER                             │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │   iOS App   │  │ Android App │  │      Web App (PWA)      │  │   │
│  │  │  (React     │  │  (React     │  │       Next.js 14        │  │   │
│  │  │   Native)   │  │   Native)   │  │                         │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         API LAYER                                │   │
│  │                     Next.js API Routes                           │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │   │
│  │  │ /api/booking │ │ /api/venues  │ │     /api/calls           │ │   │
│  │  │   • create   │ │   • search   │ │  • initiate              │ │   │
│  │  │   • cancel   │ │   • favorites│ │  • status                │ │   │
│  │  │   • modify   │ │   • add      │ │  • transcript            │ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     ORCHESTRATION LAYER                          │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │               Booking Agent (LLM-powered)                 │   │   │
│  │  │  • Parse user intent                                      │   │   │
│  │  │  • Generate conversation script                           │   │   │
│  │  │  • Handle multi-turn negotiation                          │   │   │
│  │  │  • Decide when to escalate to user                        │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│          ┌─────────────────────────┼─────────────────────────┐         │
│          ▼                         ▼                         ▼         │
│  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐      │
│  │  ElevenLabs  │        │    Twilio    │        │   WhatsApp   │      │
│  │  ┌────────┐  │        │  ┌────────┐  │        │   Business   │      │
│  │  │  TTS   │  │        │  │ Voice  │  │        │     API      │      │
│  │  │        │  │        │  │  API   │  │        │              │      │
│  │  ├────────┤  │        │  ├────────┤  │        │  ┌────────┐  │      │
│  │  │Convers.│  │        │  │  SMS   │  │        │  │Messages│  │      │
│  │  │  AI    │  │        │  │        │  │        │  │        │  │      │
│  │  └────────┘  │        │  └────────┘  │        │  └────────┘  │      │
│  └──────────────┘        └──────────────┘        └──────────────┘      │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         DATA LAYER                               │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │   │
│  │  │   Supabase   │ │    Redis     │ │      Google APIs         │ │   │
│  │  │  (Postgres)  │ │   (Cache)    │ │  • Calendar              │ │   │
│  │  │  • Users     │ │  • Sessions  │ │  • Maps (addresses)      │ │   │
│  │  │  • Venues    │ │  • Rate      │ │                          │ │   │
│  │  │  • Bookings  │ │    limits    │ │                          │ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14 + React Native | Code sharing, SSR, PWA support |
| **API** | Next.js API Routes | Unified backend, serverless |
| **LLM** | OpenAI GPT-4 / Claude | Intent parsing, conversation logic |
| **Voice AI** | ElevenLabs Conversational AI | Best-in-class latency, Spanish support |
| **Telephony** | Twilio Voice API | Reliable Mexico phone numbers |
| **Messaging** | Twilio WhatsApp / WhatsApp Business API | User confirmations |
| **Database** | Supabase (Postgres) | Real-time, auth built-in |
| **Calendar** | Google Calendar API | Most used in target market |
| **Hosting** | Vercel | Easy deployment, edge functions |

---

## 💰 Business Model

### Pricing Tiers

| Tier | Price (MXN) | Bookings/Month | Features |
|------|-------------|----------------|----------|
| **Free** | $0 | 3 | Basic booking, WhatsApp confirmation |
| **Pro** | $149/month | 20 | + Calendar sync, priority calling |
| **Unlimited** | $349/month | Unlimited | + Family accounts, call recordings |
| **Family** | $499/month | Unlimited (5 users) | For household coordinators |

### Unit Economics

| Metric | Estimate |
|--------|----------|
| **Cost per call** | ~$0.15-0.25 (Twilio + ElevenLabs) |
| **Avg calls per booking** | 1.3 (accounting for retries) |
| **Cost per booking** | ~$0.30 |
| **Free tier cost** | 3 × $0.30 = $0.90/user/month |
| **Pro tier margin** | $149 - (20 × $0.30) = $143 |

### Revenue Projections (Year 1)

| Month | Users | Paid % | MRR (MXN) |
|-------|-------|--------|-----------|
| 3 | 200 | 5% | $1,490 |
| 6 | 1,000 | 10% | $14,900 |
| 12 | 5,000 | 15% | $111,750 |

---

## 📅 Roadmap

### Phase 0: Foundation (Weeks 1-2)
- [ ] Project setup (Next.js, Supabase, Twilio, ElevenLabs)
- [ ] Basic user auth (Google OAuth)
- [ ] Phone number verification
- [ ] Simple booking request form

### Phase 1: MVP - Restaurants (Weeks 3-4)
- [ ] Restaurant booking flow
- [ ] ElevenLabs voice integration
- [ ] Twilio outbound calling
- [ ] Basic conversation handling
- [ ] WhatsApp confirmation messages
- [ ] Test with 5 real restaurants

### Phase 2: Salons & Services (Weeks 5-6)
- [ ] Salon/barbershop booking flow
- [ ] Stylist preferences
- [ ] "Mis Lugares" (favorites) feature
- [ ] Google Calendar integration
- [ ] Call recording and transcription

### Phase 3: Polish & Launch (Weeks 7-8)
- [ ] Edge case handling (noise, drops, retries)
- [ ] User onboarding flow
- [ ] Pricing/subscription (Stripe)
- [ ] Landing page
- [ ] Beta launch with friends & family

### Phase 4: Expansion (Weeks 9-12)
- [ ] Doctor/medical appointments
- [ ] Household services
- [ ] Multi-user family accounts
- [ ] React Native mobile apps
- [ ] OpenTable integration (for restaurants that support it)

---

## 📊 Success Metrics

### MVP Success Criteria (Week 8)

| Metric | Target |
|--------|--------|
| Successful restaurant bookings | 20+ |
| Successful salon bookings | 10+ |
| Booking success rate | >70% |
| Friends & family active users | 10+ |
| Average booking time | <3 minutes |

### Growth Metrics (Month 6)

| Metric | Target |
|--------|--------|
| Monthly Active Users | 1,000 |
| Bookings per month | 3,000 |
| Paid conversion rate | 10% |
| User retention (monthly) | 60% |
| NPS | >50 |

---

## 🚨 Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Businesses hang up on AI** | Medium | High | Sound extremely natural; lead with value ("tengo una reservación") |
| **High Twilio/ElevenLabs costs** | Medium | Medium | Aggressive caching, call length limits, tiered pricing |
| **WhatsApp API approval slow** | Medium | Low | Use Twilio WhatsApp as fallback |
| **Mexican Spanish voice quality** | Low | High | Extensive testing, voice cloning as backup |
| **Legal issues with AI calling** | Low | High | Clear disclosures, user consent, legal review |
| **Low adoption** | Medium | High | Start with friends/family, iterate on value prop |

---

## 📎 Appendix

### A. Sample Conversation Scripts

**Restaurant (Simple):**
```
AI: "Buenas noches, ¿hablo al restaurante Pangea?"
Biz: "Sí, buenas noches"
AI: "Quisiera hacer una reservación para el sábado a las 8
     de la noche, somos 4 personas."
Biz: "Déjeme checar... sí hay espacio. ¿A nombre de quién?"
AI: "A nombre de Rodrigo Garza."
Biz: "Perfecto, queda reservado. Sábado 8pm, 4 personas,
     Rodrigo Garza."
AI: "Muchas gracias, hasta luego."
```

**Barbershop (With Stylist Preference):**
```
AI: "Buenos días, ¿hablo a Barbería Don Pepe?"
Biz: "Sí, dígame"
AI: "Quisiera agendar un corte para el sábado en la mañana,
     de preferencia con Carlos si tiene disponibilidad."
Biz: "Con Carlos... el sábado tiene las 10:30 y las 12."
AI: "Las 10:30 está perfecto. A nombre de Rodrigo."
Biz: "Anotado. Sábado 10:30, corte con Carlos, Rodrigo."
AI: "Muchas gracias, que tenga buen día."
```

### B. Venue Database Schema

```sql
CREATE TABLE venues (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    business_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    address TEXT,
    default_preferences JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE bookings (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    venue_id UUID REFERENCES venues(id),
    status VARCHAR(20) NOT NULL, -- pending, confirmed, failed, cancelled
    requested_date DATE NOT NULL,
    requested_time TIME NOT NULL,
    confirmed_date DATE,
    confirmed_time TIME,
    party_size INTEGER,
    special_requests TEXT,
    call_recording_url TEXT,
    transcript TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### C. ElevenLabs Configuration

```javascript
// Voice configuration
const voiceConfig = {
  voice_id: "mexican_spanish_professional", // TBD after testing
  model_id: "eleven_multilingual_v2",
  voice_settings: {
    stability: 0.5,
    similarity_boost: 0.75,
    style: 0.3,
    use_speaker_boost: true
  },
  language: "es-MX"
};

// Conversational AI configuration
const conversationalConfig = {
  system_prompt: `Eres un asistente profesional que hace reservaciones
    por teléfono en Monterrey, México. Hablas español mexicano formal,
    usando "usted" con los negocios. Eres amable pero eficiente.`,
  first_message: "Buenas tardes, llamo para hacer una reservación...",
  max_duration_seconds: 180,
  interruption_handling: "natural"
};
```

---

*Document Version 1.0 — December 2024*
*For questions: zelma@citaya.mx*
