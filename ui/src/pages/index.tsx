import React, { useState } from "react";
import Head from "next/head";
import { ChatWindow, Message } from "../components/ChatWindow";
import { ChatInput } from "../components/ChatInput";
import { sendChat, isError, ChatMessage } from "../services/api";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSendMessage = async (content: string) => {
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    const context: ChatMessage[] = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({ role: m.role, content: m.content }));

    const response = await sendChat({ message: content, context });
    setLoading(false);

    if (isError(response)) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: response.error,
          timestamp: new Date(),
          isError: true,
        },
      ]);
    } else {
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.reply,
          timestamp: new Date(),
          latency_ms: response.metadata?.latency_ms,
        },
      ]);
    }
  };

  const handleClear = () => setMessages([]);

  return (
    <>
      <Head>
        <title>Aueshah — AI Concierge</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <div className="app">
        <div className="container">
          <header className="header">
            <div className="logo">Au</div>
            <div className="header-text">
              <h1>Aueshah Concierge</h1>
              <span className="status">
                <span className="status-dot" />
                Online · Luxury fine jewelry
              </span>
            </div>
            <div className="header-actions">
              <button onClick={handleClear} disabled={messages.length === 0}>
                New chat
              </button>
            </div>
          </header>

          <ChatWindow
            messages={messages}
            loading={loading}
            onSuggestion={handleSendMessage}
          />

          <ChatInput onSend={handleSendMessage} disabled={loading} />
        </div>
      </div>
    </>
  );
}
