"use client";
import { useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { CheckCircle2, CircleDashed, Loader2, TriangleAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useWebSocket } from "@/hooks/useWebSocket";

const agentNames = ["Architecture", "Business Logic"];

export default function AnalysisPage() {
  const params = useParams<{jobId:string}>();
  const router = useRouter();
  const {messages, connected, error} = useWebSocket(params?.jobId ? `/api/repos/${params.jobId}/stream` : null);
  const latest = messages.length ? messages[messages.length - 1] : null;
  const progress = useMemo(() => latest?.progress ?? latest?.job?.progress ?? 0, [latest]);
  const agents = latest?.agents ?? latest?.job?.agents ?? {};
  const complete = messages.some((m)=>m.event === "complete");
  const failed = messages.find((m)=>m.event === "error");

  function elapsed(name:string) { const a=agents[name]; if (!a) return "—"; if (typeof a.elapsed_seconds === "number") return `${a.elapsed_seconds.toFixed(1)}s`; return "running…"; }

  return <main className="min-h-screen bg-[#f7f8fa] px-6 py-10">
    <div className="mx-auto max-w-6xl">
      <div className="mb-8 flex items-center justify-between gap-4"><div><Badge className="bg-[#e8f1ff] text-[#0F62FE]">LIVE ANALYSIS</Badge><h1 className="mt-3 text-3xl font-semibold">Understanding the repository</h1><p className="mt-1 text-sm text-slate-500">{connected ? "Connected to the analysis stream." : "Connecting to the analysis stream…"}</p></div>{complete && <Button onClick={()=>router.push(`/onboarding/${params.jobId}`)}>View Onboarding</Button>}</div>
      <Card className="mb-6"><CardContent className="pt-5"><div className="mb-2 flex justify-between text-xs text-slate-500"><span>Pipeline progress</span><span>{Math.round(progress)}%</span></div><Progress value={progress}/></CardContent></Card>
      {error && <div className="mb-6 flex items-center gap-2 rounded-md bg-amber-50 p-3 text-sm text-amber-900"><TriangleAlert className="h-4 w-4"/>{error}</div>}
      {failed && <div className="mb-6 rounded-md bg-red-50 p-3 text-sm text-red-700">{failed.message}</div>}
      <div className="grid gap-5 md:grid-cols-2">
        {agentNames.map((name)=><Card key={name} className="overflow-hidden"><CardHeader><div className="flex items-center justify-between"><CardTitle>{name} Agent</CardTitle>{agents[name]?.status === "done" ? <CheckCircle2 className="h-5 w-5 text-emerald-600"/> : agents[name]?.status === "running" ? <Loader2 className="h-5 w-5 animate-spin text-[#0F62FE]"/> : <CircleDashed className="h-5 w-5 text-slate-400"/>}</div></CardHeader><CardContent><div className="text-sm font-medium capitalize">{agents[name]?.status || "queued"}</div><p className="mt-2 min-h-10 text-sm leading-6 text-slate-600">{agents[name]?.latest_message || "Waiting to start"}</p><div className="mt-3 text-xs text-slate-400">Elapsed: {elapsed(name)}</div></CardContent></Card>)}
      </div>
      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-5"><div className="text-sm font-medium">Pipeline</div><div className="mt-4 grid grid-cols-2 gap-3 text-xs text-slate-600 sm:grid-cols-6">{["Ingest","Parse","Embed","Spawn","Synthesize","Emit"].map((step, i)=><div key={step} className="rounded-md bg-slate-50 p-3"><div className="font-semibold text-slate-800">{i+1}. {step}</div></div>)}</div></div>
    </div>
  </main>;
}
