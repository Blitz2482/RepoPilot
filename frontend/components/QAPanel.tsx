"use client";
import { FormEvent, useState } from "react";
import { Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api";

type Citation = {path:string; start:number; end:number};
type Message = {role:"user"|"assistant"; content:string; citations?:Citation[]};

export function QAPanel({jobId, onCitation}: {jobId:string; onCitation:(citation:Citation)=>void}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function submit(e:FormEvent) { e.preventDefault(); const q=question.trim(); if (!q || loading) return; setQuestion(""); setError(""); setMessages(m=>[...m,{role:"user",content:q}]); setLoading(true); try { const result=await apiFetch<{answer:string;citations:Citation[]}>(`/api/repos/${jobId}/ask`,{method:"POST",body:JSON.stringify({question:q})}); setMessages(m=>[...m,{role:"assistant",content:result.answer,citations:result.citations}]); } catch(err) { setError(err instanceof Error ? err.message : "Unable to answer"); } finally { setLoading(false); } }
  return <div className="flex h-full min-h-[360px] flex-col rounded-xl border border-slate-200 bg-white"><div className="border-b border-slate-200 p-4"><div className="text-sm font-semibold">Grounded Q&amp;A</div><div className="text-xs text-slate-500">Answers are limited to retrieved repository evidence.</div></div><div className="flex-1 space-y-4 overflow-auto p-4">{messages.length===0 && <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">Try: “How does retry work?”</div>}{messages.map((m,i)=><div key={i} className={m.role==="user" ? "ml-6" : "mr-6"}><div className={`rounded-lg p-3 text-sm leading-6 ${m.role==="user" ? "bg-[#0F62FE] text-white" : "bg-slate-100 text-slate-700"}`}>{m.content}</div>{m.citations?.length ? <div className="mt-2 flex flex-wrap gap-1">{m.citations.map((c,idx)=><button key={idx} onClick={()=>onCitation(c)} className="rounded-full bg-[#e8f1ff] px-2 py-1 text-[11px] font-medium text-[#0F62FE] hover:bg-[#dbeaff]">{c.path}:{c.start}-{c.end}</button>)}</div> : null}</div>)}{loading && <div className="flex items-center gap-2 text-xs text-slate-500"><Loader2 className="h-4 w-4 animate-spin"/>Searching repository evidence…</div>}{error && <div className="text-xs text-red-600">{error}</div>}</div><form onSubmit={submit} className="flex gap-2 border-t border-slate-200 p-3"><Input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask about this repository…" maxLength={500}/><Button type="submit" disabled={!question.trim() || loading} aria-label="Ask question"><Send className="h-4 w-4"/></Button></form></div>;
}
