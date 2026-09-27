import * as React from "react";
import { cn } from "@/lib/utils";

export function Button({className, variant = "default", ...props}: React.ButtonHTMLAttributes<HTMLButtonElement> & {variant?: "default" | "outline" | "ghost"}) {
  return <button className={cn("inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50", variant === "default" ? "bg-[#0F62FE] text-white hover:bg-[#0043ce]" : variant === "outline" ? "border border-slate-300 bg-white hover:bg-slate-50" : "hover:bg-slate-100", className)} {...props} />;
}
