"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, TextArea, Button, Spinner, Avatar } from "@heroui/react";
import { Send, Bot, User, Sparkles } from "lucide-react";
import { AgentTrace, TraceEvent } from "@/components/AgentTrace";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  traces?: TraceEvent[];
}

export default function JaqpotStudioPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;

    const userQuery = input.trim();
    setInput("");

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userQuery,
    };

    const assistantMsgId = (Date.now() + 1).toString();
    const initialAssistantMessage: Message = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      traces: [],
    };

    setMessages((prev) => [...prev, userMessage, initialAssistantMessage]);
    setIsLoading(true);

    try {
      const response = await fetch(
        `http://localhost:8000/agent/stream?query=${encodeURIComponent(userQuery)}`
      );

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status} (${response.statusText})`);
      }

      if (!response.body) throw new Error("ReadableStream not supported by this browser.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || "";
        for (const block of blocks) {
          if (!block.trim()) continue;

          let eventType = "message";
          let dataLines: string[] = [];

          for (const line of block.split(/\r?\n/)) {
            const trimmed = line.trim();
            if (trimmed.startsWith("event:")) {
              eventType = trimmed.replace(/^event:\s*/, "").trim();
            } else if (trimmed.startsWith("data:")) {
              dataLines.push(trimmed.replace(/^data:\s*/, ""));
            }
          }

          if (dataLines.length === 0) continue;

          const rawData = dataLines.join("\n");

          try {
            const parsed = JSON.parse(rawData);

            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id !== assistantMsgId) return msg;

                if (eventType === "final_answer") {
                  return { ...msg, content: msg.content + (parsed.token || "") };
                }

                if (["tool_call", "chunk_result", "verifier"].includes(eventType)) {
                  const newTrace: TraceEvent = { type: eventType as any, data: parsed };
                  return { ...msg, traces: [...(msg.traces || []), newTrace] };
                }

                return msg;
              })
            );
          } catch (parseErr) {
            console.warn("Could not parse SSE JSON payload:", rawData, parseErr);
          }
        }
      }
    } catch (err: any) {
      console.error("SSE stream error:", err);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
              ...msg,
              content:
                msg.content ||
                `⚠️ Error connecting to research backend: ${err?.message || "Connection refused"}. Please check that the backend is running on http://localhost:8000.`,
            }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-black text-foreground antialiased">
      {/* Jaqpot Studio Navigation Header */}
      <header className="border-b border-divider/40 px-6 py-3 flex items-center justify-between bg-content1/20 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg text-primary">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide">Jaqpot LLM Playground</h1>
            <p className="text-[11px] text-default-400 font-mono">Agentic RAG • Llama-3.3-70B • FastMCP</p>
          </div>
        </div>
      </header>

      {/* Main Chat Scroll Container */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 max-w-4xl w-full mx-auto">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <Card className="max-w-md bg-content1/40 border border-divider/60 shadow-xl">
              <CardContent className="text-center p-8 space-y-3">
                <Avatar color="accent" className="mx-auto mb-2">
                  <Bot className="w-6 h-6" />
                </Avatar>
                <h2 className="font-semibold text-lg">Agentic Research Assistant</h2>
                <p className="text-xs text-default-400 leading-relaxed">
                  Search biomedical & arXiv papers using hybrid retrieval (BM25 + pgvector + cross-encoder) with self-verification.
                </p>
              </CardContent>
            </Card>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === "user";
            return (
              <div key={msg.id} className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
                {!isUser && (
                  <Avatar color="default" size="sm">
                    <Bot className="w-4 h-4" />
                  </Avatar>
                )}

                <div className={`max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
                  {/* Render Execution Traces if available */}
                  {!isUser && msg.traces && msg.traces.length > 0 && (
                    <AgentTrace events={msg.traces} />
                  )}

                  <Card
                    className={`shadow-none border ${isUser
                      ? "bg-primary text-primary-foreground border-primary-500/30"
                      : "bg-content1/80 border-divider text-content1-foreground"
                      }`}
                  >
                    <CardContent className="p-3.5 text-sm whitespace-pre-wrap leading-relaxed">
                      {msg.content || (isLoading && !isUser && msg.traces?.length === 0 ? (
                        <div className="flex items-center gap-2 text-default-400 text-xs">
                          <Spinner size="sm" color="current" /> Initializing agent reasoning loop...
                        </div>
                      ) : null)}
                    </CardContent>
                  </Card>
                </div>

                {isUser && (
                  <Avatar color="accent" size="sm">
                    <User className="w-4 h-4" />
                  </Avatar>
                )}
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form Bar */}
      <div className="border-t border-divider/40 p-4 bg-content1/10">
        <div className="max-w-4xl mx-auto flex gap-3 items-end">
          <TextArea
            rows={2}
            placeholder="Ask a research question... (Press Enter to send)"
            value={input}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-content1/50 border border-divider/60 rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary/80 transition-colors resize-none"
          />
          <Button
            variant="primary"
            isDisabled={isLoading}
            onClick={handleSubmit}
            className="h-12 px-5 font-medium shadow-md cursor-pointer flex items-center justify-center"
          >
            {isLoading ? <Spinner size="sm" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}