"use client";

import { Card, Avatar } from "@heroui/react";

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
}

export function ChatMessage({ message }: { message: Message }) {
    const isUser = message.role === "user";

    return (
        <div
            className={`flex gap-3 my-3 ${isUser ? "flex-row-reverse" : "flex-row"
                }`}
        >
            <Avatar
                className={`text-xs ring-2 ${isUser ? "ring-primary" : "ring-secondary"
                    }`}
            >
                <Avatar.Fallback>{isUser ? "You" : "AI"}</Avatar.Fallback>
            </Avatar>
            <Card
                className={`max-w-[80%] shadow-sm ${isUser
                    ? "bg-primary text-primary-foreground"
                    : "bg-content2 text-content2-foreground"
                    }`}
            >
                <Card.Content className="p-3 text-sm whitespace-pre-wrap leading-relaxed">
                    {message.content}
                </Card.Content>
            </Card>
        </div>
    );
}