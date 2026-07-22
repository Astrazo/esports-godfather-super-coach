import { api, showNotice } from "./global.js";

const enabledPlaceholder = "What are your thoughts on Babe?";
const disabledPlaceholder = "Configure a language model to enable coach chat.";
let resizeFrame;
let lastCoachHeight = 110;

export function bindCoach() {
    const chat = document.getElementById("coach-chat");
    const clearButton = document.getElementById("clear-coach");

    applyCoachTheme(chat);
    chat.addEventListener("render", () => {
        chat.style.height = `${lastCoachHeight}px`;
        scheduleCoachResize(chat);
    });
    chat.addEventListener("new-message", () => scheduleCoachResize(chat));
    chat.addEventListener("messages-cleared", () => scheduleCoachResize(chat));
    window.addEventListener("resize", () => scheduleCoachResize(chat));
    chat.requestBodyLimits = { maxMessages: 1 };
    chat.connect = {
        stream: true,
        handler: async (body, signals) => {
            const message = body.messages?.at(-1)?.text?.trim();
            if (!message) {
                signals.onResponse({ error: "Enter a message before sending." });
                return;
            }

            const controller = new AbortController();
            signals.stopClicked.listener = () => controller.abort();
            clearButton.disabled = true;
            try {
                const response = await fetch("/api/coach", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message }),
                    signal: controller.signal,
                });
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || "The coach could not respond.");
                }

                signals.onOpen();
                await readCoachStream(response, signals);
            } catch (error) {
                if (error.name !== "AbortError") {
                    showNotice(error.message, true);
                    await signals.onResponse({ error: error.message });
                }
            } finally {
                clearButton.disabled = false;
                signals.onClose();
            }
        },
    };

    clearButton.onclick = async () => {
        clearButton.disabled = true;
        try {
            const result = await api("/api/coach", { method: "DELETE" });
            if (result) chat.clearMessages(false);
        } finally {
            clearButton.disabled = false;
        }
    };
}

async function readCoachStream(response, signals) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
            if (!line) continue;
            const chunk = JSON.parse(line);
            if (chunk.error) throw new Error(chunk.error);
            if (chunk.text) await signals.onResponse({ text: chunk.text });
        }

        if (done) break;
    }

    if (buffer) {
        const chunk = JSON.parse(buffer);
        if (chunk.error) throw new Error(chunk.error);
        if (chunk.text) await signals.onResponse({ text: chunk.text });
    }
}

export function renderCoach(messages) {
    const chat = document.getElementById("coach-chat");
    chat.style.visibility = "hidden";
    chat.history = messages.map((message) => ({
        role: message.role === "assistant" ? "ai" : message.role,
        text: message.content,
    }));
    scheduleCoachResize(chat);
}

export function setCoachEnabled(enabled) {
    const chat = document.getElementById("coach-chat");
    chat.textInput = {
        ...chat.textInput,
        disabled: !enabled,
        placeholder: {
            text: enabled ? enabledPlaceholder : disabledPlaceholder,
            style: { color: "#9ba8bc" },
        },
    };
}

function applyCoachTheme(chat) {
    chat.chatStyle = {
        width: "100%",
        border: "1px solid #30394b",
        borderRadius: "12px",
        backgroundColor: "#171c26",
    };
    chat.messageStyles = {
        default: {
            shared: {
                bubble: {
                    maxWidth: "82%",
                    color: "#edf1f7",
                    borderRadius: "12px",
                    overflowWrap: "anywhere",
                },
            },
            user: {
                bubble: { backgroundColor: "#27446a" },
            },
            ai: {
                bubble: { backgroundColor: "#202736" },
            },
        },
        loading: {
            message: {
                styles: {
                    bubble: {
                        backgroundColor: "#202736",
                        color: "#9ba8bc",
                    },
                },
            },
        },
    };
    chat.textInput = {
        placeholder: {
            text: enabledPlaceholder,
            style: { color: "#9ba8bc" },
        },
        styles: {
            text: { color: "#edf1f7" },
            container: {
                backgroundColor: "#202736",
                border: "1px solid #30394b",
                borderRadius: "9px",
            },
            focus: { border: "1px solid #4f8ee8" },
        },
    };
}

function scheduleCoachResize(chat) {
    window.cancelAnimationFrame(resizeFrame);
    resizeFrame = window.requestAnimationFrame(() => resizeCoach(chat));
}

function resizeCoach(chat) {
    const messages = chat.shadowRoot?.getElementById("messages");
    const input = chat.shadowRoot?.getElementById("input");
    if (!messages || !input) return;

    const currentMessages = typeof chat.getMessages === "function" ? chat.getMessages() : [];
    if (currentMessages.length && !messages.children.length) {
        chat.style.height = `${lastCoachHeight}px`;
        scheduleCoachResize(chat);
        return;
    }

    const messagesHeight = [...messages.children].reduce((height, message) => {
        return height + message.getBoundingClientRect().height + 10;
    }, 0);
    const desiredHeight = messagesHeight + input.getBoundingClientRect().height + 28;
    const maximumHeight = Math.max(240, Math.min(680, window.innerHeight - 230));
    lastCoachHeight = Math.min(Math.max(desiredHeight, 110), maximumHeight);
    chat.style.height = `${lastCoachHeight}px`;
    chat.style.visibility = "visible";
}
