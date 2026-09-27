import { cn } from "@/lib/utils";
export function Badge({children, className}: {children: React.ReactNode; className?: string}) { return <span className={cn("inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700", className)}>{children}</span>; }
