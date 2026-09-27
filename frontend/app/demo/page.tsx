"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CodeTourViewer } from "@/components/CodeTourViewer";

const demoPlan = {
  role: "Full-Stack",
  architecture_summary: { overview: "Fallback demo data keeps the product walkthrough visible when live repository analysis is unavailable." },
  key_concepts: ["API contracts", "repository ingestion", "agent fanout", "grounded Q&A"],
  tour_steps: [
    {step:1,title:"Submit screen",path:"frontend/app/page.tsx",start:1,end:40,narration:"The submit screen captures the repository URL and role. It starts the onboarding job only after the GitHub URL passes validation."},
    {step:2,title:"FastAPI routes",path:"backend/routes.py",start:1,end:80,narration:"The API creates a job and starts the asynchronous analysis pipeline. This is the boundary between the browser and backend orchestration."},
    {step:3,title:"Repository ingestion",path:"backend/ingest.py",start:1,end:70,narration:"The ingestion service performs a shallow Git clone and collects basic repository metadata for downstream analysis."},
    {step:4,title:"Tree-sitter parser",path:"backend/parser.py",start:1,end:80,narration:"The parser extracts structural symbols from code files. Those symbols create concrete evidence for the later tour."},
    {step:5,title:"Chunking",path:"backend/chunker.py",start:1,end:80,narration:"The chunker creates bounded evidence units that can later be retrieved by the Q&A system."},
    {step:6,title:"Bob client",path:"backend/bob_client.py",start:1,end:120,narration:"The Bob client isolates the external analysis engine behind a stable interface used by specialized agents."},
    {step:7,title:"Synthesis",path:"backend/synthesis.py",start:1,end:120,narration:"Synthesis ranks evidence and creates exactly eight tour steps ordered for onboarding."},
    {step:8,title:"Grounded Q&A",path:"backend/qa.py",start:1,end:80,narration:"Q&A retrieves repository evidence before answering and validates returned citation ranges."}
  ]
};
const demoSource:Record<string,string> = {
  "frontend/app/page.tsx": "const valid = new URL(url).hostname === \"github.com\";\nif (valid) submit();",
  "backend/routes.py": "@router.post(\"/repos\")\nasync def create_repository(request, background_tasks):\n    job_id = str(uuid.uuid4())\n    background_tasks.add_task(_run_background, job_id, repo_url, role)",
  "backend/ingest.py": "cmd = [\"git\", \"clone\", \"--depth\", \"1\", repo_url, target]\nsubprocess.run(cmd, timeout=settings.clone_timeout_seconds)",
  "backend/parser.py": "tree = parser.parse(source)\nsymbols = _extract_symbols(tree.root_node, source)",
  "backend/chunker.py": "header = f\"File: {path} | Lines: {start}-{end} | Type: {header_type}\"",
  "backend/bob_client.py": "response = await client.post(url, headers={\"Authorization\": f\"Bearer {settings.bob_api_key}\"}, json=payload)",
  "backend/synthesis.py": "for idx, item in enumerate(unique[:8], 1):\n    narration = await generate_narration(item)",
  "backend/qa.py": "chunks = await hybrid_search(job_id, question, top_k=10)\nresult = await asyncio.wait_for(answer_with_bob(question, chunks), timeout=30)"
};

export default function DemoPage() {
  const [step, setStep] = useState(1);
  return <main className="min-h-screen bg-[#f7f8fa] p-6"><div className="mx-auto max-w-6xl"><Badge className="bg-[#e8f1ff] text-[#0F62FE]">FALLBACK DEMO</Badge><h1 className="mt-3 text-3xl font-semibold">RepoPilot demo data</h1><p className="mt-1 text-sm text-slate-500">Static plan and source snippets used when live services are unavailable.</p><div className="mt-6 grid gap-4 lg:grid-cols-[1fr_2fr]"><Card><CardHeader><CardTitle>Architecture</CardTitle></CardHeader><CardContent><p className="text-sm leading-6 text-slate-600">{demoPlan.architecture_summary.overview}</p><div className="mt-4 flex flex-wrap gap-2">{demoPlan.key_concepts.map((x)=><Badge key={x}>{x}</Badge>)}</div></CardContent></Card><div><CodeTourViewer jobId="demo" steps={demoPlan.tour_steps as any} requestedStep={step} onStepChange={(s)=>setStep(s.step)} sourceOverride={demoSource}/></div></div></div></main>;
}
