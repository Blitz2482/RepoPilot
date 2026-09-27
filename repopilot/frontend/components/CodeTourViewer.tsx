"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { ChevronLeft, ChevronRight, FileCode, BookOpen } from "lucide-react";

interface TourStep {
    step: number;
    title: string;
    path: string;
    start: number;
    end: number;
    narration: string;
    code?: string;
}

interface CodeTourViewerProps {
    steps: TourStep[];
    activeStepIndex?: number; // NEW: Allow external control
}

export function CodeTourViewer({ steps, activeStepIndex }: CodeTourViewerProps) {
    const [internalStepIndex, setInternalStepIndex] = useState(0);

    // Use external prop if provided, otherwise use internal state
    const currentStepIndex = activeStepIndex !== undefined ? activeStepIndex : internalStepIndex;

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key.toLowerCase() === "j") handleNext();
            if (e.key.toLowerCase() === "k") handlePrev();
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [currentStepIndex]);

    const handleNext = () => {
        if (currentStepIndex < steps.length - 1) {
            if (activeStepIndex === undefined) setInternalStepIndex(currentStepIndex + 1);
        }
    };

    const handlePrev = () => {
        if (currentStepIndex > 0) {
            if (activeStepIndex === undefined) setInternalStepIndex(currentStepIndex - 1);
        }
    };

    if (!steps || steps.length === 0) {
        return (
            <Card className="h-full flex items-center justify-center">
                <CardContent className="text-center text-gray-500">
                    <BookOpen className="mx-auto h-12 w-12 mb-4 opacity-50" />
                    <p>No code tour steps generated yet.</p>
                </CardContent>
            </Card>
        );
    }

    const step = steps[currentStepIndex];

    return (
        <Card className="h-full flex flex-col border border-gray-200 shadow-sm overflow-hidden">
            {/* Fake IDE Window Header */}
            <div className="flex items-center justify-between px-4 py-2.5 bg-[#1e1e1e] border-b border-gray-700">
                <div className="flex items-center gap-2">
                    <div className="flex gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
                        <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
                        <div className="w-3 h-3 rounded-full bg-[#27c93f]" />
                    </div>
                    <span className="ml-3 text-xs text-gray-400 font-mono">{step.path}</span>
                </div>
                <Badge variant="outline" className="bg-gray-800 text-gray-300 border-gray-700 text-[10px]">
                    Step {currentStepIndex + 1}/{steps.length}
                </Badge>
            </div>

            <CardContent className="flex-1 flex flex-col p-0 bg-[#282c34]">
                {/* Narration Box (Insight Bubble) */}
                <div className="p-4 bg-[#0F62FE]/10 border-b border-gray-700">
                    <div className="flex gap-3">
                        <div className="mt-0.5 bg-[#0F62FE] rounded-full p-1">
                            <FileCode className="h-3 w-3 text-white" />
                        </div>
                        <p className="text-sm text-gray-200 leading-relaxed italic">
                            {step.narration}
                        </p>
                    </div>
                </div>

                {/* Code Highlighter */}
                <div className="flex-1 overflow-auto">
                    <SyntaxHighlighter
                        language={step.path.endsWith(".py") ? "python" : step.path.endsWith(".ts") || step.path.endsWith(".tsx") ? "typescript" : "javascript"}
                        style={oneDark}
                        showLineNumbers={true}
                        startingLineNumber={step.start}
                        wrapLines={true}
                        customStyle={{ margin: 0, padding: "1rem", background: "transparent", fontSize: "0.85rem" }}
                    >
                        {step.code || `// Code snippet for ${step.path}\n// Lines ${step.start} to ${step.end}`}
                    </SyntaxHighlighter>
                </div>

                {/* Navigation Controls */}
                <div className="p-3 border-t border-gray-700 flex justify-between items-center bg-[#1e1e1e]">
                    <Button
                        variant="ghost"
                        onClick={handlePrev}
                        disabled={currentStepIndex === 0}
                        className="text-gray-400 hover:text-white hover:bg-gray-800 flex items-center gap-2 text-sm"
                    >
                        <ChevronLeft className="h-4 w-4" /> Prev
                    </Button>
                    <p className="text-[10px] text-gray-500 font-mono">Press <kbd className="px-1.5 py-0.5 bg-gray-800 rounded border border-gray-700 text-gray-300">j</kbd> / <kbd className="px-1.5 py-0.5 bg-gray-800 rounded border border-gray-700 text-gray-300">k</kbd></p>
                    <Button
                        variant="ghost"
                        onClick={handleNext}
                        disabled={currentStepIndex === steps.length - 1}
                        className="text-gray-400 hover:text-white hover:bg-gray-800 flex items-center gap-2 text-sm"
                    >
                        Next <ChevronRight className="h-4 w-4" />
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}