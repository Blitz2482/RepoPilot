"use client";
import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, TourStep } from "@/lib/api";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

export function CodeTourViewer({jobId, steps, requestedStep, onStepChange, sourceOverride}: {jobId:string; steps:TourStep[]; requestedStep?:number; onStepChange?:(step:TourStep)=>void; sourceOverride?:Record<string,string>}) {
  const [index, setIndex] = useState(0);
  const [source, setSource] = useState("");
  const current = steps[index];
  const language = useMemo(()=>{ const path=current?.path||""; if (path.endsWith(".py")) return "python"; if (path.endsWith(".ts")||path.endsWith(".tsx")) return "typescript"; return "javascript"; }, [current]);

  useEffect(() => { if (requestedStep && requestedStep >= 1 && requestedStep <= steps.length) setIndex(requestedStep-1); }, [requestedStep, steps.length]);
  useEffect(() => { if (!current) return; if (sourceOverride?.[current.path]) { setSource(sourceOverride[current.path]); return; } apiFetch<{content:string}>(`/api/repos/${jobId}/source?path=${encodeURIComponent(current.path)}&start=${current.start}&end=${current.end}`).then(d=>setSource(d.content||"")).catch(()=>setSource("Unable to load source.")); }, [current, jobId, sourceOverride]);
  useEffect(() => { const handler=(e:KeyboardEvent)=>{ if (e.key === "j" && index < steps.length-1) setIndex(v=>v+1); if (e.key === "k" && index > 0) setIndex(v=>v-1); }; window.addEventListener("keydown", handler); return ()=>window.removeEventListener("keydown", handler); }, [index, steps.length]);
  useEffect(() => { if (current) onStepChange?.(current); }, [current, onStepChange]);
  if (!current) return null;

  return <Card id="code-tour" className="overflow-hidden"><CardHeader><div className="flex items-center justify-between gap-3"><div><CardTitle>Code Tour</CardTitle><p className="mt-1 text-xs text-slate-500">Step {current.step} of 8 · {current.path}:{current.start}-{current.end}</p></div><div className="flex gap-2"><Button variant="outline" aria-label="Previous step" onClick={()=>setIndex(v=>Math.max(0,v-1))} disabled={index===0}><ChevronLeft className="h-4 w-4"/></Button><Button variant="outline" aria-label="Next step" onClick={()=>setIndex(v=>Math.min(steps.length-1,v+1))} disabled={index===steps.length-1}><ChevronRight className="h-4 w-4"/></Button></div></div></CardHeader><CardContent><div className="mb-4 rounded-lg bg-[#f0f6ff] p-4 text-sm leading-6 text-slate-700">{current.narration}</div><div className="max-h-[62vh] overflow-auto rounded-lg code-scroll"><SyntaxHighlighter language={language} style={oneDark} showLineNumbers wrapLongLines customStyle={{margin:0,fontSize:13}} startingLineNumber={current.start}>{source}</SyntaxHighlighter></div></CardContent></Card>;
}
