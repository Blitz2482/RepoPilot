export function Tabs({children}: {children: React.ReactNode}) { return <div>{children}</div>; }
export function TabsList({children}: {children: React.ReactNode}) { return <div className="flex gap-2 border-b border-slate-200">{children}</div>; }
export function TabsTrigger({children, active, onClick}: {children: React.ReactNode; active?: boolean; onClick?:()=>void}) { return <button onClick={onClick} className={`border-b-2 px-3 py-2 text-sm ${active ? "border-[#0F62FE] text-[#0F62FE]" : "border-transparent text-slate-500"}`}>{children}</button>; }
