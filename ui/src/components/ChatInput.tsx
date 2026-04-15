import React, { useRef, useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const autoGrow = (el: HTMLTextAreaElement) => {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 140) + "px";
};

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [input, setInput] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const v = input.trim();
    if (!v || disabled) return;
    onSend(v);
    setInput("");
    if (taRef.current) {
      taRef.current.style.height = "auto";
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    autoGrow(e.target);
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="chat-input-form"
    >
      <textarea
        ref={taRef}
        value={input}
        onChange={handleChange}
        onKeyDown={handleKey}
        placeholder="Ask about collections, bespoke design, appointments…"
        disabled={disabled}
        className="chat-input"
        rows={1}
        cols={1}
        wrap="soft"
      />
      <button
        type="submit"
        disabled={disabled || !input.trim()}
        className="send-button"
        aria-label="Send"
        title="Send"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 2L11 13" />
          <path d="M22 2l-7 20-4-9-9-4 20-7z" />
        </svg>
      </button>
    </form>
  );
};
