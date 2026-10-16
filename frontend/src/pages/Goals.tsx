import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { money } from "@/lib/utils";

type Goal = { id: number; name: string; target_amount: string; saved_amount: string; deadline: string | null; color: string };
type Plan = { remaining: string; percent: number; monthly_needed: number | null; months_left: number | null; status: string };

function GoalCard({ g, cur, onChange }: { g: Goal; cur: string; onChange: () => void }) {
  const plan = useQuery({ queryKey: ["goal-plan", g.id, g.saved_amount, g.deadline], queryFn: () => api<Plan>(`/goals/${g.id}/plan`) });
  const [amt, setAmt] = useState("");
  const contribute = useMutation({
    mutationFn: (sign: 1 | -1) => api(`/goals/${g.id}/contribute`, { body: { amount: String(sign * Number(amt)) } }),
    onSuccess: () => { setAmt(""); onChange(); },
  });
  const del = useMutation({ mutationFn: () => api(`/goals/${g.id}`, { method: "DELETE" }), onSuccess: onChange });
  const p = plan.data;
  return (
    <Card><CardContent className="space-y-3 p-5">
      <div className="flex items-start justify-between gap-2">
        <div><p className="font-semibold">{g.name}</p>{g.deadline && <p className="text-xs text-muted-foreground">by {g.deadline}</p>}</div>
        <div className="flex items-center gap-1">
          {p?.status === "done" && <Badge variant="success">Reached</Badge>}
          {p?.status === "overdue" && <Badge variant="destructive">Past deadline</Badge>}
          <Button variant="ghost" size="icon" aria-label={`Delete ${g.name}`} onClick={() => confirm(`Delete goal ${g.name}?`) && del.mutate()}><Trash2 className="h-3.5 w-3.5" /></Button>
        </div>
      </div>
      <Progress value={p?.percent ?? 0} barClass={p?.status === "done" ? "bg-emerald-500" : ""} />
      <div className="flex justify-between text-sm tabular-nums"><span>{money(g.saved_amount, cur)} of {money(g.target_amount, cur)}</span><span className="text-muted-foreground">{p?.percent ?? 0}%</span></div>
      {p?.monthly_needed != null && <p className="rounded-md bg-secondary px-3 py-2 text-sm">Save <b className="tabular-nums">{money(p.monthly_needed, cur)}</b> a month for {p.months_left} more month{p.months_left === 1 ? "" : "s"} to get there.</p>}
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); contribute.mutate(1); }}>
        <Input type="number" min="0.01" step="0.01" required placeholder="Amount" aria-label={`Amount for ${g.name}`} value={amt} onChange={(e) => setAmt(e.target.value)} />
        <Button size="sm" disabled={contribute.isPending}>Add</Button>
        <Button size="sm" type="button" variant="outline" disabled={!amt || contribute.isPending} onClick={() => contribute.mutate(-1)}>Withdraw</Button>
      </form>
      {contribute.error && <p className="text-sm text-destructive">{contribute.error.message}</p>}
    </CardContent></Card>
  );
}

export default function Goals() {
  const qc = useQueryClient();
  const cur = useMe().data!.default_currency;
  const { data = [] } = useQuery({ queryKey: ["goals"], queryFn: () => api<Goal[]>("/goals") });
  const [f, setF] = useState({ name: "", target: "", saved: "0", deadline: "" });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["goals"] }); qc.invalidateQueries({ queryKey: ["goal-plan"] }); };
  const add = useMutation({
    mutationFn: () => api("/goals", { body: { name: f.name, target_amount: f.target, saved_amount: f.saved || "0", deadline: f.deadline || null } }),
    onSuccess: () => { setF({ name: "", target: "", saved: "0", deadline: "" }); refresh(); },
  });
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Savings goals</h1>
      <Card><CardContent className="p-5">
        <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
          <Field label="Goal"><Input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Goa trip" /></Field>
          <Field label={`Target (${cur})`}><Input type="number" min="1" step="0.01" required value={f.target} onChange={(e) => setF({ ...f, target: e.target.value })} /></Field>
          <Field label="Saved so far"><Input type="number" min="0" step="0.01" value={f.saved} onChange={(e) => setF({ ...f, saved: e.target.value })} /></Field>
          <Field label="Deadline (optional)"><Input type="date" value={f.deadline} onChange={(e) => setF({ ...f, deadline: e.target.value })} /></Field>
          <div className="flex items-end"><Button className="w-full" disabled={add.isPending}>Add goal</Button></div>
        </form>
        {add.error && <p className="mt-2 text-sm text-destructive">{add.error.message}</p>}
      </CardContent></Card>
      <div className="grid gap-3 sm:grid-cols-2">
        {data.map((g) => <GoalCard key={g.id} g={g} cur={cur} onChange={refresh} />)}
        {!data.length && <p className="text-muted-foreground">No goals yet. Add one above and track your progress.</p>}
      </div>
    </div>
  );
}
