# 🏠 InvertiMTY - Product Requirements Document

> **Monterrey Investment Property Map with AI Voice Assistant**
>
> A tool to help find and research investment properties in Monterrey, Mexico — with ElevenLabs voice integration for portfolio/job application purposes.

---

## 📋 Executive Summary

**InvertiMTY** is a web app that helps users discover investment properties in Monterrey's metropolitan area through an interactive map interface. The app will progressively integrate ElevenLabs voice AI features, making it both a useful tool AND an impressive portfolio piece for an ElevenLabs job application.

### Why This Product?

| Motivation | How InvertiMTY Addresses It |
|------------|----------------------------|
| **Personal usefulness** | Zelma + parents actively looking for Monterrey investments |
| **ElevenLabs portfolio** | Progressive voice AI integration showcases API skills |
| **Real users from day 1** | Family = guaranteed testers with real needs |
| **Unique angle** | Spanish-first, Mexico real estate = less common in demos |

---

## 🎯 Problem Statement

### The Pain Points

1. **Property discovery is fragmented** — Listings scattered across Inmuebles24, Vivanuncios, Facebook Marketplace, WhatsApp groups
2. **No geographic investment intelligence** — Hard to compare neighborhoods, price per m², ROI potential
3. **Research is time-consuming** — Calling agents, asking the same questions repeatedly
4. **Information asymmetry** — Locals know which zones are up-and-coming, outsiders don't

### Who Has This Problem?

| Persona | Description | Pain Level |
|---------|-------------|------------|
| **Zelma** | Regía living abroad, wants to invest in hometown | 🔥🔥🔥 |
| **Zelma's parents** | Local experts but want data-driven view | 🔥🔥 |
| **Diaspora investors** | Mexicans abroad wanting to invest back home | 🔥🔥🔥 |
| **First-time investors** | Young professionals in MTY exploring options | 🔥🔥 |

---

## 🗺️ Product Vision

```
┌─────────────────────────────────────────────────────────────────┐
│                         InvertiMTY                              │
│            "Tu mapa de inversiones en Monterrey"                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                   INTERACTIVE MAP                       │   │
│   │   🏠 🏠    🏢                                            │   │
│   │        🏠      🏢 🏢                                     │   │
│   │   San Pedro    Valle   Cumbres   Centro                 │   │
│   │   $45k/m²      $28k    $18k      $22k                   │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 🎙️ AI VOICE ASSISTANT                                   │   │
│   │ "Cuéntame sobre las propiedades en San Pedro Garza..."  │   │
│   │                                                         │   │
│   │ 🔊 "San Pedro tiene el precio más alto por metro        │   │
│   │    cuadrado a $45,000 MXN. Es ideal para rentas de      │   │
│   │    alto nivel. El ROI promedio es del 6.2% anual..."    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   [Filtrar] [Comparar] [📞 Llamar al vendedor con AI]          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Phased Roadmap

### Phase 0: MVP Foundation (Week 1-2)
> **Goal:** Useful map with real data, no AI yet

| Feature | Description | Tech |
|---------|-------------|------|
| Interactive map | Monterrey metro area with zoom/pan | Mapbox or Google Maps |
| Property markers | Show listings from aggregated sources | Next.js + API |
| Zone overlays | Color-code by avg price per m² | GeoJSON polygons |
| Basic filters | Price range, type (casa/depto/terreno), bedrooms | React state |
| Property cards | Click marker → see details | Tailwind UI |

**Data sources to explore:**
- Inmuebles24 (scrape or API?)
- Vivanuncios
- Manual curation to start
- Government property registry (catastro)

**Success criteria:** Zelma's parents can use it to explore properties

---

### Phase 1: Voice Property Summaries (Week 3-4)
> **Goal:** ElevenLabs Text-to-Speech integration

| Feature | Description | Tech |
|---------|-------------|------|
| 🔊 "Escuchar resumen" | Click button, AI reads property details aloud | ElevenLabs TTS API |
| Zone audio guides | Pre-generated summaries of each neighborhood | ElevenLabs TTS |
| Spanish voice | High-quality Mexican Spanish voice | `eleven_multilingual_v2` model |

**ElevenLabs Integration:**
```
Endpoint: POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
Model: eleven_multilingual_v2
Output: mp3_44100_128
Latency: 150-170ms first byte
```

**Estimated costs:**
- ~500 characters per property summary
- 100 properties × 500 chars = 50,000 chars/month
- **Cost: ~$5-22/month (Starter/Creator tier)**

**Success criteria:** Can hear property descriptions in natural Spanish

---

### Phase 2: Conversational Property Q&A (Week 5-6)
> **Goal:** ElevenLabs Conversational AI integration

| Feature | Description | Tech |
|---------|-------------|------|
| 🎙️ Voice chat | "¿Tiene estacionamiento?" → AI answers | ElevenLabs Conversational AI |
| Property context | AI knows current property details | RAG / context injection |
| Follow-up questions | Natural multi-turn conversation | WebSocket streaming |

**ElevenLabs Integration:**
```
- Bidirectional WebSocket API
- Real-time voice-to-voice
- Support for interruptions
- ~150ms latency
```

**Success criteria:** Can have natural voice conversation about a property

---

### Phase 3: AI Calling Agent (Week 7-8)
> **Goal:** AI calls property agents/sellers for you

| Feature | Description | Tech |
|---------|-------------|------|
| 📞 "Llamar por mí" | AI makes phone call to agent | ElevenLabs + Twilio |
| Call objectives | "Ask about availability, price negotiation, viewing times" | Prompt engineering |
| Call transcripts | Get summary of what was discussed | Whisper transcription |
| Lead qualification | AI rates the property based on call | GPT-4 analysis |

**Tech Stack:**
```
ElevenLabs Conversational AI
  ↓
