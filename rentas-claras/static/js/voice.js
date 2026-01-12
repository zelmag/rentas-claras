/**
 * =========================================================================
 * VOICE AGENT - Milestone 2: Speech-to-Text
 * =========================================================================
 * 
 * WHAT THIS FILE DOES:
 * Handles push-to-talk voice interaction using the Web Speech API.
 * This is a FREE browser API - no paid services needed!
 * 
 * HOW THE WEB SPEECH API WORKS:
 * 1. Create a SpeechRecognition object
 * 2. Configure it (language, continuous mode, etc.)
 * 3. Start/stop listening based on user actions
 * 4. Receive transcript via event callbacks
 * 
 * WHY PUSH-TO-TALK (vs always listening)?
 * - No wake word detection needed ("Hey Siri" is complex)
 * - Clear start/end boundaries for speech
 * - Works well in noisy environments (bank, car)
 * - More private (only listens when pressed)
 * 
 * BROWSER SUPPORT:
 * - Chrome/Safari on iOS: ✅ Full support
 * - Firefox: ❌ Limited (we hide the button if unsupported)
 * 
 * =========================================================================
 */

// DEBUG: Add timestamp to all logs for easier tracing
function debugLog(label, data) {
    const timestamp = new Date().toISOString().split('T')[1].slice(0, 12);
    console.log(`[VOICE ${timestamp}] ${label}`, data || '');
}

debugLog('Script loaded', window.location.pathname);

