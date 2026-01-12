# 🎙️ Voice Agent Voicebox - Requirements Brainstorm

> **Status**: Ideation / Scoping
> **Co-creators**: Zelma + AI Principal Engineer
> **Target Users**: Mamá y Papá (both 60 y/o, small-screen iPhones, Mexico)
> **Interview Value**: GenAI IC5 portfolio piece showing voice agents, NLU, and accessibility

---

## 👥 Audience: 2 Users

| User | Device | Tech Comfort | Primary Use |
|------|--------|--------------|-------------|
| **Papá (Don Eduardo)** | iPhone SE | Low - prefers Excel | Check who paid, walking properties |
| **Mamá** | iPhone Mini | Medium | Bank deposits, verify amounts |

Both are 60+, Spanish-only, and use the app in hands-busy contexts (walking, driving, at bank).

---

## ✅ Key Decisions (Locked In)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **MVP Scope** | Read-only queries first | De-risk STT accuracy before mutations |
| **Interaction Model** | Push-to-talk button | No wake word (battery, privacy) |
| **Language** | Spanish only (no English support needed) | Both users are Spanish-only, app is Mexico-only |
| **TTS Provider** | ElevenLabs with Zelma's cloned voice | Personal, familiar, emotionally resonant |
| **Context of Use** | Walking, at bank, driving | Hands-free scenarios |
| **Architecture** | In-app voice (PWA mic button) | Full control, multi-turn, rich IC5 story |

---

## 🎯 The Vision

A **Spanish-language voice agent** that lets Mamá and Papá manage their 32 rental units hands-free. They press a button, ask a question, and hear **their daughter Zelma's voice** answering them.

**Why Voice?**
1. **Accessibility**: Large touch targets help, but voice removes screen dependency entirely
2. **Context of Use**: Walking properties, at the bank, driving—hands aren't free
3. **Emotional Design**: Hearing Zelma's voice is familiar and trustworthy for 60 y/o parents
4. **GenAI Differentiator**: Shows speech-to-text, intent recognition, voice cloning, and tool use

---

## 🔄 The Flow: Step-by-Step

Let me walk you through exactly what happens when Papá asks "¿Quiénes no han pagado?"

### The User Experience

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PAPÁ'S IPHONE SE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. Papá opens Rentas Claras app                                          │
│      └─ He's walking through Matehuala property                            │
│                                                                             │
│   2. He sees a BIG mic button (🎤) at bottom of screen                     │
│      └─ 80px wide, green, always visible                                   │
│                                                                             │
│   3. He PRESSES AND HOLDS the mic button                                   │
│      └─ Screen shows: "Escuchando..." with pulsing animation               │
│                                                                             │
│   4. He speaks: "¿Quiénes no han pagado?"                                  │
│      └─ His voice is recorded (5-10 seconds max)                           │
│                                                                             │
│   5. He RELEASES the button                                                │
│      └─ Screen shows: "Pensando..." with loading spinner                   │
│                                                                             │
│   6. 2-3 seconds later, HE HEARS ZELMA'S VOICE:                            │
│      └─ "No han pagado 5 inquilinos: Sergio de Matehuala,                  │
│         María de Ensenada, Juan y Carlos de Múzquiz,                       │
│         y Lupita de Huichapan. En total faltan 48,500 pesos."              │
│                                                                             │
│   7. Screen also shows the response as TEXT                                │
│      └─ For noisy environments or if he wants to read it                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Technical Pipeline

Here's what happens under the hood in those 2-3 seconds:

```
STEP 1: CAPTURE AUDIO (iPhone → Flask)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────┐
│ iPhone PWA   │  User holds mic button
│ (Safari)     │  ↓
│              │  MediaRecorder API captures audio
│              │  ↓
│              │  User releases button
│              │  ↓
│              │  Audio blob sent via HTTP POST
└──────┬───────┘
       │ POST /api/voice/query
       │ Body: { audio: <blob>, format: "webm" }
       ▼
┌──────────────┐
│ Flask Server │  Receives audio file
│ (Fly.io)     │  Saves temporarily to /tmp/
└──────┬───────┘
       │
       ▼

STEP 2: SPEECH-TO-TEXT (Flask → Whisper API)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────┐
│ Flask Server │  Sends audio to OpenAI
└──────┬───────┘
       │ POST https://api.openai.com/v1/audio/transcriptions
       │ Body: { file: audio.webm, model: "whisper-1", language: "es" }
       ▼
┌──────────────┐
│ OpenAI       │  Whisper model transcribes Spanish audio
│ Whisper API  │  ↓
│              │  Returns: "¿Quiénes no han pagado?"
└──────┬───────┘
       │ Response: { text: "¿Quiénes no han pagado?" }
       ▼

STEP 3: UNDERSTAND INTENT + GET DATA (Flask → LLM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────┐
│ Flask Server │  Sends transcript to LLM with:
│              │   - System prompt (you are Zelma's voice assistant)
│              │   - Available tools (get_unpaid, get_tenant, etc.)
│              │   - Transcript from Whisper
└──────┬───────┘
       │ POST https://api.anthropic.com/v1/messages
       │ Body: {
       │   system: "Eres el asistente de voz de Rentas Claras...",
       │   tools: [{ name: "get_unpaid_tenants", ... }],
       │   messages: [{ role: "user", content: "¿Quiénes no han pagado?" }]
       │ }
       ▼
┌──────────────┐
│ Claude API   │  LLM understands intent: "user wants unpaid list"
│              │  ↓
│              │  LLM calls tool: get_unpaid_tenants(month=1, year=2026)
└──────┬───────┘
       │ Response: { tool_use: { name: "get_unpaid_tenants", ... } }
       ▼
┌──────────────┐
│ Flask Server │  Executes tool → queries SQLite database
│              │  ↓
│ SQLite DB    │  SELECT * FROM monthly_records WHERE paid=0 AND month=1
│              │  ↓
│              │  Returns: [Sergio, María, Juan, Carlos, Lupita]
└──────┬───────┘
       │ Tool result sent back to LLM
       ▼
┌──────────────┐
│ Claude API   │  LLM formats natural response in Spanish:
│              │  "No han pagado 5 inquilinos: Sergio de Matehuala..."
└──────┬───────┘
       │ Response: { content: "No han pagado 5 inquilinos..." }
       ▼

STEP 4: TEXT-TO-SPEECH (Flask → ElevenLabs)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────┐
│ Flask Server │  Sends response text to ElevenLabs
└──────┬───────┘
       │ POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
       │ Body: { text: "No han pagado 5 inquilinos...", voice_id: "zelma_clone" }
       ▼
┌──────────────┐
│ ElevenLabs   │  Generates audio using Zelma's cloned voice
│ Voice Clone  │  ↓
│              │  Returns: audio/mpeg stream
└──────┬───────┘
       │ Response: <audio stream>
       ▼

STEP 5: PLAY RESPONSE (Flask → iPhone)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────┐
│ Flask Server │  Returns both:
│              │   - Audio stream (for playback)
│              │   - Text (for display)
└──────┬───────┘
       │ Response: { audio: <base64>, text: "No han pagado..." }
       ▼
┌──────────────┐
│ iPhone PWA   │  Plays audio through speaker
│              │  Shows text on screen
│              │  Papá hears Zelma's voice! 🎉
└──────────────┘
```

