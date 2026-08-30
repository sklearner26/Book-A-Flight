let currentThreadId = localStorage.getItem("travel_thread_id") || null;
let latestAnswerMarkdown = "";
let latestTraceData = [];
let pipelineTimerInterval = null;
let pipelineStartTime = null;

// Pipeline Node IDs
const AGENT_ORDER = ["validator_agent", "flight_agent", "hotel_agent", "itinerary_agent", "final_agent"];
const AGENT_META = {
    validator_agent: { name: "Trip Validator", icon: "🧭", sub: "Checking route & intent" },
    flight_agent: { name: "Flight Finder", icon: "✈️", sub: "Checking live flight routes" },
    hotel_agent: { name: "Hotel Scout", icon: "🏨", sub: "Finding top-rated stays" },
    itinerary_agent: { name: "Itinerary Planner", icon: "🗺️", sub: "Crafting daily activities" },
    final_agent: { name: "Trip Concierge", icon: "📋", sub: "Organizing budget & tips" }
};

function setPrompt(text) {
    const input = document.getElementById("userInput");
    input.value = text;
    input.focus();
}

function switchTab(tabName) {
    // Buttons
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    const activeBtn = document.getElementById(`tabBtn${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
    if (activeBtn) activeBtn.classList.add("active");

    // Panels
    document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
    const targetPanel = document.getElementById(`view${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
    if (targetPanel) targetPanel.classList.add("active");
}

function setLoading(isLoading) {
    const sendBtn = document.getElementById("sendBtn");
    const btnText = document.getElementById("btnText");
    const btnLoader = document.getElementById("btnLoader");
    const systemStatus = document.getElementById("systemStatus");
    const statusText = document.getElementById("statusText");

    sendBtn.disabled = isLoading;

    if (isLoading) {
        btnText.classList.add("hidden");
        btnLoader.classList.remove("hidden");
        systemStatus.classList.add("busy");
        statusText.textContent = "Your travel team is planning...";
    } else {
        btnText.classList.remove("hidden");
        btnLoader.classList.add("hidden");
        systemStatus.classList.remove("busy");
        statusText.textContent = "5 Travel Guides Ready";
    }
}

function showError(message) {
    const errorBox = document.getElementById("errorBox");
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
}

function hideError() {
    const errorBox = document.getElementById("errorBox");
    errorBox.classList.add("hidden");
    errorBox.textContent = "";
}

function addConsoleLog(level, message, timestamp = null) {
    const consoleBody = document.getElementById("consoleBody");
    if (!consoleBody) return;

    const time = timestamp || new Date().toTimeString().split(" ")[0];
    const line = document.createElement("div");
    line.className = `log-line ${level}`;
    line.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-tag">[${level.toUpperCase()}]</span> ${escapeHtml(message)}`;

    consoleBody.appendChild(line);
    consoleBody.scrollTop = consoleBody.scrollHeight;
}

function clearConsole() {
    const consoleBody = document.getElementById("consoleBody");
    if (consoleBody) {
        consoleBody.innerHTML = '<div class="log-line info"><span class="log-time">[' + new Date().toTimeString().split(" ")[0] + ']</span> <span class="log-tag">[READY]</span> Activity log cleared.</div>';
    }
}

function startPipelineVisualizer() {
    const pipelineSec = document.getElementById("pipelineSection");
    pipelineSec.classList.remove("hidden");

    AGENT_ORDER.forEach((agentId, idx) => {
        const node = document.getElementById(`node-${agentId}`);
        const badge = document.getElementById(`badge-${agentId}`);
        if (node) {
            node.className = "agent-node";
        }
        if (badge) {
            badge.textContent = "Waiting";
        }
        const arrow = document.getElementById(`arrow-${idx + 1}`);
        if (arrow) arrow.classList.remove("active");
    });

    // Start with Trip Validator active
    setNodeState("validator_agent", "running", "Validating...");

    pipelineStartTime = Date.now();
    const timerElem = document.getElementById("pipelineTimer");
    if (pipelineTimerInterval) clearInterval(pipelineTimerInterval);

    pipelineTimerInterval = setInterval(() => {
        const elapsed = ((Date.now() - pipelineStartTime) / 1000).toFixed(1);
        timerElem.textContent = `Time elapsed: ${elapsed}s`;
    }, 100);
}

function stopPipelineVisualizer() {
    if (pipelineTimerInterval) {
        clearInterval(pipelineTimerInterval);
        pipelineTimerInterval = null;
    }
}

function setNodeState(agentId, state, badgeText) {
    const node = document.getElementById(`node-${agentId}`);
    const badge = document.getElementById(`badge-${agentId}`);
    if (node) {
        node.className = `agent-node ${state}`;
    }
    if (badge && badgeText) {
        badge.textContent = badgeText;
    }

    // Update arrows
    const idx = AGENT_ORDER.indexOf(agentId);
    if (idx >= 0 && idx < AGENT_ORDER.length - 1) {
        const arrow = document.getElementById(`arrow-${idx + 1}`);
        if (arrow) {
            if (state === "completed" || state === "running") {
                arrow.classList.add("active");
            }
        }
    }
}

function escapeHtml(str) {
    if (typeof str !== "string") return str;
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderTraceCards(trace) {
    latestTraceData = trace;
    const container = document.getElementById("traceCardsContainer");
    const countBadge = document.getElementById("traceCountBadge");

    if (countBadge) countBadge.textContent = trace.length;
    if (!container) return;

    container.innerHTML = "";

    trace.forEach((step, index) => {
        const card = document.createElement("div");
        card.className = "trace-card open";
        card.id = `trace-card-${step.agent_id}`;

        // Observations HTML (Humanized)
        let obsHtml = "";
        if (step.observations && Object.keys(step.observations).length > 0) {
            obsHtml = `
                <div class="trace-section-block">
                    <div class="trace-section-title">📍 Key Findings & Discoveries</div>
                    <div class="observations-grid">
                        ${Object.entries(step.observations).map(([k, v]) => `
                            <div class="obs-chip">
                                <span class="obs-key">${escapeHtml(k.replace(/_/g, ' '))}:</span>
                                <span class="obs-val">${escapeHtml(String(v))}</span>
                            </div>
                        `).join("")}
                    </div>
                </div>
            `;
        }

        // Thoughts HTML (Humanized)
        let thoughtsHtml = "";
        if (step.thoughts && step.thoughts.length > 0) {
            thoughtsHtml = `
                <div class="trace-section-block">
                    <div class="trace-section-title">💡 Guide's Strategy & Thought Process</div>
                    <div class="reasoning-box">${escapeHtml(step.reasoning || "")}</div>
                    <ul class="thought-list">
                        ${step.thoughts.map(t => `<li class="thought-item">${escapeHtml(t)}</li>`).join("")}
                    </ul>
                </div>
            `;
        }

        // Tool Calls HTML (Humanized)
        let toolCallsHtml = "";
        if (step.tool_calls && step.tool_calls.length > 0) {
            toolCallsHtml = `
                <div class="trace-section-block">
                    <div class="trace-section-title">🔍 Searches & Data Checked</div>
                    ${step.tool_calls.map(tc => `
                        <div class="tool-box">
                            <div class="tool-header">
                                <span class="tool-name">⚡ ${escapeHtml(tc.tool_name)}</span>
                                <span class="tool-status">${escapeHtml(tc.status)} (${tc.duration_sec || "0.0"}s)</span>
                            </div>
                            <div class="tool-code"><strong>Search Request:</strong>\n${escapeHtml(JSON.stringify(tc.input, null, 2))}\n\n<strong>Results Found:</strong>\n${escapeHtml(tc.output_preview || "Information gathered successfully.")}</div>
                        </div>
                    `).join("")}
                </div>
            `;
        }

        // Raw Output Collapsible (Humanized)
        let rawOutputHtml = "";
        if (step.raw_output) {
            rawOutputHtml = `
                <div class="trace-section-block">
                    <div class="raw-output-collapse" onclick="this.classList.toggle('open')">
                        <div class="raw-output-header">
                            <span>📄 View Full Planning Notes for This Step</span>
                            <span>▾</span>
                        </div>
                        <div class="raw-output-content">${escapeHtml(step.raw_output)}</div>
                    </div>
                </div>
            `;
        }

        // Logs HTML (Humanized)
        let logsHtml = "";
        if (step.logs && step.logs.length > 0) {
            logsHtml = `
                <div class="trace-section-block">
                    <div class="trace-section-title">📝 Activity Log</div>
                    <div class="step-logs-list">
                        ${step.logs.map(l => `
                            <div class="step-log-line ${l.level}">
                                <span>[${l.timestamp}]</span>
                                <span>[${l.level.toUpperCase()}]</span>
                                <span>${escapeHtml(l.message)}</span>
                            </div>
                        `).join("")}
                    </div>
                </div>
            `;
        }

        // Friendly role / title fallback
        const friendlyName = AGENT_META[step.agent_id]?.name || step.agent_name;
        const friendlyRole = AGENT_META[step.agent_id]?.sub || step.role;

        card.innerHTML = `
            <div class="trace-card-header" onclick="toggleTraceCard('${step.agent_id}')">
                <div class="trace-card-left">
                    <div class="trace-agent-icon">${step.icon || "🧭"}</div>
                    <div class="trace-agent-info">
                        <h4>${escapeHtml(friendlyName)}</h4>
                        <div class="trace-agent-role">${escapeHtml(friendlyRole)}</div>
                    </div>
                </div>
                <div class="trace-card-right">
                    <span class="trace-latency-tag">⏱️ ${step.duration_sec || 0}s</span>
                    <span class="trace-status-tag">✓ Complete</span>
                    <span class="trace-toggle-arrow">▼</span>
                </div>
            </div>
            <div class="trace-card-body">
                ${thoughtsHtml}
                ${obsHtml}
                ${toolCallsHtml}
                ${rawOutputHtml}
                ${logsHtml}
            </div>
        `;

        container.appendChild(card);
    });
}

function toggleTraceCard(agentId) {
    const card = document.getElementById(`trace-card-${agentId}`);
    if (card) {
        card.classList.toggle("open");
    }
}

function expandAllTraceCards(expand = true) {
    document.querySelectorAll(".trace-card").forEach(c => {
        if (expand) c.classList.add("open");
        else c.classList.remove("open");
    });
}

function focusAgentCard(agentId) {
    switchTab("observability");
    const card = document.getElementById(`trace-card-${agentId}`);
    if (card) {
        card.classList.add("open");
        card.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

function showResult(answer, threadId, llmCalls = 0, runtimeSec = 0, trace = []) {
    latestAnswerMarkdown = answer;

    const resultSection = document.getElementById("resultSection");
    const resultBox = document.getElementById("resultBox");
    const threadInfo = document.getElementById("threadInfo");
    const llmCallsInfo = document.getElementById("llmCallsInfo");
    const totalTimeInfo = document.getElementById("totalTimeInfo");

    if (typeof marked !== "undefined") {
        resultBox.innerHTML = marked.parse(answer);
    } else {
        resultBox.innerText = answer;
    }

    if (threadInfo) threadInfo.textContent = threadId || "-";
    if (llmCallsInfo) llmCallsInfo.textContent = llmCalls || 0;
    if (totalTimeInfo) totalTimeInfo.textContent = `${runtimeSec}s`;

    if (trace && trace.length > 0) {
        renderTraceCards(trace);
    }

    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function sendMessage() {
    hideError();

    const input = document.getElementById("userInput");
    const message = input.value.trim();

    if (!message) {
        showError("Please let us know where you'd like to travel before starting.");
        return;
    }

    setLoading(true);
    startPipelineVisualizer();
    addConsoleLog("info", `Trip request started: "${message}"`);

    const requestStartTime = Date.now();

    try {
        // Use Streaming Response for live telemetry
        const response = await fetch("/api/travel/stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                thread_id: currentThreadId
            })
        });

        if (!response.ok) {
            throw new Error(`Server response error (${response.status})`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalData = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop(); // Keep unfinished line in buffer

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const jsonStr = line.slice(6).trim();
                    if (!jsonStr) continue;

                    try {
                        const eventData = JSON.parse(jsonStr);

                        if (eventData.event === "agent_step") {
                            const step = eventData.step_trace;
                            const agentId = step.agent_id;
                            const friendlyName = AGENT_META[agentId]?.name || step.agent_name;

                            addConsoleLog("success", `[${friendlyName}] finished research in ${step.duration_sec}s.`);
                            if (step.logs) {
                                step.logs.forEach(l => addConsoleLog(l.level, `[${friendlyName}] ${l.message}`, l.timestamp));
                            }

                            if (step.status === "clarification_needed") {
                                // Mark validator as clarification needed and pause further agent steps
                                setNodeState(agentId, "completed", "ℹ️ Clarify");
                                addConsoleLog("warn", `[${friendlyName}] Clarification requested: Please provide missing route or travel details.`);
                            } else {
                                // Mark node completed
                                setNodeState(agentId, "completed", `✓ ${step.duration_sec}s`);

                                // Set next node running
                                const currentIdx = AGENT_ORDER.indexOf(agentId);
                                if (currentIdx >= 0 && currentIdx < AGENT_ORDER.length - 1) {
                                    const nextAgent = AGENT_ORDER[currentIdx + 1];
                                    setNodeState(nextAgent, "running", "Planning...");
                                }
                            }

                            // Render intermediate trace
                            renderTraceCards(eventData.accumulated_trace);

                        } else if (eventData.event === "complete") {
                            finalData = eventData;
                        } else if (eventData.event === "error") {
                            throw new Error(eventData.error || "Something went wrong while planning your trip.");
                        }
                    } catch (e) {
                        console.error("Error processing stream chunk:", e, line);
                    }
                }
            }
        }

        const totalRuntime = ((Date.now() - requestStartTime) / 1000).toFixed(1);
        stopPipelineVisualizer();

        if (finalData) {
            currentThreadId = finalData.thread_id;
            localStorage.setItem("travel_thread_id", currentThreadId);

            if (finalData.is_valid !== false) {
                AGENT_ORDER.forEach(a => {
                    const node = document.getElementById(`node-${a}`);
                    if (!node.classList.contains("completed")) {
                        setNodeState(a, "completed", "✓ Ready");
                    }
                });
                addConsoleLog("success", `Your complete travel plan is ready! (Built in ${totalRuntime}s)`);
            } else {
                addConsoleLog("warn", `Trip Validator has asked for additional travel details.`);
            }

            showResult(finalData.answer, finalData.thread_id, finalData.llm_calls, totalRuntime, finalData.trace);
        }

    } catch (error) {
        console.error("Travel guide planning error:", error);
        stopPipelineVisualizer();
        showError(error.message || "We couldn't complete the travel plan. Please check your internet or try again.");
        addConsoleLog("error", `Planning paused: ${error.message}`);
    } finally {
        setLoading(false);
    }
}

function copyResult() {
    const resultBox = document.getElementById("resultBox");
    const text = resultBox ? resultBox.innerText : "";

    if (!text) return;

    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector(".action-btn.secondary[title*='Copy Markdown']");
        if (btn) {
            const old = btn.textContent;
            btn.textContent = "✓ Copied!";
            setTimeout(() => { btn.textContent = old; }, 1500);
        }
    }).catch(() => {
        showError("Could not copy plan text.");
    });
}

