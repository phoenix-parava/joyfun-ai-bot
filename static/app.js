/**
 * Joy Connect - Formal Minimalist Telegram Mini App Client
 * Browser-Native WebRTC (P2P Audio), External AI Speech, Sanitized Diagnostics,
 * 3-Tier Multilingual Registry, Zero Backend Audio RAM.
 */

(function () {
  'use strict';

  // --- Telegram WebApp Environment Initialization ---
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    try {
      tg.ready();
      tg.expand();
      if (tg.enableClosingConfirmation) {
        tg.enableClosingConfirmation();
      }
    } catch (e) {
      console.warn("Telegram WebApp initialization warning:", e);
    }
  }

  // --- Application State ---
  const state = {
    initData: tg ? tg.initData : (new URLSearchParams(window.location.search).get("init_data") || ""),
    user: null,
    quotas: null,
    config: null,
    ws: null,
    peerConnection: null,
    localStream: null,
    dataChannel: null,
    currentRoomId: null,
    matchedPeerName: null,
    isHumanPeer: false,
    currentModality: "voice", // 'voice' or 'text'
    callTimerInterval: null,
    callSeconds: 0,
    isMuted: false,
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    activeTab: "tab-chat"
  };

  // --- DOM Elements Cache ---
  const elements = {
    // Nav & Header
    wsIndicator: document.getElementById("ws-indicator"),
    headerPseudonym: document.getElementById("header-pseudonym"),
    navTabs: document.querySelectorAll(".nav-tab"),
    tabPanes: document.querySelectorAll(".tab-pane"),

    // Views in Tab 1
    viewIdle: document.getElementById("view-idle"),
    viewQueue: document.getElementById("view-queue"),
    viewVoiceCall: document.getElementById("view-voice-call"),
    viewTextChat: document.getElementById("view-text-chat"),

    // Idle View Controls
    modeSelector: document.getElementById("mode-selector"),
    preferenceSelector: document.getElementById("preference-selector"),
    quickLangSelect: document.getElementById("quick-lang-select"),
    btnStartSession: document.getElementById("btn-start-session"),

    // Queue View Controls
    queueStatusTitle: document.getElementById("queue-status-title"),
    queueStatusDesc: document.getElementById("queue-status-desc"),
    btnCancelQueue: document.getElementById("btn-cancel-queue"),
    btnInstantWarmup: document.getElementById("btn-instant-warmup"),
    queueWarmupContainer: document.getElementById("queue-warmup-container"),
    warmupChatBox: document.getElementById("warmup-chat-box"),
    warmupInput: document.getElementById("warmup-input"),
    btnSendWarmup: document.getElementById("btn-send-warmup"),

    // Voice Call View Controls
    voicePeerName: document.getElementById("voice-peer-name"),
    voiceLangBadge: document.getElementById("voice-lang-badge"),
    voiceCallTimer: document.getElementById("voice-call-timer"),
    voicePeerAvatar: document.getElementById("voice-peer-avatar"),
    icebreakerText: document.getElementById("icebreaker-text"),
    btnNextIcebreaker: document.getElementById("btn-next-icebreaker"),
    btnMuteMic: document.getElementById("btn-mute-mic"),
    micIcon: document.getElementById("mic-icon"),
    btnEndVoice: document.getElementById("btn-end-voice"),
    btnVoiceToText: document.getElementById("btn-voice-to-text"),
    remoteAudio: document.getElementById("remote-audio"),

    // Text Chat View Controls
    textPeerName: document.getElementById("text-peer-name"),
    textPeerSub: document.getElementById("text-peer-sub"),
    textIcebreakerBanner: document.getElementById("text-icebreaker-banner"),
    textIcebreakerContent: document.getElementById("text-icebreaker-content"),
    btnCloseIcebreaker: document.getElementById("btn-close-icebreaker"),
    btnNextIcebreakerText: document.getElementById("btn-next-icebreaker-text"),
    textChatBox: document.getElementById("text-chat-box"),
    chatMsgInput: document.getElementById("chat-msg-input"),
    btnSendText: document.getElementById("btn-send-text"),
    btnEndText: document.getElementById("btn-end-text"),

    // Diagnostics Banner
    diagnosticBanner: document.getElementById("diagnostic-banner"),
    diagCode: document.getElementById("diag-code"),
    diagMsg: document.getElementById("diag-msg"),
    diagActions: document.getElementById("diag-actions"),
    btnCloseDiag: document.getElementById("btn-close-diag"),

    // Tab 2 Quotas
    quotaP2pLimit: document.getElementById("quota-p2p-limit"),
    quotaP2pRem: document.getElementById("quota-p2p-rem"),
    quotaAiVoiceLimit: document.getElementById("quota-ai-voice-limit"),
    quotaAiVoiceRem: document.getElementById("quota-ai-voice-rem"),
    quotaAiTextLimit: document.getElementById("quota-ai-text-limit"),
    quotaAiTextRem: document.getElementById("quota-ai-text-rem"),
    btnRefreshQuota: document.getElementById("btn-refresh-quota"),

    // Tab 3 Settings
    settingPseudonym: document.getElementById("setting-pseudonym"),
    settingLanguage: document.getElementById("setting-language"),
    settingPartnerPref: document.getElementById("setting-partner-pref"),
    settingLowData: document.getElementById("setting-low-data"),
    settingSpeechRate: document.getElementById("setting-speech-rate"),
    speechRateVal: document.getElementById("speech-rate-val"),
    settingEmailEnabled: document.getElementById("setting-email-enabled"),
    settingEmailAddr: document.getElementById("setting-email-addr"),
    btnSaveSettings: document.getElementById("btn-save-settings"),
    feedbackInput: document.getElementById("feedback-input"),
    btnSubmitFeedback: document.getElementById("btn-submit-feedback"),

    // Tab 4 Info
    infoCreatorText: document.getElementById("info-creator-text"),

    // Modals
    modalTerms: document.getElementById("modal-terms"),
    btnAcceptTerms: document.getElementById("btn-accept-terms"),
    modalOnboarding: document.getElementById("modal-onboarding"),
    onboardPseudonym: document.getElementById("onboard-pseudonym"),
    onboardLanguage: document.getElementById("onboard-language"),
    onboardModeSelector: document.getElementById("onboard-mode-selector"),
    onboardPartnerPref: document.getElementById("onboard-partner-pref"),
    btnCompleteOnboarding: document.getElementById("btn-complete-onboarding")
  };

  // --- Client-Side PII Filter Pre-Flight ---
  const PII_PHONE_REGEX = /(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b\d{10,15}\b/;
  const PII_EMAIL_REGEX = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
  const PII_TELEGRAM_REGEX = /(?:@|(?:https?:\/\/)?(?:t|telegram)\.me\/)[a-zA-Z0-9_]{3,}/i;
  const PII_URL_REGEX = /(?:https?:\/\/|www\.)[^\s/$.?#].[^\s]*/i;

  function detectClientPII(text) {
    if (PII_PHONE_REGEX.test(text)) return "Phone number";
    if (PII_EMAIL_REGEX.test(text)) return "Email address";
    if (PII_TELEGRAM_REGEX.test(text)) return "Telegram username/link";
    if (PII_URL_REGEX.test(text)) return "External website URL";
    return null;
  }

  // --- API Fetch Helper ---
  async function apiRequest(endpoint, method = "GET", body = null) {
    const headers = { "Content-Type": "application/json" };
    const options = { method, headers };
    if (body) {
      options.body = JSON.stringify(body);
    }
    try {
      const res = await fetch(endpoint, options);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || `HTTP ${res.status}`);
      }
      return data;
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  }

  // --- Navigation Handling ---
  function switchTab(tabId) {
    state.activeTab = tabId;
    elements.navTabs.forEach(tab => {
      if (tab.dataset.tab === tabId) {
        tab.classList.add("active");
      } else {
        tab.classList.remove("active");
      }
    });

    elements.tabPanes.forEach(pane => {
      if (pane.id === tabId) {
        pane.classList.add("active");
      } else {
        pane.classList.remove("active");
      }
    });
  }

  elements.navTabs.forEach(tab => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  // --- Populate 3-Tier Language Dropdowns ---
  function populateLanguageDropdowns(matrix) {
    const dropdowns = [elements.quickLangSelect, elements.settingLanguage, elements.onboardLanguage];

    dropdowns.forEach(select => {
      if (!select) return;
      select.innerHTML = "";

      for (const [tierKey, tierInfo] of Object.entries(matrix)) {
        const group = document.createElement("optgroup");
        group.label = tierInfo.label;

        for (const [code, lang] of Object.entries(tierInfo.languages)) {
          const opt = document.createElement("option");
          opt.value = code;
          opt.textContent = `${lang.name} (${lang.native})`;
          group.appendChild(opt);
        }
        select.appendChild(group);
      }
    });
  }

  // --- Load System Configuration ---
  async function loadConfig() {
    try {
      const config = await apiRequest("/api/config");
      state.config = config;
      if (config.ice_servers && config.ice_servers.length > 0) {
        state.iceServers = config.ice_servers;
      }
      if (config.language_matrix) {
        populateLanguageDropdowns(config.language_matrix);
      }
      if (config.creator_handle && elements.infoCreatorText) {
        elements.infoCreatorText.innerHTML = `For platform support, inquiries, or security reports, use <code>/feedback</code> or message <a href="https://t.me/${config.creator_handle}" target="_blank" style="color:var(--link-color)">@${config.creator_handle}</a>.`;
      }
    } catch (err) {
      console.warn("Could not load public config:", err);
    }
  }

  // --- Authenticate User ---
  async function authenticate() {
    if (!state.initData) {
      showDiagnostic("BROWSER_DEV_MODE", "Telegram initData not detected. Running in standalone browser preview mode.");
      // Mock minimal user for preview
      state.user = {
        user_id: 99999999,
        pseudonym: "DemoUser",
        language: "tanglish",
        modality: "voice",
        partner_preference: "real_or_ai",
        terms_accepted_at: "2026-01-01",
        onboarding_completed: 1,
        speech_rate: 1.0,
        low_data_mode: 0
      };
      updateUIForUser();
      connectWebSocket();
      return;
    }

    try {
      const res = await apiRequest("/api/auth", "POST", { init_data: state.initData });
      state.user = res.user;
      state.quotas = res.quotas;

      updateUIForUser();
      renderQuotas(res.quotas);

      // Check Terms acceptance
      if (!state.user.terms_accepted_at) {
        elements.modalTerms.classList.remove("hidden");
        return;
      }

      // Check Onboarding status
      if (!state.user.onboarding_completed) {
        elements.modalOnboarding.classList.remove("hidden");
        return;
      }

      connectWebSocket();
    } catch (err) {
      showDiagnostic("AUTH_ERROR", "Failed to cryptographically authenticate Telegram session. Please close and reopen the app.");
    }
  }

  // --- Update UI with User Profile Data ---
  function updateUIForUser() {
    if (!state.user) return;
    elements.headerPseudonym.textContent = state.user.pseudonym;
    elements.settingPseudonym.value = state.user.pseudonym;
    elements.settingLanguage.value = state.user.language || "tanglish";
    elements.settingPartnerPref.value = state.user.partner_preference || "real_or_ai";
    elements.quickLangSelect.value = state.user.language || "tanglish";
    elements.settingSpeechRate.value = state.user.speech_rate || 1.0;
    elements.speechRateVal.textContent = `${state.user.speech_rate || 1.0}x`;
    elements.settingLowData.checked = !!state.user.low_data_mode;
    elements.settingEmailEnabled.checked = !!state.user.email_enabled;
    elements.settingEmailAddr.value = state.user.email_address || "";

    // Highlight active mode selector
    const modality = state.user.modality || "voice";
    state.currentModality = modality;
    elements.modeSelector.querySelectorAll(".segment-btn").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.val === modality);
    });

    elements.preferenceSelector.querySelectorAll(".segment-btn").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.val === state.user.partner_preference);
    });
  }

  // --- Quota Display ---
  function renderQuotas(quotas) {
    if (!quotas) return;
    const formatTime = (sec) => `${Math.floor(sec / 60)}m ${sec % 60}s`;

    elements.quotaP2pLimit.textContent = `${quotas.p2p_voice.limit} sec`;
    elements.quotaP2pRem.textContent = `${quotas.p2p_voice.remaining} sec`;

    elements.quotaAiVoiceLimit.textContent = `${quotas.ai_voice.limit} sec`;
    elements.quotaAiVoiceRem.textContent = `${quotas.ai_voice.remaining} sec`;

    elements.quotaAiTextLimit.textContent = `${quotas.ai_text.limit} msgs`;
    elements.quotaAiTextRem.textContent = `${quotas.ai_text.remaining} msgs`;
  }

  elements.btnRefreshQuota.addEventListener("click", async () => {
    try {
      const res = await apiRequest(`/api/user/quota?init_data=${encodeURIComponent(state.initData)}`);
      state.quotas = res.quotas;
      renderQuotas(res.quotas);
    } catch (e) {
      console.warn("Could not refresh quota:", e);
    }
  });

  // --- Mandatory Accept-Only Terms Handler ---
  elements.btnAcceptTerms.addEventListener("click", async () => {
    try {
      elements.btnAcceptTerms.disabled = true;
      elements.btnAcceptTerms.textContent = "Accepting...";
      const res = await apiRequest("/api/user/terms/accept", "POST", { init_data: state.initData });
      state.user = res.user;
      elements.modalTerms.classList.add("hidden");

      if (!state.user.onboarding_completed) {
        elements.modalOnboarding.classList.remove("hidden");
      } else {
        connectWebSocket();
      }
    } catch (err) {
      alert("Failed to accept terms: " + err.message);
    } finally {
      elements.btnAcceptTerms.disabled = false;
      elements.btnAcceptTerms.textContent = "✅ I Accept Terms & Privacy Policy";
    }
  });

  // --- Pre-Chat Onboarding Handler ---
  let onboardSelectedMode = "voice";
  elements.onboardModeSelector.querySelectorAll(".segment-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      elements.onboardModeSelector.querySelectorAll(".segment-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      onboardSelectedMode = btn.dataset.val;
    });
  });

  elements.btnCompleteOnboarding.addEventListener("click", async () => {
    const pseudonym = elements.onboardPseudonym.value.trim();
    const language = elements.onboardLanguage.value;
    const partnerPref = elements.onboardPartnerPref.value;

    if (pseudonym.length < 3 || pseudonym.length > 20) {
      alert("Display name must be between 3 and 20 characters.");
      return;
    }
    const piiCheck = detectClientPII(pseudonym);
    if (piiCheck) {
      alert(`Display name cannot contain personal information (${piiCheck}).`);
      return;
    }

    try {
      elements.btnCompleteOnboarding.disabled = true;
      elements.btnCompleteOnboarding.textContent = "Saving...";
      const res = await apiRequest("/api/user/onboarding", "POST", {
        init_data: state.initData,
        pseudonym,
        language,
        modality: onboardSelectedMode,
        partner_preference: partnerPref
      });
      state.user = res.user;
      elements.modalOnboarding.classList.add("hidden");
      updateUIForUser();
      connectWebSocket();
    } catch (err) {
      alert("Failed to save onboarding: " + err.message);
    } finally {
      elements.btnCompleteOnboarding.disabled = false;
      elements.btnCompleteOnboarding.textContent = "🚀 Launch Communication App";
    }
  });

  // --- Settings Update Handler ---
  elements.settingSpeechRate.addEventListener("input", (e) => {
    elements.speechRateVal.textContent = `${e.target.value}x`;
  });

  elements.btnSaveSettings.addEventListener("click", async () => {
    const pseudonym = elements.settingPseudonym.value.trim();
    const language = elements.settingLanguage.value;
    const partner_preference = elements.settingPartnerPref.value;
    const low_data_mode = elements.settingLowData.checked;
    const speech_rate = parseFloat(elements.settingSpeechRate.value);
    const email_enabled = elements.settingEmailEnabled.checked;
    const email_address = elements.settingEmailAddr.value.trim();

    if (pseudonym.length < 3 || pseudonym.length > 20) {
      alert("Display name must be 3 to 20 characters.");
      return;
    }

    try {
      elements.btnSaveSettings.disabled = true;
      elements.btnSaveSettings.textContent = "Saving...";
      const res = await apiRequest("/api/user/settings", "POST", {
        init_data: state.initData,
        pseudonym,
        language,
        partner_preference,
        low_data_mode,
        speech_rate,
        email_enabled,
        email_address
      });
      state.user = res.user;
      updateUIForUser();
      alert("Settings updated successfully!");
    } catch (err) {
      alert("Failed to update settings: " + err.message);
    } finally {
      elements.btnSaveSettings.disabled = false;
      elements.btnSaveSettings.textContent = "💾 Save Settings";
    }
  });

  // --- Feedback Submission Handler ---
  elements.btnSubmitFeedback.addEventListener("click", async () => {
    const msg = elements.feedbackInput.value.trim();
    if (!msg) {
      alert("Please enter your feedback message.");
      return;
    }

    try {
      elements.btnSubmitFeedback.disabled = true;
      elements.btnSubmitFeedback.textContent = "Sending...";
      await apiRequest("/api/feedback", "POST", {
        init_data: state.initData,
        message: msg
      });
      elements.feedbackInput.value = "";
      alert("Thank you! Your feedback has been relayed directly to the administrator.");
    } catch (err) {
      alert("Failed to send feedback: " + err.message);
    } finally {
      elements.btnSubmitFeedback.disabled = false;
      elements.btnSubmitFeedback.textContent = "📤 Send Feedback";
    }
  });

  // --- Mode & Preference Selection on Idle Screen ---
  elements.modeSelector.querySelectorAll(".segment-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      elements.modeSelector.querySelectorAll(".segment-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.currentModality = btn.dataset.val;
      if (state.user) state.user.modality = state.currentModality;
    });
  });

  elements.preferenceSelector.querySelectorAll(".segment-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      elements.preferenceSelector.querySelectorAll(".segment-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      if (state.user) state.user.partner_preference = btn.dataset.val;
    });
  });

  elements.quickLangSelect.addEventListener("change", () => {
    if (state.user) state.user.language = elements.quickLangSelect.value;
  });

  // --- WebRTC Signaling & WebSocket Hub ---
  function connectWebSocket() {
    if (state.ws && (state.ws.readyState === WebSocket.OPEN || state.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const loc = window.location;
    const proto = loc.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${proto}//${loc.host}/ws/signaling?init_data=${encodeURIComponent(state.initData)}`;

    elements.wsIndicator.className = "status-dot offline";
    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
      elements.wsIndicator.className = "status-dot online";
    };

    state.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleSignalingMessage(data);
      } catch (e) {
        console.error("Invalid signaling message:", e);
      }
    };

    state.ws.onerror = (err) => {
      console.warn("Signaling error:", err);
      elements.wsIndicator.className = "status-dot offline";
    };

    state.ws.onclose = () => {
      elements.wsIndicator.className = "status-dot offline";
      // Auto-reconnect after 3 seconds if not actively on call
      setTimeout(() => {
        if (!state.peerConnection) connectWebSocket();
      }, 3000);
    };
  }

  function sendSignaling(data) {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.ws.send(JSON.stringify(data));
    }
  }

  // --- Screen View Switcher ---
  function showView(viewName) {
    elements.viewIdle.classList.add("hidden");
    elements.viewQueue.classList.add("hidden");
    elements.viewVoiceCall.classList.add("hidden");
    elements.viewTextChat.classList.add("hidden");

    if (viewName === "idle") elements.viewIdle.classList.remove("hidden");
    else if (viewName === "queue") elements.viewQueue.classList.remove("hidden");
    else if (viewName === "voice") elements.viewVoiceCall.classList.remove("hidden");
    else if (viewName === "text") elements.viewTextChat.classList.remove("hidden");
  }

  // --- Matchmaking Controls ---
  elements.btnStartSession.addEventListener("click", () => {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
      connectWebSocket();
    }
    showView("queue");
    elements.queueStatusTitle.textContent = "Searching for a partner...";
    elements.queueStatusDesc.textContent = `Matching language (${state.user ? state.user.language : 'Tanglish'}) & modality...`;
    elements.queueWarmupContainer.classList.add("hidden");
    elements.warmupChatBox.innerHTML = "";

    sendSignaling({
      type: "join_queue"
    });
  });

  elements.btnCancelQueue.addEventListener("click", () => {
    sendSignaling({ type: "leave_queue" });
    showView("idle");
  });

  // --- Instant AI Warm-Up in Queue ---
  elements.btnInstantWarmup.addEventListener("click", () => {
    elements.queueWarmupContainer.classList.remove("hidden");
    appendWarmupMessage("Joy AI", "Hello! I am Joy AI. While you wait for a partner, feel free to practice speaking or asking anything.", "peer");
  });

  function sendWarmupText() {
    const text = elements.warmupInput.value.trim();
    if (!text) return;
    const pii = detectClientPII(text);
    if (pii) {
      alert(`Sharing ${pii} is strictly prohibited.`);
      return;
    }
    appendWarmupMessage("You", text, "mine");
    elements.warmupInput.value = "";
    sendSignaling({ type: "warmup_message", text });
  }

  elements.btnSendWarmup.addEventListener("click", sendWarmupText);
  elements.warmupInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendWarmupText();
  });

  function appendWarmupMessage(author, text, cls) {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${cls}`;
    bubble.innerHTML = `<div class="bubble-author">${author}</div><div>${escapeHtml(text)}</div>`;
    elements.warmupChatBox.appendChild(bubble);
    elements.warmupChatBox.scrollTop = elements.warmupChatBox.scrollHeight;
  }

  // --- WebRTC PeerConnection Setup ---
  async function initializePeerConnection(role) {
    const config = { iceServers: state.iceServers };
    const pc = new RTCPeerConnection(config);
    state.peerConnection = pc;

    // Local Audio Acquisition
    try {
      const audioConstraints = {
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        },
        video: false
      };
      state.localStream = await navigator.mediaDevices.getUserMedia(audioConstraints);
      state.localStream.getAudioTracks().forEach(track => pc.addTrack(track, state.localStream));
    } catch (err) {
      console.warn("Microphone access denied or unavailable:", err);
      showDiagnostic("MEDIA_MIC_DENIED", "Microphone access was denied. You can enable microphone permissions in your browser settings or switch to Text Chat mode.", [
        { label: "Switch to Text Chat", action: () => switchToTextModality() }
      ]);
      return null;
    }

    // ICE Candidate Exchange
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        sendSignaling({
          type: "ice_candidate",
          candidate: event.candidate
        });
      }
    };

    // Remote Audio Stream Arrival
    pc.ontrack = (event) => {
      if (elements.remoteAudio && event.streams[0]) {
        elements.remoteAudio.srcObject = event.streams[0];
      }
    };

    // Connection State Telemetry
    pc.onconnectionstatechange = () => {
      if (pc.connectionState === "failed") {
        showDiagnostic("WEBRTC_NAT_FAILURE", "P2P direct route failed due to restrictive NAT/firewall. Attempting relay reconnection...");
      } else if (pc.connectionState === "disconnected") {
        showDiagnostic("PEER_DROPPED", "Audio connection lost. Checking connection status...");
      }
    };

    // Create RTCDataChannel on Initiator
    if (role === "initiator") {
      try {
        state.dataChannel = pc.createDataChannel("icebreaker_sync");
        setupDataChannelEvents(state.dataChannel);
      } catch (e) {
        console.warn("DataChannel creation not supported:", e);
      }
    } else {
      pc.ondatachannel = (event) => {
        state.dataChannel = event.channel;
        setupDataChannelEvents(state.dataChannel);
      };
    }

    return pc;
  }

  function setupDataChannelEvents(dc) {
    dc.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "icebreaker_card") {
          updateIcebreakerUI(msg.topic);
        }
      } catch (err) {}
    };
  }

  // Apply 12 kbps Opus Low-Data optimization
  function applyOpusLowDataSDP(sdp) {
    if (!state.user || !state.user.low_data_mode) return sdp;
    // Set maxaveragebitrate=12000 in Opus fmtp line
    return sdp.replace(/a=fmtp:(\d+) (.*)/g, (match, pt, params) => {
      if (params.includes("opus")) {
        return `a=fmtp:${pt} ${params};maxaveragebitrate=12000;stereo=0;sprop-stereo=0`;
      }
      return match;
    });
  }

  // --- Signaling Message Router ---
  async function handleSignalingMessage(data) {
    switch (data.type) {
      case "queued":
        elements.queueStatusTitle.textContent = "Searching for a partner...";
        elements.queueStatusDesc.textContent = data.message || "Matching by language and mode...";
        break;

      case "queue_cancelled":
        showView("idle");
        break;

      case "warmup_reply":
        appendWarmupMessage("Joy AI", data.text, "peer");
        if (state.currentModality === "voice") {
          speakWithWebSpeech(data.text);
        }
        break;

      case "matched":
        state.currentRoomId = data.room_id;
        state.matchedPeerName = data.peer_pseudonym || "Anonymous";
        state.isHumanPeer = !!data.is_human;
        state.currentModality = data.modality || "voice";

        if (state.currentModality === "voice" && state.isHumanPeer) {
          // Human-to-Human WebRTC Voice Call
          showView("voice");
          elements.voicePeerName.textContent = state.matchedPeerName;
          elements.voiceLangBadge.textContent = data.language || "Bilingual";
          elements.voicePeerAvatar.textContent = "👤";
          startCallTimer();

          const pc = await initializePeerConnection(data.role);
          if (!pc) return;

          if (data.role === "initiator") {
            const offer = await pc.createOffer();
            const modifiedSDP = applyOpusLowDataSDP(offer.sdp);
            await pc.setLocalDescription(new RTCSessionDescription({ type: "offer", sdp: modifiedSDP }));
            sendSignaling({ type: "offer", sdp: pc.localDescription.sdp });
          }
        } else if (state.currentModality === "voice" && !state.isHumanPeer) {
          // AI Voice Companion Session
          showView("voice");
          elements.voicePeerName.textContent = "Joy AI Companion";
          elements.voiceLangBadge.textContent = data.language || "Bilingual";
          elements.voicePeerAvatar.textContent = "🤖";
          startCallTimer();
        } else {
          // Text Chat Session (Human or AI)
          showView("text");
          elements.textPeerName.textContent = state.matchedPeerName;
          elements.textPeerSub.textContent = state.isHumanPeer ? "Direct Encrypted P2P" : "AI Companion Active";
          elements.textChatBox.innerHTML = "";
        }
        break;

      case "offer":
        if (state.peerConnection) {
          await state.peerConnection.setRemoteDescription(new RTCSessionDescription({ type: "offer", sdp: data.sdp }));
          const answer = await state.peerConnection.createAnswer();
          const modifiedSDP = applyOpusLowDataSDP(answer.sdp);
          await state.peerConnection.setLocalDescription(new RTCSessionDescription({ type: "answer", sdp: modifiedSDP }));
          sendSignaling({ type: "answer", sdp: state.peerConnection.localDescription.sdp });
        }
        break;

      case "answer":
        if (state.peerConnection) {
          await state.peerConnection.setRemoteDescription(new RTCSessionDescription({ type: "answer", sdp: data.sdp }));
        }
        break;

      case "ice_candidate":
        if (state.peerConnection && data.candidate) {
          try {
            await state.peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
          } catch (e) {
            console.warn("Error adding ICE candidate:", e);
          }
        }
        break;

      case "icebreaker_card":
        updateIcebreakerUI(data.topic);
        break;

      case "text_message":
        appendChatMessage(data.sender, data.text, data.sender === (state.user ? state.user.pseudonym : "You") ? "mine" : "peer");
        if (data.is_ai && state.currentModality === "voice") {
          speakWithWebSpeech(data.text);
        }
        break;

      case "session_ended":
        tearDownSession();
        showDiagnostic("SESSION_ENDED", data.message || "Session ended.");
        break;

      case "diagnostic":
        showDiagnostic(data.code, data.message);
        break;
    }
  }

  // --- In-Session Call Timer ---
  function startCallTimer() {
    state.callSeconds = 0;
    elements.voiceCallTimer.textContent = "00:00";
    if (state.callTimerInterval) clearInterval(state.callTimerInterval);
    state.callTimerInterval = setInterval(() => {
      state.callSeconds++;
      const m = String(Math.floor(state.callSeconds / 60)).padStart(2, "0");
      const s = String(state.callSeconds % 60).padStart(2, "0");
      elements.voiceCallTimer.textContent = `${m}:${s}`;
    }, 1000);
  }

  function stopCallTimer() {
    if (state.callTimerInterval) {
      clearInterval(state.callTimerInterval);
      state.callTimerInterval = null;
    }
  }

  // --- Tear Down Active Session ---
  function tearDownSession() {
    stopCallTimer();

    if (state.localStream) {
      state.localStream.getTracks().forEach(t => t.stop());
      state.localStream = null;
    }
    if (state.peerConnection) {
      state.peerConnection.close();
      state.peerConnection = null;
    }
    state.dataChannel = null;
    if (elements.remoteAudio) elements.remoteAudio.srcObject = null;
    showView("idle");
  }

  elements.btnEndVoice.addEventListener("click", () => {
    sendSignaling({ type: "end_session" });
    tearDownSession();
  });

  elements.btnEndText.addEventListener("click", () => {
    sendSignaling({ type: "end_session" });
    tearDownSession();
  });

  // --- Voice Controls (Mute / Unmute) ---
  elements.btnMuteMic.addEventListener("click", () => {
    if (!state.localStream) return;
    const audioTrack = state.localStream.getAudioTracks()[0];
    if (audioTrack) {
      audioTrack.enabled = !audioTrack.enabled;
      state.isMuted = !audioTrack.enabled;
      elements.micIcon.textContent = state.isMuted ? "🔇" : "🎙️";
      elements.btnMuteMic.style.backgroundColor = state.isMuted ? "var(--danger-color)" : "var(--secondary-bg)";
    }
  });

  // --- Switch from Voice to Text Modality ---
  function switchToTextModality() {
    state.currentModality = "text";
    showView("text");
    elements.textPeerName.textContent = state.matchedPeerName || "Joy AI";
    elements.textPeerSub.textContent = "Switched to Text Mode";
  }

  elements.btnVoiceToText.addEventListener("click", switchToTextModality);

  // --- Topic Icebreaker Deck Request ---
  function requestNextIcebreaker() {
    sendSignaling({ type: "request_icebreaker" });
  }

  elements.btnNextIcebreaker.addEventListener("click", requestNextIcebreaker);
  elements.btnNextIcebreakerText.addEventListener("click", () => {
    elements.textIcebreakerBanner.classList.remove("hidden");
    requestNextIcebreaker();
  });

  elements.btnCloseIcebreaker.addEventListener("click", () => {
    elements.textIcebreakerBanner.classList.add("hidden");
  });

  function updateIcebreakerUI(topic) {
    if (elements.icebreakerText) {
      elements.icebreakerText.textContent = `"${topic}"`;
    }
    if (elements.textIcebreakerContent) {
      elements.textIcebreakerContent.textContent = topic;
    }
  }

  // --- Text Chat Message Handling ---
  function sendChatMessage() {
    const text = elements.chatMsgInput.value.trim();
    if (!text) return;

    // Client-side PII Pre-flight guardrail
    const piiViolation = detectClientPII(text);
    if (piiViolation) {
      showDiagnostic("PII_BLOCKED", `🚫 Message blocked: Sharing ${piiViolation} is strictly prohibited.`);
      return;
    }

    appendChatMessage("You", text, "mine");
    elements.chatMsgInput.value = "";

    sendSignaling({
      type: "text_message",
      text: text
    });
  }

  elements.btnSendText.addEventListener("click", sendChatMessage);
  elements.chatMsgInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendChatMessage();
  });

  function appendChatMessage(author, text, cls) {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${cls}`;
    bubble.innerHTML = `<div class="bubble-author">${escapeHtml(author)}</div><div>${escapeHtml(text)}</div>`;
    elements.textChatBox.appendChild(bubble);
    elements.textChatBox.scrollTop = elements.textChatBox.scrollHeight;
  }

  // --- Browser-Native Web Speech Synthesis (AI Voice) ---
  function speakWithWebSpeech(text) {
    if (!("speechSynthesis" in window)) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = state.user ? (state.user.speech_rate || 1.0) : 1.0;

      // Select voice based on user's language code
      const voices = window.speechSynthesis.getVoices();
      const lang = state.user ? state.user.language : "tanglish";
      let langCode = "en-IN";
      if (lang === "hindi" || lang === "hinglish") langCode = "hi-IN";
      else if (lang === "tamil" || lang === "tanglish") langCode = "ta-IN";
      else if (lang === "telugu" || lang === "telugish") langCode = "te-IN";
      else if (lang === "spanish") langCode = "es-ES";
      else if (lang === "french") langCode = "fr-FR";

      const matchedVoice = voices.find(v => v.lang.startsWith(langCode));
      if (matchedVoice) utterance.voice = matchedVoice;

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("Speech synthesis error:", e);
    }
  }

  // --- Diagnostics Banner ---
  function showDiagnostic(code, message, actions = []) {
    elements.diagCode.textContent = code;
    elements.diagMsg.textContent = message;
    elements.diagActions.innerHTML = "";

    actions.forEach(action => {
      const btn = document.createElement("button");
      btn.className = "btn btn-xs btn-primary mt-2";
      btn.textContent = action.label;
      btn.addEventListener("click", () => {
        elements.diagnosticBanner.classList.add("hidden");
        action.action();
      });
      elements.diagActions.appendChild(btn);
    });

    elements.diagnosticBanner.classList.remove("hidden");
  }

  elements.btnCloseDiag.addEventListener("click", () => {
    elements.diagnosticBanner.classList.add("hidden");
  });

  // --- Utility Helpers ---
  function escapeHtml(string) {
    const div = document.createElement("div");
    div.innerText = string;
    return div.innerHTML;
  }

  // --- App Initialization Sequence ---
  async function initApp() {
    await loadConfig();
    await authenticate();
  }

  // Start initialization
  initApp();

})();