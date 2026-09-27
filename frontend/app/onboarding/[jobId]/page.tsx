"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Server, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiFetch, Plan } from "@/lib/api";
import { CodeTourViewer } from "@/components/CodeTourViewer";
import { QAPanel } from "@/components/QAPanel";

type Citation = { path: string; start: number; end: number };

export default function OnboardingPage() {
  const params = useParams<{ jobId: string }>();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  const [requestedStep, setRequestedStep] = useState<number | undefined>();

  useEffect(() => {
    if (!params?.jobId) return;
    apiFetch<Plan>(`/api/repos/${params.jobId}/plan`)
      .then(setPlan)
      .catch((e) => setError(e instanceof Error ? e.message : "Unable to load plan"));
  }, [params?.jobId]);

  if (error) {
    return (
      <main className="min-h-screen p-10">
        <div className="mx-auto max-w-4xl rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">{error}</div>
      </main>
    );
  }

  if (!plan) {
    return (
      <main className="min-h-screen p-10">
        <div className="mx-auto max-w-4xl animate-pulse rounded-xl bg-white p-10 text-slate-500">Loading onboarding plan…</div>
      </main>
    );
  }

  const arch = typeof plan.architecture_summary === "string"
    ? { overview: plan.architecture_summary, modules: [], entry_points: [], data_flow: "" }
    : plan.architecture_summary;

  function citation(c: Citation) {
  if (!plan) return; // Add this null check
  
  const overlapping = plan.tour_steps.find((s) => s.path === c.path && s.start <= c.end && s.end >= c.start);
  const sameFile = plan.tour_steps.find((s) => s.path === c.path);
  const nearest = [...plan.tour_steps].sort((a, b) => {
    const distance = (step: typeof a) => {
      if (step.path !== c.path) return Number.POSITIVE_INFINITY;
      if (step.start <= c.end && step.end >= c.start) return 0;
      return Math.min(Math.abs(step.start - c.end), Math.abs(c.start - step.end));
    };
    return distance(a) - distance(b);
  })[0];
  const target = overlapping || sameFile || (nearest && Number.isFinite(nearest.start) ? nearest : null);
  if (target) setRequestedStep(target.step);
  document.getElementById("code-tour")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

  return (
    <main className="min-h-screen bg-[#f7f8fa] p-4 lg:p-6">
      <div className="mx-auto max-w-[1600px]">
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            <Badge className="bg-[#e8f1ff] text-[#0F62FE]">ONBOARDING PLAN</Badge>
            <h1 className="mt-2 text-3xl font-semibold">
              {plan.repo_context?.repo_url?.split("github.com/")[1] || "Repository"}
            </h1>
            <p className="text-sm text-slate-500">
              Role: {plan.role} · {plan.repo_context?.file_count ?? 0} files · {(plan.repo_context?.languages || []).join(", ") || "unknown languages"}
            </p>
          </div>
          <div className="text-right text-xs text-slate-400">
            <div className="flex items-center gap-1"><Sparkles className="h-4 w-4" />Evidence-backed</div>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-12">
          <aside className="space-y-4 lg:col-span-3">
            <Card>
              <CardHeader><CardTitle>Architecture</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-slate-600">{arch.overview}</p>

                <div className="mt-5 text-xs font-semibold uppercase tracking-wide text-slate-400">Modules</div>
                <div className="mt-2 space-y-2">
                  {arch.modules.length > 0 ? arch.modules.map((module) => (
                    <div key={module} className="rounded-md bg-slate-50 p-2 text-sm">{module}</div>
                  )) : (
                    <div className="text-sm text-slate-500">No module names were explicitly extracted.</div>
                  )}
                </div>

                <div className="mt-5 text-xs font-semibold uppercase tracking-wide text-slate-400">Entry points</div>
                <div className="mt-2 space-y-2">
                  {arch.entry_points.length > 0 ? arch.entry_points.map((entry) => (
                    <div key={entry} className="flex items-start gap-2 text-sm">
                      <Server className="mt-0.5 h-4 w-4 text-[#0F62FE]" />{entry}
                    </div>
                  )) : (
                    <div className="text-sm text-slate-500">No entry point was confidently identified.</div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Key concepts</CardTitle></CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {plan.key_concepts.map((concept, index) => <Badge key={index}>{concept}</Badge>)}
                </div>
              </CardContent>
            </Card>
          </aside>

          <section className="lg:col-span-6">
            <CodeTourViewer jobId={params.jobId} steps={plan.tour_steps} requestedStep={requestedStep} />
          </section>

          <aside className="lg:col-span-3">
            <QAPanel jobId={params.jobId} onCitation={citation} />
          </aside>
        </div>
      </div>
    </main>
  );
}
