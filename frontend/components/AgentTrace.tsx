"use client";

import { Card, Chip, Accordion } from "@heroui/react";
import { Terminal, Database, CheckCircle2, AlertTriangle, Search } from "lucide-react";

export interface TraceEvent {
    type: "tool_call" | "chunk_result" | "verifier";
    data: any;
}

export function AgentTrace({ events }: { events: TraceEvent[] }) {
    if (events.length === 0) return null;

    return (
        <Card className="my-2 bg-content1/50 border border-divider shadow-none">
            <Card.Content className="p-2">
                <Accordion className="px-0">
                    <Accordion.Item id="trace">
                        <Accordion.Heading>
                            <Accordion.Trigger className="flex items-center justify-between w-full py-2 text-xs font-mono text-default-600 cursor-pointer">
                                <div className="flex items-center gap-2">
                                    <Terminal className="w-4 h-4 text-primary" />
                                    <span>Agent Reasoning Trace ({events.length} steps)</span>
                                </div>
                                <Accordion.Indicator />
                            </Accordion.Trigger>
                        </Accordion.Heading>
                        <Accordion.Panel>
                            <Accordion.Body className="space-y-2 py-1 text-xs font-mono">
                                {events.map((event, idx) => {
                                    if (event.type === "tool_call") {
                                        return (
                                            <div key={idx} className="flex items-center gap-2 bg-content2/50 p-2 rounded-md">
                                                <Search className="w-3.5 h-3.5 text-warning" />
                                                <span className="font-semibold text-warning">Tool Call:</span>
                                                <span>{event.data.tool}</span>
                                                <span className="text-default-400">({JSON.stringify(event.data.args)})</span>
                                            </div>
                                        );
                                    }

                                    if (event.type === "chunk_result") {
                                        return (
                                            <div key={idx} className="flex items-center gap-2 bg-content2/50 p-2 rounded-md">
                                                <Database className="w-3.5 h-3.5 text-secondary" />
                                                <span className="font-semibold text-secondary">Retrieved Context:</span>
                                                <span className="truncate">{event.data.title}</span>
                                                <Chip size="sm" variant="soft" color="accent" className="h-5 text-[10px]">
                                                    p. {event.data.page || 1}
                                                </Chip>
                                            </div>
                                        );
                                    }

                                    if (event.type === "verifier") {
                                        const isVerified = event.data.verdict === "VERIFIED";
                                        return (
                                            <div key={idx} className="flex items-center gap-2 bg-content2/50 p-2 rounded-md">
                                                {isVerified ? (
                                                    <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                                                ) : (
                                                    <AlertTriangle className="w-3.5 h-3.5 text-danger" />
                                                )}
                                                <span className={isVerified ? "font-semibold text-success" : "font-semibold text-danger"}>
                                                    Verifier Status: {event.data.verdict}
                                                </span>
                                                {event.data.flagged_claims?.length > 0 && (
                                                    <span className="text-danger-400">Flagged: {event.data.flagged_claims.join(", ")}</span>
                                                )}
                                            </div>
                                        );
                                    }

                                    return null;
                                })}
                            </Accordion.Body>
                        </Accordion.Panel>
                    </Accordion.Item>
                </Accordion>
            </Card.Content>
        </Card>
    );
}