Twilio Voice API (Mexican phone numbers)
  ↓
Call Recording → Whisper → Summary
```

**Success criteria:** AI successfully calls a real agent and reports back

---

## 📊 ElevenLabs API Details

### APIs to Use

| API | Use Case | Endpoint |
|-----|----------|----------|
| **Text-to-Speech** | Property summaries, zone guides | `/v1/text-to-speech/{voice_id}` |
| **Conversational AI** | Property Q&A, phone calls | WebSocket API |
| **Voice Cloning** | Create "InvertiMTY" brand voice | `/v1/voices/add` |

### Key Parameters

```javascript
// Text-to-Speech request
{
  "text": "Esta propiedad en San Pedro tiene 3 recámaras...",
  "model_id": "eleven_multilingual_v2",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.75
  }
}
```

### Pricing Estimate

| Phase | Monthly Characters | Cost |
|-------|-------------------|------|
| Phase 1 (TTS) | ~50,000 | $5-22 |
| Phase 2 (Conversational) | ~100,000 | $22-99 |
| Phase 3 (Calling) | ~200,000+ | $99+ |

### Spanish Language Quality
- ✅ Full support in `eleven_multilingual_v2` model
- ✅ Mexican accent available
- ✅ Handles Spanish ↔ English code-switching
- ✅ 70+ languages supported

---

## 🏗️ Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│                    Next.js 14 + React                           │
├─────────────────────────────────────────────────────────────────┤
│  MapView          │  PropertyCard    │  VoiceAssistant          │
│  (Mapbox GL)      │  (Details UI)    │  (ElevenLabs SDK)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND API                             │
│                    Next.js API Routes                           │
├─────────────────────────────────────────────────────────────────┤
│  /api/properties  │  /api/voice      │  /api/call               │
│  (CRUD + search)  │  (ElevenLabs)    │  (Twilio + 11Labs)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       EXTERNAL SERVICES                         │
├─────────────────────────────────────────────────────────────────┤
│  ElevenLabs       │  Twilio          │  Mapbox                  │
│  (Voice AI)       │  (Phone calls)   │  (Maps)                  │
├─────────────────────────────────────────────────────────────────┤
│  Supabase/Postgres│  Property APIs   │  OpenAI                  │
│  (Database)       │  (Data sources)  │  (Analysis)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎨 UI/UX Design Principles

1. **Map-first** — The map IS the product, everything else is secondary
2. **Mobile-optimized** — Most users will browse on phone
3. **Spanish-first** — All UI in Spanish, MXN currency
4. **Voice as enhancement** — Works without voice, voice makes it magical
5. **Fast** — Property cards load instantly, voice streams

---

## 📈 Success Metrics

### Phase 0 (MVP)
- [ ] Zelma's parents use it at least 3x in first week
- [ ] 50+ properties displayed on map
- [ ] Load time < 2 seconds

### Phase 1 (Voice Summaries)
- [ ] 80% of voice summaries sound natural
- [ ] < 200ms latency to first audio byte
- [ ] Users listen to at least 5 summaries per session

### Phase 2 (Conversational)
- [ ] Can answer 5 common property questions accurately
- [ ] Natural conversation flow with interruptions
- [ ] < 500ms response time

### Phase 3 (AI Calling)
- [ ] Successfully complete 1 real phone call
- [ ] Accurate transcript and summary
- [ ] User rates call as "helpful"

---

## ⚠️ Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **No good property data source** | High | Start with manual curation, 20-50 properties |
| **ElevenLabs costs too high** | Medium | Cache audio, limit to premium users |
| **Spanish voice quality poor** | Medium | Test extensively, try different voices |
| **Twilio Mexico numbers expensive** | Medium | Start with outbound-only calls |
| **Legal issues with AI calling** | High | Add disclosure, research Mexican laws |
| **Map API costs** | Low | Mapbox free tier = 50k loads/month |

---

## 🔗 Integration with Other Products

```
┌─────────────────────────────────────────────────────────────────┐
│                      ZELMA'S PRODUCT SUITE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   VueloDigno          InvertiMTY           (Future?)            │
│   ┌─────────┐         ┌─────────┐         ┌─────────┐           │
│   │ ✈️ Air  │         │ 🏠 Real │         │ 📅 Appt │           │
│   │ Compen- │         │ Estate  │         │ Booking │           │
│   │ sation  │         │ Invest  │         │ Helper  │           │
│   └────┬────┘         └────┬────┘         └────┬────┘           │
│        │                   │                   │                │
│        └───────────────────┼───────────────────┘                │
│                            │                                    │
│                    ┌───────▼───────┐                            │
│                    │  🎙️ LlamadaAI │                            │
│                    │  Voice Engine │                            │
│                    │  (ElevenLabs) │                            │
│                    └───────────────┘                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