(function() {
    'use strict';

    // =========================================================================
    // SECTION 1: DOM ELEMENTS
    // =========================================================================
    // We grab references to all HTML elements we need to manipulate.
    // Using getElementById for performance (faster than querySelector).
    // 
    // WHY const? These references never change - the elements exist in the DOM
    // and we just keep a pointer to them.

    const container = document.getElementById('voice-agent-container');
    
    // Exit early if voice container doesn't exist on this page
    if (!container) {
        return;
    }

    const micBtn = document.getElementById('voice-mic-btn');
    const micIcon = document.getElementById('voice-mic-icon');
    const spinner = document.getElementById('voice-spinner');
    const btnLabel = document.getElementById('voice-btn-label');
    const overlay = document.getElementById('voice-overlay');
    const statusText = document.getElementById('voice-status');
    const transcriptText = document.getElementById('voice-transcript');
    const responseText = document.getElementById('voice-response');
    const replayBtn = document.getElementById('voice-replay-btn');

    // =========================================================================
    // SECTION 2: STRINGS FROM DATA ATTRIBUTES
    // =========================================================================
    // All user-facing text comes from data-str-* attributes on the container.
    // 
    // WHY THIS PATTERN?
    // 1. Keeps UI strings in HTML (easy for non-engineers to edit)
    // 2. JavaScript stays language-agnostic
    // 3. If we add English later, just swap data attributes
    // 
    // HOW dataset WORKS:
    // HTML: data-str-idle="Mantén para hablar"
    // JS:   container.dataset.strIdle → "Mantén para hablar"
    // Note: kebab-case in HTML becomes camelCase in JS

    const STRINGS = {
        idle: container.dataset.strIdle,
        listening: container.dataset.strListening,
        processing: container.dataset.strProcessing,
        error: container.dataset.strError,
        offline: container.dataset.strOffline,
        noSpeech: container.dataset.strNoSpeech,
        replay: container.dataset.strReplay,
        help: container.dataset.strHelp,
        fallback: container.dataset.strFallback
    };

    const LANG = container.dataset.lang || 'es-MX';

    // =========================================================================
    // SECTION 3: STATE MANAGEMENT
    // =========================================================================
    // A simple object to track what the voice agent is doing.
    // 
    // WHY A STATE OBJECT (vs separate variables)?
    // - Single source of truth
    // - Easy to debug: console.log(state)
    // - Prevents impossible states (can't be recording AND processing)
    // 
    // In React you'd use useState, in Hack you'd use a shape.
    // In vanilla JS, a plain object works fine.

    const state = {
        isRecording: false,
        isProcessing: false,
        isSpeaking: false,
        lastTranscript: '',
        lastResponse: '',
        gotFinalResult: false  // Track if we received a final transcript
    };

    // =========================================================================
    // SECTION 4: SPEECH RECOGNITION SETUP
    // =========================================================================
    // The Web Speech API is a browser-native API (no library needed).
    // Safari uses webkit prefix, Chrome uses unprefixed.
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    // If browser doesn't support speech recognition, hide the button and exit
    if (!SpeechRecognition) {
        console.warn('Voice Agent: SpeechRecognition not supported');
        container.style.display = 'none';
        return;
    }

    // Create the recognition instance (like new XMLHttpRequest in old days)
    const recognition = new SpeechRecognition();
    
    // -------------------------------------------------------------------------
    // RECOGNITION CONFIG
    // -------------------------------------------------------------------------
    // These settings control how speech recognition behaves.
    
    // Language: Mexican Spanish (important for accent/vocabulary)
    recognition.lang = LANG;
    
    // continuous: false = stop after one utterance (good for push-to-talk)
    // If true, it would keep listening forever
    recognition.continuous = false;
    
    // interimResults: true = show partial transcripts while speaking
    // This makes it feel responsive ("it's hearing me!")
    recognition.interimResults = true;
    
    // maxAlternatives: how many guesses to return (we just use the best one)
    recognition.maxAlternatives = 1;

    // =========================================================================
    // SECTION 5: UI STATE FUNCTIONS
    // =========================================================================
    // These functions update the visual state of the voice UI.
    // We keep them separate from logic for clarity.
    //
    // PATTERN: Each function does ONE thing (Single Responsibility Principle)

    function setIdleState() {
        debugLog('setIdleState called', { ...state });
        state.isRecording = false;
        state.isProcessing = false;
        
        // Update container class (CSS uses this for styling)
        container.className = 'voice-agent-container';
        
        // Update button
        micBtn.classList.remove('recording', 'processing', 'speaking', 'error');
        
        // Show mic icon, hide spinner
        micIcon.classList.remove('hidden');
        spinner.classList.add('hidden');
        
        // Update label
        btnLabel.textContent = STRINGS.idle;
        
        // Hide overlay
        overlay.classList.add('hidden');
        overlay.classList.remove('recording', 'processing');
    }

    function setRecordingState() {
        debugLog('setRecordingState called', { ...state });
        state.isRecording = true;
        state.isProcessing = false;
        state.gotFinalResult = false;  // Reset on new recording
        
        container.className = 'voice-agent-container recording';
        
        micBtn.classList.add('recording');
        micBtn.classList.remove('processing', 'speaking', 'error');
        
        micIcon.classList.remove('hidden');
        spinner.classList.add('hidden');
        
        btnLabel.textContent = STRINGS.listening;
        
        // Show overlay with recording state
        overlay.classList.remove('hidden');
        overlay.classList.add('recording');
        overlay.classList.remove('processing');
        
        // Update status text
        statusText.textContent = STRINGS.listening;
        
        // Clear previous content
        transcriptText.textContent = '';
        responseText.textContent = '';
        replayBtn.classList.add('hidden');
    }

    function setProcessingState() {
        debugLog('setProcessingState called', { ...state });
        state.isRecording = false;
        state.isProcessing = true;
        
        container.className = 'voice-agent-container processing';
        
        micBtn.classList.remove('recording', 'speaking', 'error');
        micBtn.classList.add('processing');
        
        // Show spinner, hide mic
        micIcon.classList.add('hidden');
        spinner.classList.remove('hidden');
        
        btnLabel.textContent = STRINGS.processing;
        
        overlay.classList.remove('hidden', 'recording');
        overlay.classList.add('processing');
        
        statusText.textContent = STRINGS.processing;
    }

    function setErrorState(message) {
        state.isRecording = false;
        state.isProcessing = false;
        
        container.className = 'voice-agent-container';
        
        micBtn.classList.remove('recording', 'processing', 'speaking');
        micBtn.classList.add('error');
        
        micIcon.classList.remove('hidden');
        spinner.classList.add('hidden');
        
        btnLabel.textContent = STRINGS.idle;
        
        // Show error in overlay
        overlay.classList.remove('hidden', 'recording', 'processing');
        statusText.textContent = message || STRINGS.error;
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            if (!state.isRecording && !state.isProcessing) {
                setIdleState();
            }
        }, 3000);
    }

    // =========================================================================
    // SECTION 6: SPEECH RECOGNITION EVENT HANDLERS
    // =========================================================================
    // The Web Speech API uses events (like DOM events).
    // We attach handlers to respond when things happen.
    //
    // EVENTS WE CARE ABOUT:
    // - onresult: Got speech transcript (partial or final)
    // - onerror: Something went wrong
    // - onend: Recognition stopped
    // - onspeechend: User stopped talking

    recognition.onresult = function(event) {
        debugLog('onresult fired', { 
            resultsLength: event.results.length,
            currentState: { ...state }
        });
        
        // event.results is an array of SpeechRecognitionResult objects
        // Each result has alternatives (different possible transcriptions)
        // We take the first (most confident) alternative
        
        const result = event.results[event.results.length - 1];
        const transcript = result[0].transcript;
        const isFinal = result.isFinal;
        
        debugLog('transcript', { transcript, isFinal });
        
        // Update the transcript display
        transcriptText.textContent = transcript;
        
        // If this is a final result (not interim), save it
        if (isFinal) {
            debugLog('FINAL result - calling handleTranscript');
            state.lastTranscript = transcript;
            state.gotFinalResult = true;  // Mark that we got a result
            
            // Move to processing state
            setProcessingState();
            
            // TODO (M3): Send transcript to pattern matching
            // For now, just show what was said
            handleTranscript(transcript);
        }
    };

    recognition.onerror = function(event) {
        debugLog('onerror fired', { error: event.error, message: event.message });
        
        // Map error types to user-friendly messages
        const errorMessages = {
            'no-speech': STRINGS.noSpeech,
            'audio-capture': STRINGS.error,
            'not-allowed': 'Necesito permiso para usar el micrófono.',
            'network': STRINGS.offline,
            'aborted': null  // User cancelled, no message needed
        };
        
        const message = errorMessages[event.error];
        if (message) {
            setErrorState(message);
        } else {
            setIdleState();
        }
    };

    recognition.onend = function() {
        debugLog('onend fired', { ...state });
        // Recognition ended (either naturally or due to error)
        // If we're still in recording state, it means user released button
        // but speech continued processing
        if (state.isRecording) {
            // Check if we got a final result
            if (state.gotFinalResult) {
                debugLog('onend: got final result, setting processing');
                setProcessingState();
            } else {
                // No speech detected - user pressed too briefly or didn't speak
                debugLog('onend: NO final result, showing no-speech error');
                setErrorState(STRINGS.noSpeech);
            }
        }
    };

    recognition.onspeechend = function() {
        debugLog('onspeechend fired', { ...state });
    };

    recognition.onstart = function() {
        debugLog('onstart fired - recognition started successfully');
    };

    recognition.onaudiostart = function() {
        debugLog('onaudiostart fired - audio capture started');
    };

    recognition.onaudioend = function() {
        debugLog('onaudioend fired - audio capture ended');
    };

    // =========================================================================
    // SECTION 7: INTENT DETECTION (M3)
    // =========================================================================
    // Detects what the user is asking for based on Spanish keywords.
    // 
    // SUPPORTED INTENTS:
    // 1. unpaid_list    → "¿Quiénes no han pagado?"
    // 2. payment_status → "¿Ya pagó Claudia?"
    // 3. contract_info  → "¿Cuándo vence el contrato de María?"
    // 4. deposit_owed   → "¿Cuánto depósito debemos a Juan?"
    // 5. help           → "¿Qué puedes hacer?" / "Ayuda"
    // 6. unknown        → Anything else (fallback)
    //
    // HOW IT WORKS:
    // 1. Normalize transcript (lowercase, remove accents for matching)
    // 2. Check for keyword patterns in priority order
    // 3. Extract name if query is about a specific tenant
    // 4. Return intent object { type, name, originalTranscript }

    // Helper: Remove accents for easier matching
    // "pagó" → "pago", "María" → "maria"
    function removeAccents(str) {
        return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    }

    // Helper: Normalize transcript for pattern matching
    function normalizeForMatching(transcript) {
        return removeAccents(transcript.toLowerCase().trim());
    }

    // Main intent detection function
    function detectIntent(transcript) {
        const normalized = normalizeForMatching(transcript);
        const original = transcript.trim();
        
        debugLog('detectIntent', { original, normalized });
        
        // -----------------------------------------------------------------
        // INTENT 1: Unpaid list - "¿Quiénes no han pagado?"
        // Keywords: quién/quiénes + no + pagado/pagaron/pago
        //           OR: pendiente, faltan, deben
        // -----------------------------------------------------------------
        if (
            (normalized.includes('quien') && normalized.includes('no') && 
             (normalized.includes('pagado') || normalized.includes('pagaron') || normalized.includes('pago'))) ||
            (normalized.includes('pendiente')) ||
            (normalized.includes('faltan') || normalized.includes('falta')) ||
            (normalized.includes('no han pagado'))
        ) {
            debugLog('detectIntent → unpaid_list');
            return { type: 'unpaid_list', name: null, originalTranscript: original };
        }
        
        // -----------------------------------------------------------------
        // INTENT 1b: Paid list - "¿Quiénes ya pagaron?"
        // Keywords: quién/quiénes + ya + pagaron/pagado (WITHOUT "no")
        // -----------------------------------------------------------------
        if (
            (normalized.includes('quien') && 
             (normalized.includes('ya') || normalized.includes('pagaron') || normalized.includes('pagado')) &&
             !normalized.includes('no'))
        ) {
            debugLog('detectIntent → paid_list');
            return { type: 'paid_list', name: null, originalTranscript: original };
        }
        
        // -----------------------------------------------------------------
        // INTENT 2: Payment status - "¿Ya pagó Claudia?"
        // Keywords: pagó/pago/pagado + name
        // -----------------------------------------------------------------
        if (
            normalized.includes('pago') || 
            normalized.includes('pagado')
        ) {
            const name = extractName(transcript);
            debugLog('detectIntent → payment_status', { name });
            return { type: 'payment_status', name, originalTranscript: original };
        }
        
        // -----------------------------------------------------------------
        // INTENT 3: Contract info - "¿Cuándo vence/entra el contrato?"
        // Keywords: contrato + vence/entra/termina/cuándo
        // -----------------------------------------------------------------
        if (
            normalized.includes('contrato') &&
            (normalized.includes('vence') || normalized.includes('entra') || 
             normalized.includes('termina') || normalized.includes('cuando') ||
             normalized.includes('expira'))
        ) {
            const name = extractName(transcript);
            debugLog('detectIntent → contract_info', { name });
            return { type: 'contract_info', name, originalTranscript: original };
        }
        
        // -----------------------------------------------------------------
        // INTENT 4: Deposit owed - "¿Cuánto depósito debemos a Juan?"
        // Keywords: depósito/deposito + debemos/cuánto
        // -----------------------------------------------------------------
        if (
            normalized.includes('deposito') &&
            (normalized.includes('debemos') || normalized.includes('cuanto') || 
             normalized.includes('debe'))
        ) {
            const name = extractName(transcript);
            debugLog('detectIntent → deposit_owed', { name });
            return { type: 'deposit_owed', name, originalTranscript: original };
        }
        
        // -----------------------------------------------------------------
        // INTENT 5: Help - "¿Qué puedes hacer?" / "Ayuda"
        // -----------------------------------------------------------------
        if (
            normalized.includes('ayuda') ||
            normalized.includes('que puedes') ||
            normalized.includes('como funciona')
        ) {
            debugLog('detectIntent → help');
            return { type: 'help', name: null, originalTranscript: original };
        }
        
        // -----------------------------------------------------------------
        // INTENT 6: Unknown - Fallback
        // -----------------------------------------------------------------
        debugLog('detectIntent → unknown');
        return { type: 'unknown', name: null, originalTranscript: original };
    }

    // Extract tenant name from transcript
    // For now, returns the last word(s) that might be a name
    // In M4, we'll match against actual tenant names from the database
    function extractName(transcript) {
        // Common patterns:
        // "ya pagó claudia" → "claudia"
        // "contrato de maría garcía" → "maría garcía"
        // "depósito de juan" → "juan"
        
        const normalized = transcript.toLowerCase().trim();
        
        // Pattern: "de [name]" - extract everything after "de"
        const deMatch = normalized.match(/\bde\s+(.+?)(?:\s*\?)?$/);
        if (deMatch) {
            return deMatch[1].trim();
        }
        
        // Pattern: "[verb] [name]" - last word is likely the name
        // Remove common query words to find the name
        const queryWords = [
            'ya', 'pago', 'pagó', 'pagado', 'el', 'la', 'los', 'las',
            'quien', 'quienes', 'cuanto', 'cuando', 'que', 'como',
            'contrato', 'deposito', 'depósito', 'debemos', 'vence',
            'entra', 'termina', 'no', 'han', 'ha'
        ];
        
        const words = normalized.split(/\s+/);
        const potentialNames = words.filter(w => 
            !queryWords.includes(removeAccents(w)) && w.length > 2
        );
        
        if (potentialNames.length > 0) {
            // Return the last potential name (most likely to be the actual name)
            return potentialNames[potentialNames.length - 1];
        }
        
        return null;
    }

    // Updated handleTranscript - now calls Flask API for real data
    async function handleTranscript(transcript) {
        debugLog('handleTranscript called', { transcript });
        
        const intent = detectIntent(transcript);
        debugLog('handleTranscript: detected intent', intent);
        
        // Call Flask API for real data
        try {
            debugLog('handleTranscript: calling /api/voice/query');
            const apiResponse = await fetch('/api/voice/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(intent)
            });
            
            if (!apiResponse.ok) {
                throw new Error(`API returned ${apiResponse.status}`);
            }
            
            const data = await apiResponse.json();
            debugLog('handleTranscript: API response', data);
            
            showResponse(data.response);
            
        } catch (error) {
            debugLog('handleTranscript: API error', { error: error.message });
            
            // Fallback to offline message if API fails
            showResponse(STRINGS.offline || 'No pude conectar. Intenta de nuevo.');
        }
    }

    function showResponse(text) {
        debugLog('showResponse called', { text, currentState: { ...state } });
        state.isProcessing = false;
        state.lastResponse = text;
        
        container.className = 'voice-agent-container speaking';
        
        micBtn.classList.remove('recording', 'processing', 'error');
        micBtn.classList.add('speaking');
        
        micIcon.classList.remove('hidden');
        spinner.classList.add('hidden');
        
        // Show response
        statusText.textContent = '';
        responseText.textContent = text;
        
        // Show replay button
        replayBtn.textContent = STRINGS.replay;
        replayBtn.classList.remove('hidden');
        
        // TODO (M5): Speak the response with TTS
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (!state.isRecording && !state.isProcessing) {
                setIdleState();
            }
        }, 5000);
    }

    // =========================================================================
    // SECTION 8: PUSH-TO-TALK HANDLERS
    // =========================================================================
    // We need to handle both mouse (desktop) and touch (mobile) events.
    // 
    // FLOW:
    // 1. User presses down → Start recording
    // 2. User releases → Stop recording
    //
    // WHY BOTH mousedown/mouseup AND touchstart/touchend?
    // - Mouse events work on desktop
    // - Touch events work on mobile
    // - On mobile, mouse events fire after touch (we prevent that)

    function startRecording() {
        debugLog('startRecording called', { ...state });
        
        if (state.isRecording || state.isProcessing) {
            debugLog('startRecording BLOCKED', { 
                reason: state.isRecording ? 'already recording' : 'still processing' 
            });
            return;
        }
        
        debugLog('startRecording: setting recording state');
        setRecordingState();
        
        try {
            debugLog('startRecording: calling recognition.start()');
            recognition.start();
            debugLog('startRecording: recognition.start() succeeded');
        } catch (e) {
            // Can happen if recognition is already running
            debugLog('startRecording EXCEPTION', { error: e.message, name: e.name });
            setErrorState(STRINGS.error);
        }
    }

    function stopRecording() {
        debugLog('stopRecording called', { ...state });
        
        if (!state.isRecording) {
            debugLog('stopRecording BLOCKED - not recording');
            return;
        }
        
        debugLog('stopRecording: calling recognition.stop()');
        
        try {
            recognition.stop();
            debugLog('stopRecording: recognition.stop() succeeded');
        } catch (e) {
            debugLog('stopRecording EXCEPTION', { error: e.message });
        }
        
        // If we got a transcript, we'll move to processing via onresult
        // If not, we'll get an error via onerror
    }

    // -------------------------------------------------------------------------
    // MOUSE EVENTS (Desktop)
    // -------------------------------------------------------------------------
    
    micBtn.addEventListener('mousedown', function(e) {
        e.preventDefault();
        startRecording();
    });

    micBtn.addEventListener('mouseup', function(e) {
        e.preventDefault();
        stopRecording();
    });

    micBtn.addEventListener('mouseleave', function(e) {
        // If user drags finger off button, stop recording
        if (state.isRecording) {
            stopRecording();
        }
    });

    // -------------------------------------------------------------------------
    // TOUCH EVENTS (Mobile - iPhone)
    // -------------------------------------------------------------------------
    
    micBtn.addEventListener('touchstart', function(e) {
        e.preventDefault();  // Prevent mouse events from also firing
        startRecording();
    });

    micBtn.addEventListener('touchend', function(e) {
        e.preventDefault();
        stopRecording();
    });

    micBtn.addEventListener('touchcancel', function(e) {
        // Touch was interrupted (e.g., incoming call)
        if (state.isRecording) {
            stopRecording();
        }
    });

    // -------------------------------------------------------------------------
    // REPLAY BUTTON
    // -------------------------------------------------------------------------
    
    replayBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (state.lastResponse) {
            // TODO (M5): Re-speak with TTS
            console.log('Replay:', state.lastResponse);
        }
    });

    // =========================================================================
    // SECTION 9: INITIALIZATION
    // =========================================================================
    // Set up the initial state when the page loads.

    function init() {
        console.log('Voice Agent initialized');
        console.log('Language:', LANG);
        console.log('Strings loaded:', Object.keys(STRINGS).length);
        
        // Set initial state
        setIdleState();
    }

    // Run init when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