### The Tools We Use

| Tool | What It Does | Cost | Why This One |
|------|--------------|------|--------------|
| **MediaRecorder API** | Captures audio in browser | Free | Built into Safari, no install needed |
| **OpenAI Whisper API** | Converts speech → text | ~$0.006/min | Best Spanish accuracy, handles Mexican accents |
| **Claude API** | Understands intent, calls DB | ~$0.015/query | Great at function calling, Spanish fluent |
| **ElevenLabs** | Converts text → Zelma's voice | ~$0.30/1000 chars | Voice cloning, natural Spanish |
| **Flask** | Orchestrates everything | Free (Fly.io hosting) | Already running Rentas Claras |
| **SQLite** | Stores tenant/payment data | Free | Already the database |

### Cost Estimate (Per Query) — V1 Paid Version

```
Audio: 5 seconds of speech
━━━━━━━━━━━━━━━━━━━━━━━━━━
Whisper:     $0.006 × (5/60) = $0.0005
Claude:      $0.015 (input) + $0.075 (output ~500 tokens) = ~$0.02
ElevenLabs:  $0.30 × (150 chars / 1000) = $0.045
━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL:       ~$0.07 per voice query

If Papá asks 10 questions/day = $0.70/day = ~$21/month
```

---

## 🆓 V0: Prove It Works (FREE)

Before paying for APIs, let's prove the pipeline works with **100% free browser APIs**.

### V0 Pipeline (All Free)

```
┌─────────────────┐
│   iPhone PWA    │
│  [🎤 Mic Button]│
└────────┬────────┘
         │ User holds button, speaks
         ▼
┌─────────────────┐
│  Web Speech API │  ← FREE, built into Safari
│  (Browser STT)  │     Converts voice → text
└────────┬────────┘
         │ Transcript: "¿Quiénes no han pagado?"
         ▼
┌─────────────────┐
│ Pattern Matching│  ← FREE, runs in browser JavaScript
│  (Hardcoded)    │     Matches keywords → DB query
└────────┬────────┘
         │ Intent: "get_unpaid"
         ▼
┌─────────────────┐
│  Flask Backend  │  ← FREE, already deployed on Fly.io
│  (Fly.io)       │     Queries SQLite, returns data
└────────┬────────┘
         │ Response: { unpaid: ["Sergio", "María"...] }
         ▼
┌─────────────────┐
│ SpeechSynthesis │  ← FREE, built into Safari
│  (Browser TTS)  │     Speaks response (robotic voice)
└────────┬────────┘
         │ Audio plays through speaker
         ▼
┌─────────────────┐
│   iPhone PWA    │
│   [🔊 Speaker]  │  Papá hears: "No han pagado Sergio..."
└─────────────────┘   (Robot voice, not Zelma's)
```

### V0 Trade-offs

| What | V0 (Free) | V1 (Paid) |
|------|-----------|-----------|
| **STT** | Web Speech API | Whisper API |
| **Understanding** | Pattern Matching | Claude LLM |
| **TTS** | Browser SpeechSynthesis | ElevenLabs (your voice) |
| **Cost** | $0 | ~$0.07/query |
| **Voice Quality** | Robotic | Natural (YOUR voice) |
| **Flexibility** | Only exact phrases | Any phrasing |

### V0 Supported Queries (Hardcoded)

These EXACT phrases will work in V0:

| User Says (EXACT) | What Happens |
|-------------------|--------------|
| "¿Quiénes no han pagado?" | Lists unpaid tenants |
| "¿Ya pagó [NAME]?" | Checks if NAME paid |
| "¿Cuánto he cobrado?" | Shows total collected |
| "¿Cómo va [PROPERTY]?" | Shows property summary |

### V0 Does NOT Support

| User Says | Why It Fails |
|-----------|--------------|
| "¿Quién falta?" | No pattern—same meaning, different words |
| "¿Y María?" | No context awareness |
| "¿Pagó el güero?" | Can't resolve nicknames |
| "Dame los morosos" | Slang not in pattern list |

### V0 Implementation Plan