The ElevenLabs voice integration can eventually become a **shared service** that all products use:
- VueloDigno → AI calls airline customer service
- InvertiMTY → AI calls property agents
- Future apps → AI makes any phone call

---

## 📝 For ElevenLabs Application

### Why This Project Stands Out

1. **Real product, real users** — Not just a demo, family uses it
2. **Spanish-first** — Less common in portfolios, shows multilingual capability
3. **Progressive integration** — TTS → Conversational → Phone calls
4. **Multiple APIs used** — Text-to-Speech, Conversational AI, potentially Voice Cloning
5. **Practical use case** — Real estate is relatable, everyone understands

### Talking Points for Interview

> "I built InvertiMTY to help my family find investment properties in Monterrey. I progressively integrated ElevenLabs, starting with text-to-speech for property summaries, then conversational AI for Q&A, and finally phone calling capability. The Spanish language support was excellent, and the 150ms latency made conversations feel natural. The biggest challenge was [X], which I solved by [Y]..."

---

## 🏁 Next Steps

1. **Validate data sources** — Can we get property listings?
2. **Set up Next.js project** — Reuse VueloDigno patterns
3. **Get API keys** — Mapbox, ElevenLabs, (Twilio later)
4. **Build Phase 0 MVP** — Map with manual property data
5. **Test with parents** — Get real feedback

---

## 📅 Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1-2 | Phase 0 | MVP with map + 50 properties |
| 3-4 | Phase 1 | Voice property summaries |
| 5-6 | Phase 2 | Conversational Q&A |
| 7-8 | Phase 3 | AI phone calling |
| 9+ | Polish | Apply to ElevenLabs! 🚀 |

---

*Last updated: December 21, 2024*
*Author: Zelma*
