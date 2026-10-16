import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { api, download } from "@/lib/api";
import { cn, money } from "@/lib/utils";

type Overview = {
  currency: string;
  trend: { month: string; spent: string; income: string; savings_rate: number | null }[];
  category_changes: { name: string; current: number; previous: number; delta: number }[];
  projection: { spent_so_far: number; projected_month_end: number; previous_month: number };
  top_merchants: { name: string; count: number; total: string }[];
  biggest_this_month: { date: string; note: string | null; amount: string }[];
};

const tip = { background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 };

export default function Insights() {
  const [months, setMonths] = useState(6);
  const { data } = useQuery({ queryKey: ["insights", months], queryFn: () => api<Overview>(`/insights/overview?months=${months}`) });
  const [report, setReport] = useState(new Date().toISOString().slice(0, 7));
  if (!data) return <p className="text-muted-foreground">Loading…</p>;
  const cur = data.currency, p = data.projection;
  const trend = data.trend.map((t) => ({ ...t, spent: Number(t.spent), income: Number(t.income) }));
  const last = trend[trend.length - 1], prev = trend[trend.length - 2];
  const vsPrev = prev && prev.spent ? ((p.projected_month_end - prev.spent) / prev.spent) * 100 : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Insights</h1>
        <div className="flex items-center gap-2">
          <input type="month" aria-label="Report month" className="h-9 rounded-md border border-input bg-background px-3 text-sm" value={report} onChange={(e) => setReport(e.target.value)} />
          <Button variant="outline" size="sm" onClick={() => download(`/reports/monthly.pdf?month=${report}`, `report-${report}.pdf`)}><Download className="h-4 w-4" /> PDF report</Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardHeader><CardTitle>Projected spend this month</CardTitle></CardHeader><CardContent>
          <p className="text-2xl font-bold tabular-nums">{money(p.projected_month_end, cur)}</p>
          <p className="text-xs text-muted-foreground">{money(p.spent_so_far, cur)} so far at the current pace{vsPrev != null && ` · ${vsPrev >= 0 ? "+" : ""}${vsPrev.toFixed(0)}% vs last month`}</p>
        </CardContent></Card>
        <Card><CardHeader><CardTitle>Last month spent</CardTitle></CardHeader><CardContent>
          <p className="text-2xl font-bold tabular-nums">{money(p.previous_month, cur)}</p></CardContent></Card>
        <Card><CardHeader><CardTitle>Savings rate (this month)</CardTitle></CardHeader><CardContent>
          <p className={cn("text-2xl font-bold tabular-nums", last?.savings_rate != null && last.savings_rate < 0 && "text-red-500")}>{last?.savings_rate != null ? `${last.savings_rate}%` : "—"}</p>
          <p className="text-xs text-muted-foreground">Share of income you kept</p></CardContent></Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0"><CardTitle>Income vs spending by month</CardTitle>
          <Select className="h-8 w-32" aria-label="Months" value={months} onChange={(e) => setMonths(Number(e.target.value))}>{[3, 6, 12].map((m) => <option key={m} value={m}>{m} months</option>)}</Select></CardHeader>
        <CardContent className="h-72">
          <ResponsiveContainer>
            <BarChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
              <XAxis dataKey="month" fontSize={11} /><YAxis fontSize={11} width={48} />
              <Tooltip formatter={(v: number) => money(v, cur)} contentStyle={tip} />
              <Bar dataKey="income" fill="#22c55e" radius={[3, 3, 0, 0]} /><Bar dataKey="spent" fill="#ef4444" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Category changes vs last month</CardTitle></CardHeader><CardContent className="space-y-2">
          {data.category_changes.length ? data.category_changes.slice(0, 8).map((c) => (
            <div key={c.name} className="flex items-center justify-between text-sm">
              <span>{c.name}</span>
              <span className="tabular-nums"><span className="text-muted-foreground">{money(c.previous, cur)} → </span>{money(c.current, cur)}
                <span className={cn("ml-2 font-medium", c.delta > 0 ? "text-red-500" : c.delta < 0 ? "text-emerald-500" : "")}>{c.delta > 0 ? "▲" : c.delta < 0 ? "▼" : "•"} {money(Math.abs(c.delta), cur)}</span></span>
            </div>
          )) : <p className="text-sm text-muted-foreground">Not enough data yet.</p>}
        </CardContent></Card>
        <Card><CardHeader><CardTitle>Top places you spend</CardTitle></CardHeader><CardContent className="space-y-2">
          {data.top_merchants.length ? data.top_merchants.map((m) => (
            <div key={m.name} className="flex items-center justify-between text-sm">
              <span className="truncate capitalize">{m.name} <span className="text-xs text-muted-foreground">× {m.count}</span></span>
              <span className="tabular-nums">{money(m.total, cur)}</span>
            </div>
          )) : <p className="text-sm text-muted-foreground">Add notes to your expenses (e.g. “Swiggy”) to see your top places.</p>}
        </CardContent></Card>
      </div>

      <Card><CardHeader><CardTitle>Biggest expenses this month</CardTitle></CardHeader><CardContent className="space-y-2">
        {data.biggest_this_month.length ? data.biggest_this_month.map((b, i) => (
          <div key={i} className="flex items-center justify-between text-sm"><span>{b.note || "Expense"} <span className="text-xs text-muted-foreground">{b.date}</span></span><span className="tabular-nums">{money(b.amount, cur)}</span></div>
        )) : <p className="text-sm text-muted-foreground">No expenses yet this month.</p>}
      </CardContent></Card>
    </div>
  );
}