```
Step 1: Add mic button to PWA (HTML/CSS/JS)
        └─ 80px button, push-to-talk

Step 2: Capture audio with Web Speech API
        └─ Uses browser's built-in speech recognition
        └─ Returns text transcript

Step 3: Pattern matching in JavaScript
        └─ if (transcript.includes("no han pagado")) → call /api/unpaid
        └─ if (transcript.includes("ya pagó")) → extract name → call /api/tenant/{name}

Step 4: Flask API endpoints (already exist or easy to add)
        └─ GET /api/voice/unpaid → returns unpaid tenants
        └─ GET /api/voice/tenant/{name} → returns tenant status

Step 5: Speak response with SpeechSynthesis API
        └─ Uses browser's built-in text-to-speech
        └─ Select Spanish voice: speechSynthesis.getVoices().find(v => v.lang === 'es-MX')
```

### V0 Success Criteria

Before moving to V1 (paid), V0 must prove:

1. ✅ Mic button works on iPhone SE and Mini
2. ✅ Web Speech API transcribes Mexican Spanish correctly (test with parents)
3. ✅ Pattern matching handles the 4 core queries
4. ✅ Flask returns correct data
5. ✅ Browser speaks the response (even if robotic)
6. ✅ End-to-end latency < 5 seconds

### When to Upgrade to V1 (Paid)

Move to paid APIs when:

| Problem | Solution |
|---------|----------|
| Web Speech API accuracy is bad | Upgrade to Whisper ($0.0005/query) |
| Parents say things differently | Upgrade to Claude ($0.02/query) |
| Robot voice is confusing/annoying | Upgrade to ElevenLabs ($0.045/query) |
| All of the above | Full V1 stack (~$0.07/query) |

---

## 🔧 V0 Technical Details

### Web Speech API (Free STT)

```javascript
// In browser JavaScript (no server needed for STT)
const recognition = new webkitSpeechRecognition();
recognition.lang = 'es-MX';  // Mexican Spanish
recognition.continuous = false;
recognition.interimResults = false;

recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    console.log('User said:', transcript);
    handleVoiceQuery(transcript);
};

recognition.start();  // Called when mic button pressed
```

### Pattern Matching (Free "Understanding")

```javascript
function handleVoiceQuery(transcript) {
    const text = transcript.toLowerCase();

    if (text.includes('no han pagado') || text.includes('quiénes deben')) {
        return fetchUnpaidTenants();
    }

    if (text.includes('ya pagó')) {
        const name = extractNameAfter(text, 'ya pagó');
        return fetchTenantStatus(name);
    }

    if (text.includes('cuánto he cobrado') || text.includes('cuánto llevamos')) {
        return fetchCollectionTotal();
    }

    if (text.includes('cómo va')) {
        const property = extractNameAfter(text, 'cómo va');
        return fetchPropertySummary(property);
    }

    // Fallback
    speak('No entendí. Intenta preguntar: ¿Quiénes no han pagado?');
}
```

### SpeechSynthesis API (Free TTS)

```javascript
function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-MX';
    utterance.rate = 0.9;  // Slightly slower for elderly

    // Try to find Mexican Spanish voice
    const voices = speechSynthesis.getVoices();
    const mexicanVoice = voices.find(v => v.lang === 'es-MX');
    if (mexicanVoice) {
        utterance.voice = mexicanVoice;
    }

    speechSynthesis.speak(utterance);
}
```

### New Flask Endpoints Needed

```python
# routes/voice.py (new file)

@voice_bp.route('/api/voice/unpaid')
@login_required
def get_unpaid_for_voice():
    """Return unpaid tenants formatted for voice response."""
    unpaid = get_unpaid_tenants(current_month, current_year)

    if not unpaid:
        return jsonify({
            'text': 'Todos han pagado este mes. ¡Felicidades!'
        })

    names = [f"{t['name']} de {t['property_name']}" for t in unpaid]
    total = sum(t['rent'] for t in unpaid)

    return jsonify({
        'text': f"No han pagado {len(unpaid)} inquilinos: {', '.join(names)}. "
                f"En total faltan {total:,.0f} pesos."
    })
```

---

## 📋 Functional Requirements (What It Does)

### 🎯 MVP SCOPE: Read-Only Queries (Phase 1)

These are the ONLY features for MVP. No mutations (marking paid, sending messages).

### Clarified Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Tenant names** | Real names only (no nicknames) | Parents use "Sergio", "María" |
| **Time scope** | Current month + past months | Sometimes ask "¿Pagó Juan en diciembre?" |
| **Long lists** | Summarize first, offer details | "10 no han pagado. ¿Quieres los nombres?" |
| **Deposits** | Included in MVP | Parents need deposit info too |

---

#### FR-1: Core Payment Queries

| ID | Requirement | Example Utterances | Response Example |
|----|-------------|-------------------|------------------|
| FR-1.1 | **List unpaid tenants** | "¿Quiénes no han pagado?" | **Summarize first**: "No han pagado 10 inquilinos. En total faltan 85,000 pesos. ¿Quieres que te diga los nombres?" |
| FR-1.2 | **List unpaid (detailed)** | "Sí, dime los nombres" / "¿Quiénes son?" | "Son: Sergio y Juan de Matehuala, María de Ensenada, Carlos y Lupita de Múzquiz..." |
| FR-1.3 | **Check specific tenant** | "¿Ya pagó Sergio?" | "Sí, Sergio de Matehuala pagó 9,800 pesos el día 3 de enero por transferencia." |
| FR-1.4 | **Collection totals** | "¿Cuánto he cobrado?" / "¿Cuánto llevamos?" | "Este mes has cobrado 245,000 pesos de 32 inquilinos. Faltan 48,500 pesos de 5 inquilinos." |
| FR-1.5 | **Pending amount** | "¿Cuánto falta por cobrar?" / "¿Cuánto deben?" | "Faltan por cobrar 48,500 pesos de 5 inquilinos." |
| FR-1.6 | **Past month query** | "¿Pagó Juan en diciembre?" / "¿Cómo estuvo noviembre?" | "Sí, Juan pagó en diciembre. El día 5 por transferencia." |

