import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pause, Pencil, Play, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Field } from "@/components/Field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Input, Select } from "@/components/ui/input";
import { api, type Sub } from "@/lib/api";
import { useAccounts, useCategories, useMe } from "@/lib/hooks";
import { money, today } from "@/lib/utils";

const FACTOR: Record<string, number> = { weekly: 52 / 12, monthly: 1, quarterly: 1 / 3, yearly: 1 / 12 };
const blank = (cur: string) => ({ name: "", amount: "", currency: cur, cycle: "monthly", next_billing_date: today(), category_id: "", account_id: "", status: "active", remind_days_before: "3", auto_post: false, notes: "" });

function SubDialog({ sub, open, onClose }: { sub: Sub | null; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const cur = useMe().data!.default_currency;
  const cats = (useCategories().data ?? []).filter((c) => c.kind === "expense");
  const accounts = useAccounts().data ?? [];
  const [f, setF] = useState<any>(blank(cur));
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!open) return;
    setErr("");
    setF(sub ? { ...sub, category_id: String(sub.category_id ?? ""), account_id: String(sub.account_id ?? ""), remind_days_before: String(sub.remind_days_before), notes: sub.notes ?? "" } : blank(cur));
  }, [open, sub, cur]);
  const save = useMutation({
    mutationFn: () => {
      const body = { ...f, currency: f.currency.toUpperCase(), category_id: f.category_id ? Number(f.category_id) : null, account_id: f.account_id ? Number(f.account_id) : null, remind_days_before: Number(f.remind_days_before), notes: f.notes || null };
      return sub ? api(`/subscriptions/${sub.id}`, { method: "PUT", body }) : api("/subscriptions", { body });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["subs"] }); qc.invalidateQueries({ queryKey: ["sub-summary"] }); onClose(); },
    onError: (e: Error) => setErr(e.message),
  });
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title={sub ? "Edit subscription" : "Add subscription"}>
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
          <Field label="Name"><Input required value={f.name} onChange={set("name")} placeholder="Netflix" /></Field>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2"><Field label="Amount"><Input type="number" step="0.01" min="0.01" required value={f.amount} onChange={set("amount")} /></Field></div>
            <Field label="Currency"><Input maxLength={3} minLength={3} required value={f.currency} onChange={set("currency")} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Billing cycle"><Select value={f.cycle} onChange={set("cycle")}>{["weekly", "monthly", "quarterly", "yearly"].map((c) => <option key={c}>{c}</option>)}</Select></Field>
            <Field label="Next billing date"><Input type="date" required value={f.next_billing_date} onChange={set("next_billing_date")} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Category"><Select value={f.category_id} onChange={set("category_id")}><option value="">None</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>
            <Field label="Account"><Select value={f.account_id} onChange={set("account_id")}><option value="">None</option>{accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</Select></Field>
          </div>
          <Field label="Remind me (days before)"><Input type="number" min="0" max="60" value={f.remind_days_before} onChange={set("remind_days_before")} /></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.auto_post} onChange={(e) => setF({ ...f, auto_post: e.target.checked })} /> Auto-create a transaction on billing date</label>
          {err && <p className="text-sm text-destructive">{err}</p>}
          <Button className="w-full" disabled={save.isPending}>Save</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function Subscriptions() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Sub | null>(null);
  const [open, setOpen] = useState(false);
  const { data: subs = [] } = useQuery({ queryKey: ["subs"], queryFn: () => api<Sub[]>("/subscriptions") });
  const { data: sum } = useQuery({ queryKey: ["sub-summary"], queryFn: () => api("/subscriptions/summary") });
  const cats = Object.fromEntries((useCategories().data ?? []).map((c) => [c.id, c.name]));
  const refresh = () => { qc.invalidateQueries({ queryKey: ["subs"] }); qc.invalidateQueries({ queryKey: ["sub-summary"] }); };
  const del = useMutation({ mutationFn: (id: number) => api(`/subscriptions/${id}`, { method: "DELETE" }), onSuccess: refresh });
  const toggle = useMutation({
    mutationFn: (s: Sub) => api(`/subscriptions/${s.id}`, { method: "PUT", body: { ...s, status: s.status === "active" ? "paused" : "active" } }),
    onSuccess: refresh,
  });
  const days = (d: string) => Math.round((new Date(d).getTime() - new Date(today()).getTime()) / 864e5);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Subscriptions</h1>
        <Button onClick={() => { setEditing(null); setOpen(true); }}><Plus className="h-4 w-4" /> Add subscription</Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardHeader><CardTitle>Monthly cost</CardTitle></CardHeader><CardContent>
          {sum && Object.keys(sum.monthly_by_currency).length ? Object.entries(sum.monthly_by_currency).map(([c, v]) => <p key={c} className="text-2xl font-bold tabular-nums">{money(v as number, c)}</p>) : <p className="text-2xl font-bold">—</p>}</CardContent></Card>
        <Card><CardHeader><CardTitle>Yearly cost</CardTitle></CardHeader><CardContent>
          {sum && Object.keys(sum.yearly_by_currency).length ? Object.entries(sum.yearly_by_currency).map(([c, v]) => <p key={c} className="text-2xl font-bold tabular-nums">{money(v as number, c)}</p>) : <p className="text-2xl font-bold">—</p>}</CardContent></Card>
        <Card><CardHeader><CardTitle>Active</CardTitle></CardHeader><CardContent><p className="text-2xl font-bold">{sum?.active_count ?? 0}</p></CardContent></Card>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {subs.map((s) => {
          const d = days(s.next_billing_date);
          return (
            <Card key={s.id} className={s.status !== "active" ? "opacity-60" : ""}>
              <CardContent className="space-y-3 p-5">
                <div className="flex items-start justify-between">
                  <div><p className="font-semibold">{s.name}</p><p className="text-xs text-muted-foreground">{s.category_id ? cats[s.category_id] : "Uncategorized"} · {s.cycle}</p></div>
                  <Badge variant={s.status === "active" ? "success" : "secondary"}>{s.status}</Badge>
                </div>
                <p className="text-2xl font-bold tabular-nums">{money(s.amount, s.currency)}</p>
                <p className="text-xs text-muted-foreground">≈ {money(Number(s.amount) * FACTOR[s.cycle], s.currency)}/mo</p>
                <div className="flex items-center justify-between text-sm">
                  <span>Next: {s.next_billing_date}</span>
                  {s.status === "active" && <Badge variant={d < 0 ? "destructive" : d <= s.remind_days_before ? "warning" : "secondary"}>{d < 0 ? `${-d}d overdue` : d === 0 ? "today" : `in ${d}d`}</Badge>}
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" aria-label="Edit" onClick={() => { setEditing(s); setOpen(true); }}><Pencil className="h-3.5 w-3.5" /></Button>
                  <Button variant="ghost" size="icon" aria-label={s.status === "active" ? "Pause" : "Resume"} onClick={() => toggle.mutate(s)}>{s.status === "active" ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}</Button>
                  <Button variant="ghost" size="icon" aria-label="Delete" onClick={() => confirm(`Delete ${s.name}?`) && del.mutate(s.id)}><Trash2 className="h-3.5 w-3.5" /></Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
        {!subs.length && <p className="text-muted-foreground">No subscriptions yet — add Netflix, Spotify, rent…</p>}
      </div>
      <SubDialog sub={editing} open={open} onClose={() => setOpen(false)} />
    </div>
  );
}
