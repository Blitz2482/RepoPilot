"use client";

import { QAPanel } from "@/components/QAPanel";
import * as React from "react";
const { useEffect, useState } = React;
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CodeTourViewer } from "@/components/CodeTourViewer";
import { Loader2, AlertCircle, ArrowLeft, Brain, Cpu, Lightbulb } from "lucide-react";
import { useRouter } from "next/navigation";

interface TourStep {
    step: number;
    title: string;
    path: string;
    start: number;
    end: number;
    narration: string;
    code?: string;
}

interface OnboardingPlan {
    role: string;
    architecture_summary: string;
    key_concepts: string[];
    tour_steps: TourStep[];
}

export default function OnboardingPage({ params }: { params: { jobId: string } }) {
    const router = useRouter();
    const [plan, setPlan] = useState<OnboardingPlan | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    // NEW: State to allow the Q&A panel to control the Code Tour Viewer
    const [activeTourStep, setActiveTourStep] = useState<number | undefined>(undefined);

    useEffect(() => {
        const fetchPlan = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const res = await fetch(`${apiUrl}/api/repos/${params.jobId}/plan`);
                if (!res.ok) throw new Error("Failed to fetch onboarding plan.");
                const data = await res.json();
                setPlan(data);
            } catch (err) {
                console.warn("Backend unavailable. Falling back to mock data for demo.", err);
                // HACKATHON SURVIVAL TACTIC: Load mock data if backend fails
                import("@/lib/mockData").then((module) => {
                    setPlan(module.mockOnboardingPlan);
                });
            } finally {
                setLoading(false);
            }
        };
        fetchPlan();
    }, [params.jobId]);

    // NEW: Handler to jump the Code Tour to a specific file when a citation is clicked
    const handleCitationClick = (citation: { path: string; start: number; end: number }) => {
        if (!plan?.tour_steps) return;

        const matchingStepIndex = plan.tour_steps.findIndex(
            (step) => step.path === citation.path
        );

        if (matchingStepIndex !== -1) {
            setActiveTourStep(matchingStepIndex);
        }
    };

    if (loading) {
        return (
            <main className="min-h-screen bg-gray-50 flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-[#0F62FE]" />
            </main>
        );
    }

    if (error || !plan) {
        return (
            <main className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
                <Card className="w-full max-w-md border-red-200 bg-red-50">
                    <CardContent className="flex items-center gap-3 p-6 text-red-700">
                        <AlertCircle className="h-5 w-5" />
                        <div>
                            <p className="font-bold">Failed to load plan</p>
                            <p className="text-sm">{error || "Plan not found."}</p>
                        </div>
                    </CardContent>
                </Card>
            </main>
        );
    }

    return (
        <main className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-7xl mx-auto space-y-6">

                {/* Top Navigation */}
                <div className="flex items-center justify-between">
                    <div>
                        <Button variant="ghost" onClick={() => router.back()} className="text-gray-600">
                            <ArrowLeft className="mr-2 h-4 w-4" /> Back
                        </Button>
                        <h1 className="text-2xl font-bold text-gray-900 mt-2">Onboarding Dashboard</h1>
                        <p className="text-sm text-gray-500">Role: <Badge variant="secondary">{plan.role}</Badge></p>
                    </div>
                    <Badge className="bg-green-100 text-green-800 hover:bg-green-100 border-green-200">
                        Analysis Complete
                    </Badge>
                </div>

                {/* 3-Column Grid Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-140px)]">

                    {/* Left Column: Architecture Summary (25%) */}
                    <div className="lg:col-span-3 space-y-6 overflow-y-auto pr-2">
                        <Card className="border-t-4 border-t-[#0F62FE]">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-lg font-bold flex items-center gap-2">
                                    <Brain className="h-5 w-5 text-[#0F62FE]" /> Architecture
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                                    {plan.architecture_summary || "No architecture summary provided."}
                                </p>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-lg font-bold flex items-center gap-2">
                                    <Cpu className="h-5 w-5 text-purple-500" /> Domain Concepts
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <ul className="space-y-2">
                                    {plan.key_concepts && plan.key_concepts.length > 0 ? (
                                        plan.key_concepts.map((concept, i) => (
                                            <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                                                <span className="text-[#0F62FE] font-bold mt-0.5">•</span>
                                                {concept}
                                            </li>
                                        ))
                                    ) : (
                                        <li className="text-sm text-gray-500">No key concepts identified.</li>
                                    )}
                                </ul>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Center Column: Code Tour Viewer (50%) */}
                    <div className="lg:col-span-6 h-full">
                        {/* UPDATED: Passes the activeTourStep to allow external control */}
                        <CodeTourViewer
                            steps={plan.tour_steps || []}
                            activeStepIndex={activeTourStep}
                        />
                    </div>

                    {/* Right Column: Learning Path + Q&A Panel (25%) */}
                    <div className="lg:col-span-3 space-y-6 overflow-y-auto pl-2">

                        {/* Learning Path Card */}
                        <Card className="border-t-4 border-t-green-500">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-lg font-bold flex items-center gap-2">
                                    <Lightbulb className="h-5 w-5 text-green-500" /> Learning Path
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-sm text-gray-600 mb-4">
                                    Recommended concepts to study for a <strong>{plan.role}</strong> developer:
                                </p>
                                <div className="space-y-2">
                                    {plan.key_concepts?.slice(0, 4).map((c, i) => (
                                        <div key={i} className="bg-gray-100 p-2 rounded text-xs text-gray-700">
                                            {i + 1}. {c}
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Q&A Panel Component */}
                        <div className="h-[400px]">
                            {/* UPDATED: Passes the citation click handler */}
                            <QAPanel
                                jobId={params.jobId}
                                onCitationClick={handleCitationClick}
                            />
                        </div>

                    </div>

                </div>
            </div>
        </main>
    );
}