#### FR-2: Property-Level Queries

| ID | Requirement | Example Utterances | Response Example |
|----|-------------|-------------------|------------------|
| FR-2.1 | **Property summary** | "¿Cómo va Matehuala?" / "¿Qué onda con Ensenada?" | "En Matehuala han pagado 6 de 8 inquilinos. Faltan 2 que deben 19,600 pesos. ¿Quieres los nombres?" |
| FR-2.2 | **Property collection** | "¿Cuánto hemos cobrado de Múzquiz?" | "De Múzquiz has cobrado 45,000 pesos de 5 inquilinos. Todos han pagado." |

#### FR-3: Late Fee Queries

| ID | Requirement | Example Utterances | Response Example |
|----|-------------|-------------------|------------------|
| FR-3.1 | **Individual late fees** | "¿Cuánto debe Juan de recargos?" | "Juan debe 980 pesos de recargos. Ya van 12 días de retraso." |
| FR-3.2 | **Total late fees** | "¿Cuánto hay de recargos?" | "Este mes hay 4,200 pesos en recargos pendientes de 5 inquilinos." |

#### FR-4: Contract Queries

| ID | Requirement | Example Utterances | Response Example |
|----|-------------|-------------------|------------------|
| FR-4.1 | **Expiring contracts** | "¿Qué contratos se vencen pronto?" | "Se vencen 3 contratos este mes. ¿Quieres los detalles?" |
| FR-4.2 | **Expiring (detailed)** | "Sí, dime cuáles" | "Juan de Matehuala el día 15, María de Ensenada el día 20, y Carlos de Múzquiz el día 28." |
| FR-4.3 | **Contract expiry date** | "¿Cuándo se vence el contrato de Sergio?" | "El contrato de Sergio vence el 30 de marzo. Faltan 78 días." |
| FR-4.4 | **Contract start date** | "¿Cuándo entró Sergio?" / "¿Desde cuándo renta María?" | "Sergio entró el 1 de enero de 2024. Lleva 2 años rentando." |

#### FR-5: Deposit Queries (NEW)

| ID | Requirement | Example Utterances | Response Example |
|----|-------------|-------------------|------------------|
| FR-5.1 | **Check tenant deposit** | "¿Sergio pagó su depósito?" | "Sí, Sergio pagó depósito de 9,800 pesos." |
| FR-5.2 | **Deposit owed to tenant** | "¿Cuánto le debemos a Sergio de depósito?" | "Le debemos 9,800 pesos de depósito a Sergio." |
| FR-5.3 | **All deposits owed** | "¿Cuánto debemos de depósitos?" | "Debes 156,000 pesos en depósitos a 16 inquilinos activos." |
| FR-5.4 | **Unpaid deposits** | "¿Quién no ha pagado depósito?" | "3 inquilinos no han pagado depósito: Juan, María y Carlos." |

#### FR-6: Error Handling & Conversation Flow

| ID | Requirement | Trigger | Agent Response |
|----|-------------|---------|----------------|
| FR-6.1 | **Name disambiguation** | User says "Juan" but there are 2 Juans | "¿Te refieres a Juan de Matehuala o Juan de Ensenada?" |
| FR-6.2 | **Not understood** | Low confidence transcription | "No entendí bien. ¿Puedes repetir?" |
| FR-6.3 | **Out of scope** | User asks something the agent can't do | "Solo puedo consultar información. Para marcar pagos o mandar mensajes, usa la pantalla." |
| FR-6.4 | **Help request** | "¿Qué puedo preguntarte?" / "Ayuda" | "Puedo decirte quién ha pagado, contratos, y depósitos. Pregunta lo que quieras." |
| FR-6.5 | **Follow-up offer** | After long list summary | "¿Quieres que te diga los nombres?" / "¿Te doy los detalles?" |
| FR-6.6 | **Confirm follow-up** | User says "Sí" / "Dime" | Agent provides the detailed list |

### 🔮 Future Phases (NOT MVP)

**Phase 2: Mutations (After STT Accuracy Validated)**
- Mark single tenant as paid: "Pagó Juan García"
- Mark with payment method: "Sergio pagó con transferencia"
- Undo last action: "Cancelar, no pagó"

**Phase 3: WhatsApp Integration**
- Send reminder: "Manda recordatorio a María"
- Bulk reminders: "Manda recordatorio a todos los que deben"

---

## ⚙️ Non-Functional Requirements (How It Behaves)

### NFR-1: Speech Recognition (Input)

| ID | Requirement | Target | Why It Matters |
|----|-------------|--------|----------------|
| NFR-1.1 | **Mexican Spanish accuracy** | 95%+ on tenant names | "Sergio", "Güero", "María Luisa" must transcribe correctly |
| NFR-1.2 | **Accent tolerance** | Northern Mexican accents | Papá is from Monterrey, Mamá from Mexico City |
| NFR-1.3 | **Noise handling** | Works at 60dB ambient noise | Bank lobbies, street corners, construction sites |
| NFR-1.4 | **Short utterance support** | 2-15 seconds | Most queries will be brief |
| NFR-1.5 | **No training required** | Works out of the box | Parents won't do voice training |

### NFR-2: Voice Response (Output)

