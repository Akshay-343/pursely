import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AiTips } from "@/components/Ai";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { api, type Tx } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { cn, iso, money, monthStart, today } from "@/lib/utils";

const presets = {
  "This month": () => [monthStart(), today()],
  "Last 30 days": () => [iso(new Date(Date.now() - 29 * 864e5)), today()],
  "This year": () => [`${new Date().getFullYear()}-01-01`, today()],
} as const;

export default function Dashboard() {
  const cur = useMe().data!.default_currency;
  const [preset, setPreset] = useState<keyof typeof presets | "Custom">("This month");
  const [[from, to], setRange] = useState<string[]>(presets["This month"]());
  const qs = `from=${from}&to=${to}`;
  const days = (new Date(to).getTime() - new Date(from).getTime()) / 864e5;
  const gran = days > 120 ? "month" : days > 45 ? "week" : "day";

  const summary = useQuery({ queryKey: ["dashboard", "summary", qs], queryFn: () => api(`/dashboard/summary?${qs}`) });
  const byCat = useQuery({ queryKey: ["dashboard", "cat", qs], queryFn: () => api<any[]>(`/dashboard/by-category?${qs}`) });
  const series = useQuery({ queryKey: ["dashboard", "ts", qs, gran], queryFn: () => api<any[]>(`/dashboard/timeseries?${qs}&granularity=${gran}`) });
  const budgets = useQuery({ queryKey: ["budget-status"], queryFn: () => api<any[]>("/budgets/status") });
  const recent = useQuery({ queryKey: ["transactions", "recent"], queryFn: () => api<{ items: Tx[] }>("/transactions?page_size=6") });
  const subs = useQuery({ queryKey: ["sub-summary"], queryFn: () => api("/subscriptions/summary") });

  const s = summary.data;
  const kpis = [
    { label: "Spent", value: s?.total_spent, tone: "text-red-500" },
    { label: "Income", value: s?.total_income, tone: "text-emerald-500" },
    { label: "Net savings", value: s?.net, tone: Number(s?.net) < 0 ? "text-red-500" : "text-emerald-500" },
    { label: "Avg / day", value: s?.avg_per_day, tone: "" },
  ];
  const totalCat = (byCat.data ?? []).reduce((a, c) => a + Number(c.total), 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex flex-wrap items-center gap-2">
          {(Object.keys(presets) as (keyof typeof presets)[]).map((p) => (
            <button key={p} onClick={() => { setPreset(p); setRange(presets[p]()); }}
              className={cn("rounded-full border px-3 py-1 text-xs", preset === p ? "border-primary bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent")}>{p}</button>
          ))}
          <Input type="date" className="h-8 w-36" value={from} onChange={(e) => { setPreset("Custom"); setRange([e.target.value, to]); }} />
          <Input type="date" className="h-8 w-36" value={to} onChange={(e) => { setPreset("Custom"); setRange([from, e.target.value]); }} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map((k) => (
          <Card key={k.label}><CardHeader><CardTitle>{k.label}</CardTitle></CardHeader>
            <CardContent><p className={cn("text-2xl font-bold tabular-nums", k.tone)}>{k.value == null ? "—" : money(k.value, cur)}</p></CardContent></Card>
        ))}
      </div>

      <AiTips />

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader><CardTitle>Income vs expense (per {gran})</CardTitle></CardHeader>
          <CardContent className="h-72">
            {series.data?.length ? (
              <ResponsiveContainer>
                <BarChart data={series.data.map((r) => ({ ...r, income: Number(r.income), expense: Number(r.expense) }))}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                  <XAxis dataKey="period" tickFormatter={(v) => v.slice(gran === "month" ? 0 : 5)} fontSize={11} />
                  <YAxis fontSize={11} width={48} />
                  <Tooltip formatter={(v: number) => money(v, cur)} contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
                  <Bar dataKey="income" fill="#22c55e" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="expense" fill="#ef4444" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <Empty />}
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Spending by category</CardTitle></CardHeader>
          <CardContent className="h-72">
            {byCat.data?.length ? (
              <div className="flex h-full flex-col">
                <ResponsiveContainer height="60%">
                  <PieChart>
                    <Pie data={byCat.data.map((c) => ({ ...c, total: Number(c.total) }))} dataKey="total" nameKey="name" innerRadius="55%" outerRadius="90%" paddingAngle={2}>
                      {byCat.data.map((c) => <Cell key={c.name} fill={c.color} />)}
                    </Pie>
                    <Tooltip formatter={(v: number) => money(v, cur)} contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
                  </PieChart>
                </ResponsiveContainer>
                <ul className="mt-2 space-y-1 overflow-y-auto text-xs">
                  {byCat.data.slice(0, 5).map((c) => (
                    <li key={c.name} className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-2"><i className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />{c.name}</span>
                      <span className="tabular-nums text-muted-foreground">{money(c.total, cur)} · {totalCat ? Math.round((Number(c.total) / totalCat) * 100) : 0}%</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : <Empty />}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Budgets (this month)</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {budgets.data?.length ? budgets.data.map((b) => (
              <div key={b.id} className="space-y-1">
                <div className="flex justify-between text-sm"><span>{b.category}</span>
                  <span className="tabular-nums text-muted-foreground">{money(b.spent, cur)} / {money(b.budget, cur)}</span></div>
                <Progress value={b.percent} barClass={b.state === "over" ? "bg-red-500" : b.state === "warning" ? "bg-amber-500" : "bg-emerald-500"} />
              </div>
            )) : <p className="text-sm text-muted-foreground">No budgets yet. Set one on the Budgets page.</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Upcoming renewals</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {subs.data?.upcoming.length ? subs.data.upcoming.slice(0, 5).map((u: any) => (
              <div key={u.id} className="flex items-center justify-between text-sm">
                <span>{u.name}</span>
                <span className="flex items-center gap-2"><span className="tabular-nums">{money(u.amount, u.currency)}</span>
                  <Badge variant={u.days <= 3 ? "warning" : "secondary"}>{u.days <= 0 ? "due" : `${u.days}d`}</Badge></span>
              </div>
            )) : <p className="text-sm text-muted-foreground">Nothing due in the next 30 days.</p>}
            {subs.data && Object.entries(subs.data.monthly_by_currency).map(([c, v]) => (
              <p key={c} className="border-t pt-2 text-xs text-muted-foreground">Monthly subscription cost: {money(v as number, c)}</p>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Recent transactions</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {recent.data?.items.length ? recent.data.items.map((t) => (
              <div key={t.id} className="flex items-center justify-between text-sm">
                <div className="min-w-0"><p className="truncate">{t.note || t.category?.name || "Transaction"}</p><p className="text-xs text-muted-foreground">{t.date}</p></div>
                <span className={cn("tabular-nums", t.kind === "income" ? "text-emerald-500" : "")}>{t.kind === "income" ? "+" : "−"}{money(t.amount, t.account?.currency ?? cur)}</span>
              </div>
            )) : <p className="text-sm text-muted-foreground">No transactions yet. Use “Add” to log one.</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

const Empty = () => <div className="flex h-full items-center justify-center text-sm text-muted-foreground">No data for this period</div>;
