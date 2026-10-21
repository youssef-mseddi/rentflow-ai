/**
 * ============================================================================
 * AutoExpress - Voice & Text AI Assistant
 * Frontend Application Logic (Vanilla JavaScript)
 * ============================================================================
 */

(function () {
  'use strict';

  // --- Configuration ---
  const CONFIG = {
    WEBHOOK_URL: 'http://localhost:5678/webhook/car-rental-voice-agent' // replace with your n8n webhook URL,
    SESSION_STORAGE_KEY: 'sessionId',
    AUDIO_TIMESLICE_MS: 250,
  };

  // --- DOM Elements ---
  const elements = {
    // Header & Meta
    statusBadge: document.getElementById('statusBadge'),
    statusText: document.getElementById('statusText'),
    sessionDisplay: document.getElementById('sessionDisplay'),
    resetSessionBtn: document.getElementById('resetSessionBtn'),

    // Voice Recording Controls
    micStage: document.querySelector('.mic-stage'),
    recordBtn: document.getElementById('recordBtn'),
    micIcon: document.getElementById('micIcon'),
    stopIcon: document.getElementById('stopIcon'),
    recordingTimer: document.getElementById('recordingTimer'),
    waveform: document.getElementById('waveform'),
    micHelperText: document.getElementById('micHelperText'),

    // Chat History & Inputs
    chatMessages: document.getElementById('chatMessages'),
    typingIndicator: document.getElementById('typingIndicator'),
    textForm: document.getElementById('textForm'),
    textInput: document.getElementById('textInput'),
    sendBtn: document.getElementById('sendBtn'),
    clearChatBtn: document.getElementById('clearChatBtn'),

    // Quick Actions
    quickButtons: document.querySelectorAll('.quick-btn'),

    // Toast
    toast: document.getElementById('toast'),
    toastIcon: document.getElementById('toastIcon'),
    toastMessage: document.getElementById('toastMessage'),
  };

  // --- Application State ---
  const state = {
    sessionId: null,
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    audioStream: null,
    timerInterval: null,
    recordingSeconds: 0,
    currentAudio: null, // Track currently playing HTML5 Audio object
  };

  // ==========================================================================
  // 1. Session Management
  // ==========================================================================

  /**
   * Initializes or restores the unique session identifier from localStorage.
   */
  function initSession() {
    let storedSessionId = localStorage.getItem(CONFIG.SESSION_STORAGE_KEY);
    if (!storedSessionId) {
      storedSessionId = 'session-' + Date.now();
      localStorage.setItem(CONFIG.SESSION_STORAGE_KEY, storedSessionId);
    }
    state.sessionId = storedSessionId;
    elements.sessionDisplay.textContent = state.sessionId;
  }

  /**
   * Resets the current session ID and creates a fresh session identifier.
   */
  function resetSession() {
    state.sessionId = 'session-' + Date.now();
    localStorage.setItem(CONFIG.SESSION_STORAGE_KEY, state.sessionId);
    elements.sessionDisplay.textContent = state.sessionId;
    showToast('Nouvelle session initialisée : ' + state.sessionId, 'info');
  }

  // ==========================================================================
  // 2. UI Status & Feedback
  // ==========================================================================

  /**
   * Updates the live status badge in the header.
   * @param {'ready'|'recording'|'processing'|'playing'} type
   * @param {string} label
   */
  function setStatus(type, label) {
    elements.statusBadge.className = 'status-badge status-' + type;
    elements.statusText.textContent = label;
  }

  /**
   * Displays a temporary floating toast alert.
   * @param {string} message
   * @param {'info'|'success'|'error'} type
   * @param {number} duration
   */
  function showToast(message, type = 'info', duration = 4000) {
    elements.toast.className = 'toast toast-' + type;
    elements.toastMessage.textContent = message;

    if (type === 'error') elements.toastIcon.textContent = '⚠️';
    else if (type === 'success') elements.toastIcon.textContent = '✓';
    else elements.toastIcon.textContent = 'ℹ';

    elements.toast.classList.remove('hidden');

    clearTimeout(elements.toast._timeout);
    elements.toast._timeout = setTimeout(() => {
      elements.toast.classList.add('hidden');
    }, duration);
  }

  /**
   * Formats seconds into MM:SS display.
   * @param {number} totalSeconds
   * @returns {string}
   */
  function formatTime(totalSeconds) {
    const mins = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const secs = String(totalSeconds % 60).padStart(2, '0');
    return `${mins}:${secs}`;
  }

  // ==========================================================================
  // 3. Audio & Voice Mode (MediaRecorder API)
  // ==========================================================================

  /**
   * Detects the best supported audio MIME type across browsers.
   */
  function getSupportedMimeType() {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ];
    for (const type of types) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }
    return '';
  }

  /**
   * Starts microphone audio capture.
   */
  async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showToast("L'API MediaDevices/Microphone n'est pas supportée sur ce navigateur.", 'error');
      return;
    }

    try {
      // Arrêter toute lecture audio en cours avant d'enregistrer
      stopCurrentAudio();

      state.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const mimeType = getSupportedMimeType();
      state.mediaRecorder = mimeType
        ? new MediaRecorder(state.audioStream, { mimeType })
        : new MediaRecorder(state.audioStream);

      state.audioChunks = [];

      state.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          state.audioChunks.push(event.data);
        }
      };

      state.mediaRecorder.onstop = handleRecordingStopped;

      state.mediaRecorder.start(CONFIG.AUDIO_TIMESLICE_MS);
      state.isRecording = true;

      // Update UI for active recording state
      elements.micStage.classList.add('is-recording');
      elements.recordBtn.classList.add('recording');
      elements.micIcon.classList.add('hidden');
      elements.stopIcon.classList.remove('hidden');
      elements.waveform.classList.remove('hidden');
      elements.recordingTimer.classList.remove('hidden');
      elements.micHelperText.textContent = "Écoute en cours... Cliquez sur le bouton rouge pour arrêter et envoyer.";

      setStatus('recording', 'Enregistrement en cours...');

      // Start timer
      state.recordingSeconds = 0;
      elements.recordingTimer.textContent = '00:00';
      clearInterval(state.timerInterval);
      state.timerInterval = setInterval(() => {
        state.recordingSeconds++;
        elements.recordingTimer.textContent = formatTime(state.recordingSeconds);
      }, 1000);

    } catch (err) {
      console.error('Erreur accès microphone :', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        showToast("Accès au microphone refusé. Veuillez autoriser le micro dans les paramètres du navigateur.", 'error', 6000);
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        showToast("Aucun microphone détecté sur cet appareil.", 'error');
      } else {
        showToast("Impossible d'activer le microphone : " + err.message, 'error');
      }
      stopRecordingUI();
    }
  }

  /**
   * Stops recording and releases hardware tracks.
   */
  function stopRecording() {
    if (!state.mediaRecorder || state.mediaRecorder.state === 'inactive') return;

    try {
      if (typeof state.mediaRecorder.requestData === 'function') {
        state.mediaRecorder.requestData();
      }
    } catch (e) {
      console.warn("requestData ignored", e);
    }

    state.mediaRecorder.stop();
    stopRecordingUI();
  }

  /**
   * Resets visual recording indicators.
   */
  function stopRecordingUI() {
    state.isRecording = false;
    clearInterval(state.timerInterval);

    elements.micStage.classList.remove('is-recording');
    elements.recordBtn.classList.remove('recording');
    elements.micIcon.classList.remove('hidden');
    elements.stopIcon.classList.add('hidden');
    elements.waveform.classList.add('hidden');
    elements.recordingTimer.classList.add('hidden');
    elements.micHelperText.textContent = "Cliquez sur le micro pour parler, puis cliquez à nouveau pour envoyer.";

    // Fermeture des pistes audio physiques
    if (state.audioStream) {
      state.audioStream.getTracks().forEach((track) => track.stop());
      state.audioStream = null;
    }
  }

  /**
   * Callback fired once MediaRecorder stops. Compiles the blob and sends the request.
   */
  async function handleRecordingStopped() {
    let totalBytes = 0;
    for (const chunk of state.audioChunks) {
      totalBytes += chunk.size;
    }

    // Protection contre les clics instantanés vides
    if (state.audioChunks.length === 0 || totalBytes < 400) {
      showToast("Enregistrement audio trop court ou inaudible. Maintenez au moins 1 à 2 secondes.", 'error');
      setStatus('ready', 'Prêt');
      return;
    }

    const mimeType = state.mediaRecorder.mimeType || 'audio/webm';
    const audioBlob = new Blob(state.audioChunks, { type: mimeType });

    // Création d'une bulle utilisateur temporaire en attente de transcription
    const tempUserMsgId = appendMessage('user', '🎙️ Message vocal en cours de transcription...');

    // Construction du FormData multipart/form-data
    const formData = new FormData();
    formData.append('data', audioBlob, 'recording.webm');
    formData.append('sessionId', state.sessionId);

    await executeWebhookRequest(formData, true, tempUserMsgId);
  }

  // ==========================================================================
  // 4. Text Mode (Direct JSON Transmission)
  // ==========================================================================

  /**
   * Handles text input form submission.
   * @param {Event} e
   */
  async function handleTextSubmit(e) {
    e.preventDefault();
    const text = elements.textInput.value.trim();
    if (!text) return;

    elements.textInput.value = '';
    await sendTextMessage(text);
  }

  /**
   * Sends a text query via application/json payload.
   * @param {string} text
   */
  async function sendTextMessage(text) {
    stopCurrentAudio();

    // Affiche immédiatement le message utilisateur
    appendMessage('user', text);

    // Payload JSON attendu : { chatInput: string, sessionId: string }
    const payload = JSON.stringify({
      chatInput: text,
      sessionId: state.sessionId,
    });

    await executeWebhookRequest(payload, false);
  }

  // ==========================================================================
  // 5. Webhook Communication & Multimodal Response Handling
  // ==========================================================================

  /**
   * Executes HTTP POST request to n8n webhook (handles multipart or application/json).
   * @param {FormData|string} body
   * @param {boolean} isMultipart
   * @param {string|null} tempUserMsgId
   */
  async function executeWebhookRequest(body, isMultipart, tempUserMsgId = null) {
    setLoadingState(true);
    setStatus('processing', 'Traitement IA...');

    try {
      const headers = {};
      if (!isMultipart) {
        headers['Content-Type'] = 'application/json';
      }
      // Note: Ne pas définir Content-Type pour FormData (le navigateur injecte le boundary multipart automatiquement)

      const response = await fetch(CONFIG.WEBHOOK_URL, {
        method: 'POST',
        headers: headers,
        body: body,
      });

      if (!response.ok) {
        throw new Error(`Le serveur webhook n8n a répondu avec le statut ${response.status} (${response.statusText}).`);
      }

      // Lecture textuelle sécurisée pour éviter le crash JSON sur corps vide
      const rawText = await response.text();
      console.log('Réponse brute n8n reçue :', rawText);

      if (!rawText || rawText.trim() === '') {
        throw new Error("Le serveur n8n a renvoyé une réponse vide. Vérifiez le nœud 'Respond to Webhook' du workflow.");
      }

      let cleanText = rawText.trim();
      // Nettoyage automatique du préfixe n8n si un signe '=' accidentel est renvoyé en début de corps
      if (cleanText.startsWith('=')) {
        cleanText = cleanText.substring(1).trim();
      }

      let data;
      try {
        data = JSON.parse(cleanText);
      } catch (parseErr) {
        console.warn("Échec parsing JSON direct, fallback en chaîne brute :", parseErr);
        data = { text: cleanText };
      }

      // Détection si n8n renvoie un tableau d'objets [ { ... } ]
      if (Array.isArray(data) && data.length > 0) {
        data = data[0];
      }
      if (data && data.json) {
        data = data.json;
      }

      handleAgentSuccess(data, tempUserMsgId);

    } catch (err) {
      console.error('Erreur Webhook AutoExpress :', err);
      showToast("Échec de communication : " + err.message, 'error', 6000);

      // Si un message vocal était en attente, signaler l'échec dans la bulle
      if (tempUserMsgId) {
        updateMessageContent(tempUserMsgId, "❌ Impossible de transcrire l'audio (Erreur réseau)");
      }

      appendMessage('assistant', "Désolé, une erreur technique est survenue lors de la communication avec le serveur d'orchestration. Veuillez vérifier que le webhook n8n est actif et accessible.");
      setStatus('ready', 'Erreur de connexion');
    } finally {
      setLoadingState(false);
    }
  }

  /**
   * Processes the verified JSON response from AutoExpress n8n agent.
   * Expected format: { transcript: string, text: string, audio_base64: string }
   * @param {Object} data
   * @param {string|null} tempUserMsgId
   */
  function handleAgentSuccess(data, tempUserMsgId = null) {
    // 1. Mise à jour de la transcription utilisateur
    const transcript = data.transcript || data.user_text || data.transcription || null;
    if (tempUserMsgId && transcript) {
      updateMessageContent(tempUserMsgId, transcript);
    } else if (tempUserMsgId) {
      updateMessageContent(tempUserMsgId, "🎙️ Message vocal transmis");
    }

    // 2. Affichage du texte de l'agent
    const responseText = data.text || data.output || data.response || data.message || "Votre demande a été traitée avec succès.";
    const assistantMsgId = appendMessage('assistant', responseText);

    // 3. Décodage et restitution vocale (TTS MP3 Base64)
    const base64Audio = data.audio_base64 || data.audio || null;

    if (base64Audio && typeof base64Audio === 'string' && base64Audio.trim().length > 0) {
      playAgentVoice(base64Audio.trim(), assistantMsgId);
    } else {
      setStatus('ready', 'Prêt');
    }
  }

  /**
   * Instantiates HTML5 Audio and triggers automated speech playback.
   * @param {string} rawBase64
   * @param {string} messageId
   */
  function playAgentVoice(rawBase64, messageId) {
    stopCurrentAudio();

    const audioSrc = rawBase64.startsWith('data:')
      ? rawBase64
      : `data:audio/mp3;base64,${rawBase64}`;

    try {
      const audio = new Audio(audioSrc);
      state.currentAudio = audio;

      setStatus('playing', 'Lecture audio...');

      // Ajout d'un bouton d'écoute dans la bulle de message
      attachAudioPill(messageId, audio);

      audio.play()
        .then(() => {
          console.log("Lecture vocale démarrée avec succès.");
        })
        .catch((playErr) => {
          console.warn("Autoplay bloqué par le navigateur :", playErr);
          showToast("Lecture automatique restreinte : cliquez sur le badge audio pour écouter.", 'info');
          setStatus('ready', 'Prêt (Audio disponible)');
        });

      audio.onended = () => {
        setStatus('ready', 'Prêt');
        state.currentAudio = null;
      };

      audio.onerror = (e) => {
        console.error("Erreur décodeur audio HTML5 :", e);
        setStatus('ready', 'Prêt');
        state.currentAudio = null;
      };

    } catch (err) {
      console.error("Échec initialisation Audio :", err);
      setStatus('ready', 'Prêt');
    }
  }

  /**
   * Stops any currently playing audio.
   */
  function stopCurrentAudio() {
    if (state.currentAudio) {
      try {
        state.currentAudio.pause();
        state.currentAudio.currentTime = 0;
      } catch (e) {}
      state.currentAudio = null;
    }
  }

  /**
   * Attaches an interactive audio replay pill inside the assistant's message bubble.
   * @param {string} messageId
   * @param {HTMLAudioElement} audio
   */
  function attachAudioPill(messageId, audio) {
    const bubble = document.getElementById(messageId);
    if (!bubble) return;

    const pill = document.createElement('div');
    pill.className = 'message-audio-pill';
    pill.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
      </svg>
      <span>Écouter la voix de synthèse</span>
    `;

    pill.addEventListener('click', () => {
      stopCurrentAudio();
      state.currentAudio = audio;
      setStatus('playing', 'Lecture audio...');
      audio.currentTime = 0;
      audio.play().catch((e) => console.warn(e));
      audio.onended = () => setStatus('ready', 'Prêt');
    });

    bubble.querySelector('.message-bubble').appendChild(pill);
  }

  // ==========================================================================
  // 6. Chat DOM Operations
  // ==========================================================================

  /**
   * Appends a new chat message to the history container.
   * @param {'user'|'assistant'} sender
   * @param {string} text
   * @returns {string} The created element ID
   */
  function appendMessage(sender, text) {
    const msgId = 'msg-' + Math.random().toString(36).substring(2, 9);
    const wrapper = document.createElement('div');
    wrapper.id = msgId;
    wrapper.className = `message-wrapper ${sender}`;

    const now = new Date();
    const timeString = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    let avatarSvg = '';
    let senderName = '';

    if (sender === 'assistant') {
      senderName = 'AutoExpress Assistant';
      avatarSvg = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 8V4H8"></path>
          <rect width="16" height="12" x="4" y="8" rx="2"></rect>
          <path d="M2 14h2"></path>
          <path d="M20 14h2"></path>
          <path d="M15 13v2"></path>
          <path d="M9 13v2"></path>
        </svg>
      `;
    } else {
      senderName = 'Vous';
      avatarSvg = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
      `;
    }

    wrapper.innerHTML = `
      <div class="message-avatar">
        ${avatarSvg}
      </div>
      <div class="message-bubble">
        <div class="message-header">
          <span class="message-sender">${senderName}</span>
          <span class="message-time">${timeString}</span>
        </div>
        <div class="message-content">${escapeHtml(text)}</div>
      </div>
    `;

    elements.chatMessages.appendChild(wrapper);
    scrollToBottom();
    return msgId;
  }

  /**
   * Updates an existing message content (e.g. replacing placeholder with real transcript).
   * @param {string} msgId
   * @param {string} newText
   */
  function updateMessageContent(msgId, newText) {
    const el = document.getElementById(msgId);
    if (!el) return;
    const content = el.querySelector('.message-content');
    if (content) {
      content.textContent = newText;
      scrollToBottom();
    }
  }

  /**
   * Sets UI loading / waiting state.
   * @param {boolean} isLoading
   */
  function setLoadingState(isLoading) {
    if (isLoading) {
      elements.typingIndicator.classList.remove('hidden');
      elements.sendBtn.disabled = true;
      elements.textInput.disabled = true;
    } else {
      elements.typingIndicator.classList.add('hidden');
      elements.sendBtn.disabled = false;
      elements.textInput.disabled = false;
      elements.textInput.focus();
    }
    scrollToBottom();
  }

  /**
   * Scrolls chat log to the latest message.
   */
  function scrollToBottom() {
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  }

  /**
   * Escapes HTML entities to prevent XSS.
   * @param {string} str
   * @returns {string}
   */
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /**
   * Clears all messages from the conversation view.
   */
  function clearChat() {
    stopCurrentAudio();
    elements.chatMessages.innerHTML = `
      <div class="message-wrapper assistant">
        <div class="message-avatar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 8V4H8"></path>
            <rect width="16" height="12" x="4" y="8" rx="2"></rect>
            <path d="M2 14h2"></path>
            <path d="M20 14h2"></path>
            <path d="M15 13v2"></path>
            <path d="M9 13v2"></path>
          </svg>
        </div>
        <div class="message-bubble">
          <div class="message-header">
            <span class="message-sender">AutoExpress Assistant</span>
            <span class="message-time">À l'instant</span>
          </div>
          <div class="message-content">
            Historique réinitialisé. Comment puis-je vous aider ?
          </div>
        </div>
      </div>
    `;
    setStatus('ready', 'Prêt');
    showToast('Historique de conversation effacé.', 'info');
  }

  // ==========================================================================
  // 7. Event Listeners & Initialization
  // ==========================================================================

  function bindEvents() {
    // Microphone toggle click
    elements.recordBtn.addEventListener('click', () => {
      if (!state.isRecording) {
        startRecording();
      } else {
        stopRecording();
      }
    });

    // Form text submission
    elements.textForm.addEventListener('submit', handleTextSubmit);

    // Reset session ID
    elements.resetSessionBtn.addEventListener('click', resetSession);

    // Clear chat history
    elements.clearChatBtn.addEventListener('click', clearChat);

    // Quick Action shortcut buttons
    elements.quickButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const query = btn.getAttribute('data-query');
        if (query) {
          elements.textInput.value = query;
          sendTextMessage(query);
        }
      });
    });

    // Handle spacebar shortcut (when not focused in text input)
    window.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && document.activeElement !== elements.textInput) {
        e.preventDefault();
        elements.recordBtn.click();
      }
    });
  }

  // Application Entry Point
  function init() {
    initSession();
    bindEvents();
    setStatus('ready', 'Prêt');
    console.log("AutoExpress Voice & Text Assistant initialisé. Webhook cible :", CONFIG.WEBHOOK_URL);
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
