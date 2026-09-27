import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({className, ...props}, ref) => (
  <input ref={ref} className={cn("flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-[#0F62FE] focus:ring-2 focus:ring-[#0F62FE]/20", className)} {...props} />
));
Input.displayName = "Input";
