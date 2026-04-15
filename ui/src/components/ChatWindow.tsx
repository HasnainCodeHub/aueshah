import React, { useEffect, useRef } from "react";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  latency_ms?: number;
  isError?: boolean;
}

interface ChatWindowProps {
  messages: Message[];
  loading?: boolean;
  onSuggestion?: (text: string) => void;
}

const SUGGESTIONS = [
  "Tell me about the Noor Collection",
  "What collections do you offer?",
  "How does a bespoke piece work?",
  "Book a virtual appointment",
];

function formatTime(d: Date) {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  loading,
  onSuggestion,
}) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="chat-window">
      {messages.length === 0 && !loading ? (
        <div className="chat-empty">
          <div className="hero">Au</div>
          <h2>Aueshah Concierge</h2>
          <p>
            Ask about our collections, bespoke design, appointments, or care.
            I provide concise, grounded guidance — and refer you to our team
            when a human touch is needed.
          </p>
          {onSuggestion && (
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="suggestion"
                  onClick={() => onSuggestion(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="messages">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`row ${msg.role} ${msg.isError ? "error" : ""}`}
            >
              <div className={`avatar ${msg.role}`}>
                {msg.role === "user" ? "U" : "AI"}
              </div>
              <div className="bubble-wrap">
                <div className="bubble">{msg.content}</div>
                <div className="meta">
                  {formatTime(msg.timestamp)}
                  {msg.latency_ms != null && msg.role === "assistant"
                    ? ` · ${msg.latency_ms}ms`
                    : ""}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="row assistant">
              <div className="avatar assistant">AI</div>
              <div className="bubble">
                <div className="typing">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}

          <div ref={endRef} />
        </div>
      )}
    </div>
  );
};
