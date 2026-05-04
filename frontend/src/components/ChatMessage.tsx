"use client";

import type { ChatMessage as ChatMessageType } from "@/lib/types";
import { ChatActions } from "./ChatActions";

export function ChatMessage({ msg }: { msg: ChatMessageType }) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-xs font-mono ${
          isUser
            ? "bg-accent-purple/20 text-terminal-text"
            : "bg-terminal-surface text-terminal-text"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{msg.content}</p>
        {!isUser && (
          <ChatActions
            trades={msg.trades}
            watchlist_changes={msg.watchlist_changes}
          />
        )}
      </div>
    </div>
  );
}