function copyTraceJSON() {
    if (!latestTraceData || latestTraceData.length === 0) {
        showError("No trace telemetry data available yet.");
        return;
    }

    const jsonStr = JSON.stringify(latestTraceData, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
        const btn = document.querySelector(".action-btn.secondary[title*='Copy entire telemetry']");
        if (btn) {
            const old = btn.textContent;
            btn.textContent = "✓ JSON Copied!";
            setTimeout(() => { btn.textContent = old; }, 1500);
        }
    }).catch(() => {
        showError("Could not copy JSON trace.");
    });
}

function downloadPDF() {
    const pdfContent = document.getElementById("pdfContent");

    if (!latestAnswerMarkdown || !pdfContent) {
        showError("No travel plan available to download.");
        return;
    }

    const downloadBtn = document.querySelector(".action-btn.primary");
    const oldText = downloadBtn.textContent;

    downloadBtn.textContent = "Generating PDF...";
    downloadBtn.disabled = true;

    const options = {
        margin: 0.5,
        filename: "aether-voyage-expedition-dossier.pdf",
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: "#ffffff" },
        jsPDF: { unit: "in", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["avoid-all", "css", "legacy"] }
    };

    html2pdf().set(options).from(pdfContent).save()
        .then(() => {
            downloadBtn.textContent = oldText;
            downloadBtn.disabled = false;
        })
        .catch(() => {
            downloadBtn.textContent = oldText;
            downloadBtn.disabled = false;
            showError("Could not generate PDF.");
        });
}

document.addEventListener("keydown", function(event) {
    if (event.ctrlKey && event.key === "Enter") {
        sendMessage();
    }
});