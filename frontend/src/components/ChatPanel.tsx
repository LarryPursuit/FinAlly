"use client";

import { useState, useRef, useEffect } from "react";
import { useChat } from "@/contexts/ChatContext";
import { ChatMessage } from "./ChatMessage";

export function ChatPanel() {
  const { messages, sending, sendMessage } = useChat();
  const [input, setInput] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    await sendMessage(text);
  };

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="flex items-center justify-center w-10 h-full bg-terminal-surface border-l border-terminal-border text-terminal-muted hover:text-accent-yellow transition-colors"
        title="Open chat"
      >
        <span className="text-xs font-mono [writing-mode:vertical-rl] rotate-180">
          AI Chat
        </span>
      </button>
    );
  }

  return (
    <div className="flex flex-col h-full border-l border-terminal-border bg-terminal-surface w-80">
      <div className="flex items-center justify-between px-3 py-2 border-b border-terminal-border">
        <h2 className="text-xs font-mono uppercase tracking-wider text-terminal-muted">
          AI Chat
        </h2>
        <button
          onClick={() => setCollapsed(true)}
          className="text-terminal-muted hover:text-terminal-text text-xs"
          title="Collapse"
        >
          ✕
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <p className="text-terminal-muted text-xs font-mono text-center mt-8">
            Ask me about your portfolio, or tell me to execute trades.
          </p>
        )}
        {messages.map((msg) => (
          <ChatMessage key={msg.id} msg={msg} />
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="bg-terminal-surface border border-terminal-border rounded-lg px-3 py-2 text-xs font-mono text-terminal-muted animate-pulse">
              Thinking...
            </div>
          </div>
        )}
      </div>

      <div className="p-2 border-t border-terminal-border">
        <div className="flex gap-1">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Ask FinAlly..."
            className="flex-1 bg-terminal-bg border border-terminal-border rounded px-2 py-1.5 text-xs font-mono text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-accent-purple"
            disabled={sending}
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="px-3 py-1.5 text-xs font-mono bg-accent-purple/20 text-accent-purple rounded hover:bg-accent-purple/30 disabled:opacity-40 transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
