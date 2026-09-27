"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, BookOpen, GitBranch, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api";

const roles = ["Backend", "Frontend", "Full-Stack", "Data", "DevOps", "QA"];

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [role, setRole] = useState("Full-Stack");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const valid = useMemo(() => { try { const u = new URL(url); return (u.protocol === "https:" || u.protocol === "http:") && (u.hostname === "github.com" || u.hostname === "www.github.com") && /^\/[^/]+\/[^/]+(?:\.git)?\/?$/.test(u.pathname); } catch { return false; } }, [url]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid) return;
    setLoading(true); setError("");
    try {
      const result = await apiFetch<{job_id:string;status:string}>("/api/repos", { method: "POST", body: JSON.stringify({repo_url:url, role}) });
      router.push(`/analysis/${result.job_id}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to submit repository"); setLoading(false); }
  }

  return <main className="min-h-screen bg-[#f7f8fa] px-6 py-16">
    <div className="mx-auto max-w-5xl">
      <div className="mb-12 grid gap-12 md:grid-cols-[1.1fr_0.9fr] md:items-center">
        <div>
          <div className="mb-5 inline-flex rounded-full bg-[#e8f1ff] px-3 py-1 text-xs font-semibold tracking-wide text-[#0F62FE]">IBM-inspired developer onboarding</div>
          <h1 className="text-5xl font-semibold tracking-tight md:text-6xl">RepoPilot</h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">Turn a codebase into a guided tour: architecture, evidence-backed walkthroughs, and grounded Q&amp;A.</p>
          <div className="mt-7 grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
            <div className="flex items-center gap-2"><GitBranch className="h-4 w-4 text-[#0F62FE]"/>GitHub ingestion</div>
            <div className="flex items-center gap-2"><BookOpen className="h-4 w-4 text-[#0F62FE]"/>8-step tour</div>
            <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[#0F62FE]"/>Cited answers</div>
          </div>
        </div>
        <Card className="border-0 shadow-xl">
          <CardHeader><CardTitle className="text-xl">Analyze a repository</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-5">
              <div>
                <label className="mb-2 block text-sm font-medium">GitHub URL</label>
                <Input value={url} onChange={(e)=>setUrl(e.target.value)} placeholder="https://github.com/owner/repo" inputMode="url" autoComplete="url" />
                {url && !valid && <p className="mt-2 text-xs text-red-600">Enter a valid github.com repository URL.</p>}
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium">Developer role</label>
                <select value={role} onChange={(e)=>setRole(e.target.value)} className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm focus:border-[#0F62FE] focus:outline-none">
                  {roles.map((r)=><option key={r}>{r}</option>)}
                </select>
              </div>
              {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}
              <Button type="submit" disabled={!valid || loading} className="w-full py-3">{loading ? "Submitting…" : "Analyze Repository"}<ArrowRight className="ml-2 h-4 w-4"/></Button>
              <p className="text-center text-xs text-slate-500">The MVP clones a shallow read-only copy and analyzes Python, TypeScript, and JavaScript.</p>
            </form>
          </CardContent>
        </Card>
      </div>
      <div className="border-t border-slate-200 pt-8 text-xs text-slate-500">RepoPilot is designed around full-repository analysis and citation-backed onboarding.</div>
    </div>
  </main>;
}