| ID | Requirement | Target | Why It Matters |
|----|-------------|--------|----------------|
| NFR-2.1 | **Natural Mexican Spanish** | Native-sounding, not robotic | Must feel like talking to Zelma |
| NFR-2.2 | **Pace for elderly** | Slightly slower than normal | Give time to process |
| NFR-2.3 | **Clear number pronunciation** | "Cuarenta y ocho mil quinientos" not "48500" | Parents prefer spelled-out numbers |
| NFR-2.4 | **Volume** | Loud enough for 60 y/o hearing | May need hearing assistance |
| NFR-2.5 | **Voice consistency** | Always Zelma's cloned voice | Familiarity builds trust |

### NFR-3: Latency & Performance

| ID | Requirement | Target | Why It Matters |
|----|-------------|--------|----------------|
| NFR-3.1 | **Total response time** | < 3 seconds end-to-end | Longer feels broken, parents lose patience |
| NFR-3.2 | **Audio start time** | < 500ms after processing | Start speaking fast, stream the rest |
| NFR-3.3 | **Works on iPhone SE** | 2GB RAM, A13 chip | Papá's device |
| NFR-3.4 | **Works on iPhone Mini** | 4GB RAM, A14 chip | Mamá's device |
| NFR-3.5 | **Works on 4G LTE** | < 500kbps bandwidth | Rural Mexico property visits |

### NFR-4: User Interface (Push-to-Talk)

| ID | Requirement | Spec | Why It Matters |
|----|-------------|------|----------------|
| NFR-4.1 | **Mic button size** | 80px diameter minimum | Large enough for 60 y/o fingers |
| NFR-4.2 | **Mic button position** | Fixed bottom center, above nav | Always accessible, thumb-friendly |
| NFR-4.3 | **Recording indicator** | Pulsing red dot + "Escuchando..." | Clear feedback that it's listening |
| NFR-4.4 | **Processing indicator** | Spinner + "Pensando..." | Know it's working, not frozen |
| NFR-4.5 | **Text fallback** | Show response as text too | For noisy places or hearing issues |
| NFR-4.6 | **Replay button** | Tap to hear response again | Missed it? Replay. |

### NFR-5: Reliability & Errors

| ID | Requirement | Behavior | Why It Matters |
|----|-------------|----------|----------------|
| NFR-5.1 | **No connection** | "Sin conexión. Usa la pantalla por ahora." | Clear guidance, don't leave hanging |
| NFR-5.2 | **STT fails** | "No entendí. ¿Puedes repetir?" (max 3 retries) | Graceful retry, then fall back |
| NFR-5.3 | **LLM fails** | "Hay un problema. Intenta de nuevo." | Don't show technical errors |
| NFR-5.4 | **TTS fails** | Show text response only | Partial success is okay |
| NFR-5.5 | **Timeout** | 10 second max, then error message | Don't leave parents waiting forever |

### NFR-6: Privacy & Security

| ID | Requirement | Implementation | Why It Matters |
|----|-------------|----------------|----------------|
| NFR-6.1 | **Session auth required** | Same PIN login as rest of app | Don't expose tenant data without auth |
| NFR-6.2 | **No audio storage** | Delete audio after transcription | Tenant names are PII |
| NFR-6.3 | **No conversation logging** | Don't store query history server-side | Privacy for parents' queries |
| NFR-6.4 | **Minimal PII in responses** | "Sergio" not "Sergio García 555-123-4567" | Only enough to identify |

### NFR-7: Accessibility (60+ Users)

| ID | Requirement | Implementation | Why It Matters |
|----|-------------|----------------|----------------|
| NFR-7.1 | **No hidden features** | Mic button always visible | Parents don't discover hidden UI |
| NFR-7.2 | **No gesture required** | Press-and-hold, not swipe | Simple motor skills |
| NFR-7.3 | **High contrast** | Green (#2D6A4F) on white | Matches existing app, good visibility |
| NFR-7.4 | **Large text** | 17px+ for transcript display | Same as rest of app |
| NFR-7.5 | **Audio + visual** | Always show text alongside audio | Redundancy for accessibility |

---

## 🏗️ Architecture (Locked In)

### Pipeline: PWA → Whisper → LLM → ElevenLabs

```
┌─────────────────┐
│   iPhone PWA    │
│  [🎤 Mic Button]│
└────────┬────────┘
         │ WebRTC/MediaRecorder (audio blob)
         ▼
┌─────────────────┐
│  Flask Backend  │
│   (Fly.io)      │
└────────┬────────┘
         │ Audio file
         ▼
┌─────────────────┐
│  OpenAI Whisper │  ← STT (Spanish, large model)
│  (API or self)  │
└────────┬────────┘
         │ Transcript: "¿Quiénes no han pagado?"
         ▼
┌─────────────────┐
│  LLM (Claude/   │  ← Intent + Tool Use
│   GPT-4)        │     Function: get_unpaid_tenants()
└────────┬────────┘
         │ Response: "No han pagado Sergio, María y Juan..."
         ▼
┌─────────────────┐
│  ElevenLabs     │  ← TTS with Zelma's cloned voice
│  Voice Clone    │
└────────┬────────┘
         │ Audio stream
         ▼
┌─────────────────┐
│   iPhone PWA    │  ← Plays audio response
│   [🔊 Speaker]  │
└─────────────────┘
```

### Component Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **STT** | OpenAI Whisper API | Best Spanish accuracy, handles Mexican names |
| **LLM** | Claude or GPT-4 | Function calling for DB queries |
| **TTS** | ElevenLabs Voice Clone | Zelma's voice = trust + emotional design |
| **Frontend** | PWA mic button | Works on iPhone SE, no app store |
| **Backend** | Flask on Fly.io | Already deployed, add voice routes |

### New API Endpoints Needed

```python
# POST /api/voice/transcribe
# - Receives audio blob
# - Returns transcript + intent + response

# POST /api/voice/speak
# - Receives text
# - Returns ElevenLabs audio stream
```

---

## ⚖️ Trade-offs

### Architecture Trade-offs

| Decision | Option A | Option B | We Chose | Why |
|----------|----------|----------|----------|-----|
| **STT Provider** | Web Speech API (free, in-browser) | Whisper API (paid, server-side) | V0: Web Speech, V1: Whisper | Prove first, pay later |
| **Understanding** | Pattern matching (fast, limited) | LLM (flexible, costly) | V0: Patterns, V1: LLM | Start simple, upgrade when parents say things differently |
| **TTS Provider** | Browser SpeechSynthesis (free, robotic) | ElevenLabs (paid, your voice) | V0: Browser, V1: ElevenLabs | Voice clone is the emotional hook, but costs money |
| **Processing** | On-device (private, limited) | Cloud (powerful, latency) | Cloud | iPhone SE can't run Whisper locally |
| **Interaction** | Wake word ("Hey Rentas") | Push-to-talk (button) | Push-to-talk | No always-listening = better battery, simpler |

### UX Trade-offs

| Decision | Option A | Option B | We Chose | Why |
|----------|----------|----------|----------|-----|
| **Long lists** | Read all names immediately | Summarize first, offer details | Summarize first | 10 names is overwhelming to hear |
| **Confirmation** | Always confirm before action | Only for mutations | Only mutations | Read-only is safe, don't slow down queries |
| **Error handling** | Show technical errors | Friendly Spanish messages | Friendly messages | Parents don't need to know "API 500 error" |
| **Disambiguation** | Guess the most likely tenant | Ask user to clarify | Ask user | Wrong guess = wrong data = lost trust |
| **Response length** | Short and fast | Detailed and complete | Context-dependent | "¿Ya pagó Sergio?" = short, "¿Cómo va Matehuala?" = detailed |

### Cost Trade-offs

| Decision | Cheap Option | Quality Option | Trade-off |
|----------|--------------|----------------|-----------|
| **STT** | Web Speech API ($0) | Whisper ($0.0005) | Accuracy on Mexican names |
| **LLM** | Pattern matching ($0) | Claude ($0.02) | Handle "¿Quién falta?" vs "¿Quiénes no han pagado?" |
| **TTS** | Browser voice ($0) | ElevenLabs ($0.045) | Your voice vs robot voice |
| **Total** | $0/query | $0.07/query | ~$21/month at 10 queries/day |

---

## 🚨 Edge Cases

### Speech Recognition Edge Cases

| Edge Case | What Happens | How We Handle |
|-----------|--------------|---------------|
| **Background noise** | Bank lobby, street traffic, construction | Retry up to 3x, then show "No entendí. Usa la pantalla." |
| **Interrupted speech** | "¿Quiénes no han—" (stops mid-sentence) | Detect incomplete, ask "¿Puedes repetir?" |
| **Accidental trigger** | Button pressed in pocket | Require minimum 1 second hold, ignore gibberish |
| **Very long utterance** | User rambles for 30 seconds | Cap at 15 seconds, process what we got |
| **Silence** | Button held but nothing said | After 5 seconds, prompt "No escuché nada. Intenta de nuevo." |
| **Wrong language** | User accidentally speaks English | Whisper detects, respond "Solo hablo español." |

### Tenant Name Edge Cases

| Edge Case | Example | How We Handle |
|-----------|---------|---------------|
| **Duplicate first names** | 2 tenants named "Juan" | "¿Te refieres a Juan de Matehuala o Juan de Ensenada?" |
| **Similar names** | "María" vs "María Luisa" | Fuzzy match, confirm if ambiguous |
| **Misspoken name** | "Serbio" instead of "Sergio" | Fuzzy match with threshold, ask if unsure |
| **Name not found** | "¿Ya pagó Roberto?" (no Roberto exists) | "No encontré ningún inquilino llamado Roberto." |
| **Partial name** | "¿Ya pagó el de Matehuala?" | If only 1 tenant there, assume. If multiple, ask. |

### Data Edge Cases

| Edge Case | Example | How We Handle |
|-----------|---------|---------------|
| **Empty results** | "¿Quiénes no han pagado?" but everyone paid | "¡Todos han pagado este mes! Felicidades." |
| **New tenant** | Contract starts this month, not in billing yet | Exclude from "who hasn't paid" (existing logic) |
| **Inactive tenant** | Asking about someone who moved out | "Sergio ya no renta aquí. Su contrato terminó en diciembre." |
| **Future month** | "¿Quién pagó en marzo?" (it's January) | "Marzo aún no llega. ¿Te refieres a diciembre pasado?" |
| **Very old month** | "¿Quién pagó en 2020?" | "Solo tengo registros desde [earliest_date]." |

### Network/System Edge Cases

| Edge Case | What Happens | How We Handle |
|-----------|--------------|---------------|
| **No internet** | Phone offline (rural Mexico) | "Sin conexión. Usa la pantalla por ahora." |
| **Slow connection** | 2G/3G in rural areas | Timeout after 10 seconds, show partial if available |
| **Whisper API down** | OpenAI outage | Fall back to browser Web Speech API |
| **Claude API down** | Anthropic outage | Fall back to pattern matching |
| **ElevenLabs down** | TTS fails | Show text response, skip audio |
| **Fly.io down** | Backend unreachable | "No puedo conectar. Intenta en unos minutos." |

### Conversation Flow Edge Cases

| Edge Case | Example | How We Handle |
|-----------|---------|---------------|
| **Follow-up without context** | User says "¿Y María?" as first query | "No entendí. ¿Qué quieres saber de María?" |
| **Changing topic mid-conversation** | "¿Quiénes deben?" → "¿Cuándo se vence el contrato de Sergio?" | Clear context, handle new topic |
| **Rapid-fire questions** | User asks 3 questions before response finishes | Queue or interrupt? TBD - probably interrupt |
| **Contradictory input** | "Sí, no, bueno, dime los nombres" | Parse final intent, or ask for clarification |
| **Cancellation** | User says "Olvídalo" or "Cancelar" | Stop current action, return to ready state |

### Device-Specific Edge Cases

| Edge Case | Device | How We Handle |
|-----------|--------|---------------|
| **Mic permission denied** | iOS Safari | Show clear instructions to enable mic in Settings |
| **Low battery** | iPhone SE | Don't warn (voice doesn't drain much more than screen) |
| **Screen locked** | Phone locks during response | Audio continues playing, show transcript when unlocked |
| **Ringer on silent** | No audio heard | Always show text fallback |
| **AirPods connected** | Audio routes to earbuds | Works fine, no special handling |
| **Speakerphone** | User holds phone away | Mic sensitivity should handle normal distance |

---

## ❓ Remaining Open Questions

### Technical Questions (To Spike)
1. **Whisper deployment**: OpenAI API vs self-hosted on Fly.io? (Cost vs latency)
2. **Audio format**: What format does MediaRecorder produce on iOS Safari?
3. **ElevenLabs latency**: Can we stream audio or wait for full generation?
4. **Fly.io capacity**: Single machine enough for audio processing?

### Product Questions (To Validate)
1. **Interrupt handling**: What if he says "Wait, never mind" mid-response?
2. **Noise tolerance**: Test at bank, street, construction site
3. **Battery impact**: How much does continuous mic affect iPhone SE battery?

### GenAI/Interview Questions
1. How do we frame this for IC5 scope? (System design, not just feature)
2. What makes this "voice agent" vs "voice command"? (Agentic behavior)
3. Evaluation metrics for voice agent quality?

---

## 💡 Interview Framing Ideas

### IC5 Scope Signals
- **System design**: STT → LLM → TTS pipeline, latency optimization
- **Agentic behavior**: Tool use, multi-turn disambiguation, memory
- **Evaluation**: WER metrics, user satisfaction, task completion rate
- **Accessibility**: Voice as inclusive design, not just convenience
- **Trade-offs**: On-device vs cloud, privacy vs capability

### Talking Points
> "I built a voice agent for my parents' rental app. It handles Mexican Spanish with regional variations, disambiguates between 32 tenants by name and property, and uses function calling to interact with a Flask backend. The hardest part was designing confirmation flows that are fast enough to not frustrate a 60-year-old user, but safe enough to prevent accidental payments."

---

## 🚀 MVP Scope Proposal

### Phase 1: Voice Queries Only (Read-Only)
- "¿Quiénes no han pagado?"
- "¿Ya pagó Sergio?"
- "¿Cuánto he cobrado?"

**Why start here**: Low risk (no mutations), validates STT accuracy, quick win

### Phase 2: Voice Commands with Confirmation
- "Marca a Sergio como pagado" → "¿Confirmo que Sergio de Matehuala pagó?"

### Phase 3: WhatsApp Voice Notes
- Send voice note to WhatsApp Business → Get text reply with status

---

## 📝 Next Steps

1. [ ] Interview Don Eduardo about voice usage context
2. [ ] Spike: Test Whisper accuracy on Mexican Spanish names
3. [ ] Spike: Measure latency budget (STT + LLM + TTS)
4. [ ] Define success metrics
5. [ ] Create detailed technical design doc

---

## 🚀 Implementation Plan (V0 - Free Version)

### Overview

We're building V0 first to **prove the concept works** before paying for APIs.

| Milestone | Deliverable | Effort |
|-----------|-------------|--------|
| **M1: Mic Button UI** | Push-to-talk button in PWA | 1-2 hours |
| **M2: Speech-to-Text** | Web Speech API integration | 1-2 hours |
| **M3: Pattern Matching** | Handle 4 core queries | 2-3 hours |
| **M4: Voice API Endpoints** | Flask routes for voice | 2-3 hours |
| **M5: Text-to-Speech** | Browser SpeechSynthesis | 1 hour |
| **M6: End-to-End Testing** | Test with parents | 1-2 hours |
| **Total** | Working V0 | ~10-12 hours |

---

### Milestone 1: Mic Button UI 🎤

**Goal:** Add a big, visible push-to-talk button to the PWA.

**Files to Create/Modify:**
```
templates/partials/voice_button.html  (NEW)
static/css/voice.css                   (NEW)
templates/pagos.html                   (MODIFY - include voice button)
```

**Deliverables:**
- [ ] 80px green mic button, fixed at bottom center (above nav)
- [ ] Press-and-hold interaction (not tap)
- [ ] Visual states: idle → recording → processing
- [ ] "Escuchando..." text when recording
- [ ] "Pensando..." text when processing
- [ ] Works on iPhone SE and Mini

**UI Design:**
```
┌─────────────────────────────────────┐
│                                     │
│         [Tenant Cards...]           │
│                                     │
│                                     │
├─────────────────────────────────────┤
│           ┌─────────┐               │
│           │   🎤    │  ← 80px green │
│           │         │    button     │
│           └─────────┘               │
├─────────────────────────────────────┤
│  Rentas │ Contratos │ Depósitos ... │  ← existing nav
└─────────────────────────────────────┘
```

---

### Milestone 2: Speech-to-Text 🗣️→📝

**Goal:** Capture voice and convert to text using Web Speech API.

**Files to Create/Modify:**
```
static/js/voice.js                     (NEW)
templates/pagos.html                   (MODIFY - include voice.js)
```

**Deliverables:**
- [ ] Initialize `webkitSpeechRecognition` with `lang: 'es-MX'`
- [ ] Start recognition when button pressed
- [ ] Stop recognition when button released
- [ ] Display transcript on screen
- [ ] Handle errors: "No entendí. ¿Puedes repetir?"
- [ ] Test with Mexican Spanish names (Sergio, María, etc.)

**Code Structure:**
```javascript
// static/js/voice.js
class VoiceAgent {
    constructor() {
        this.recognition = new webkitSpeechRecognition();
        this.recognition.lang = 'es-MX';
        this.recognition.continuous = false;
    }

    startListening() { ... }
    stopListening() { ... }
    onResult(transcript) { ... }
    onError(error) { ... }
}
```

---

### Milestone 3: Pattern Matching 🧠

**Goal:** Match transcripts to intents and extract parameters.

**Files to Modify:**
```
static/js/voice.js                     (MODIFY - add pattern matching)
```

**Deliverables:**
- [ ] Pattern: "no han pagado" → `GET /api/voice/unpaid`
- [ ] Pattern: "ya pagó [NAME]" → `GET /api/voice/tenant/{name}`
- [ ] Pattern: "cuánto he cobrado" → `GET /api/voice/totals`
- [ ] Pattern: "cómo va [PROPERTY]" → `GET /api/voice/property/{name}`
- [ ] Fallback: "No entendí. Intenta preguntar: ¿Quiénes no han pagado?"
- [ ] Extract names using regex

**Patterns to Implement:**
```javascript
const PATTERNS = [
    { regex: /no han pagado|quiénes deben/, intent: 'unpaid' },
    { regex: /ya pagó (.+)/, intent: 'check_tenant', extractName: true },
    { regex: /cuánto he cobrado|cuánto llevamos/, intent: 'totals' },
    { regex: /cómo va (.+)/, intent: 'property', extractName: true },
    { regex: /cuánto le debemos.*depósito/, intent: 'deposits_owed' },
];
```

---

### Milestone 4: Voice API Endpoints 🔌

**Goal:** Flask routes that return voice-friendly responses.

**Files to Create/Modify:**
```
routes/voice.py                        (NEW)
routes/__init__.py                     (MODIFY - register blueprint)
```

**Deliverables:**
- [ ] `GET /api/voice/unpaid` → summarized unpaid list
- [ ] `GET /api/voice/tenant/<name>` → tenant payment status
- [ ] `GET /api/voice/totals` → collection totals
- [ ] `GET /api/voice/property/<name>` → property summary
- [ ] `GET /api/voice/deposits` → total deposits owed
- [ ] All responses formatted for voice (spelled-out numbers, natural Spanish)

**Response Format:**
```python
@voice_bp.route('/api/voice/unpaid')
@login_required
def get_unpaid_for_voice():
    unpaid = get_unpaid_tenants(current_month, current_year)

    if not unpaid:
        return jsonify({
            'text': '¡Todos han pagado este mes! Felicidades.',
            'count': 0
        })

    if len(unpaid) > 5:
        # Summarize first
        return jsonify({
            'text': f'No han pagado {len(unpaid)} inquilinos. '
                    f'En total faltan {format_currency(total)} pesos. '
                    f'¿Quieres que te diga los nombres?',
            'count': len(unpaid),
            'has_details': True
        })
    else:
        # List all
        names = [f"{t['name']} de {t['property_name']}" for t in unpaid]
        return jsonify({
            'text': f'No han pagado {len(unpaid)} inquilinos: {", ".join(names)}.',
            'count': len(unpaid)
        })
```

---

### Milestone 5: Text-to-Speech 📝→🔊

**Goal:** Speak the response using browser's SpeechSynthesis.

**Files to Modify:**
```
static/js/voice.js                     (MODIFY - add TTS)
```

**Deliverables:**
- [ ] Use `SpeechSynthesisUtterance` with `lang: 'es-MX'`
- [ ] Slightly slower rate (0.9) for elderly users
- [ ] Display text on screen simultaneously
- [ ] Add replay button to hear again
- [ ] Handle voice not available (text-only fallback)

**Code Structure:**
```javascript
function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-MX';
    utterance.rate = 0.9;

    // Find Mexican Spanish voice if available
    const voices = speechSynthesis.getVoices();
    const mxVoice = voices.find(v => v.lang === 'es-MX');
    if (mxVoice) utterance.voice = mxVoice;

    speechSynthesis.speak(utterance);
}
```

---

### Milestone 6: End-to-End Testing 🧪

**Goal:** Validate with real users (Mamá and Papá).

**Test Scenarios:**
- [ ] "¿Quiénes no han pagado?" → Lists unpaid tenants
- [ ] "¿Ya pagó Sergio?" → Shows Sergio's payment status
- [ ] "¿Cuánto he cobrado?" → Shows total collected
- [ ] "¿Cómo va Matehuala?" → Shows property summary
- [ ] Background noise test (at bank, street)
- [ ] Button size test (easy to press with 60 y/o fingers)

**Success Criteria:**
- [ ] Works on iPhone SE (Papá's device)
- [ ] Works on iPhone Mini (Mamá's device)
- [ ] Web Speech API transcribes Mexican names correctly
- [ ] Responses are understandable (even if robotic voice)
- [ ] End-to-end latency < 5 seconds
- [ ] Parents can use it without instructions

**Feedback to Collect:**
1. Did they understand the response?
2. Was the button easy to find and use?
3. What did they try to ask that didn't work?
4. Would they use this regularly?

---

### After V0: Decide on V1

Based on V0 testing, decide which paid services to add:

| Problem Found | Solution | Cost |
|---------------|----------|------|
| Web Speech API doesn't understand names | Upgrade to Whisper | +$0.0005/query |
| Parents say things differently | Upgrade to Claude LLM | +$0.02/query |
| Robot voice is annoying | Upgrade to ElevenLabs | +$0.045/query |

---

*Brainstorm started: January 2026*
