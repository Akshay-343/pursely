import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import { useCategories, useMe } from "@/lib/hooks";
import { cn, money } from "@/lib/utils";

export default function Budgets() {
  const qc = useQueryClient();
  const cur = useMe().data!.default_currency;
  const cats = (useCategories().data ?? []).filter((c) => c.kind === "expense");
  const { data = [] } = useQuery({ queryKey: ["budget-status"], queryFn: () => api<any[]>("/budgets/status") });
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");
  const [err, setErr] = useState("");
  const refresh = () => qc.invalidateQueries({ queryKey: ["budget-status"] });
  const add = useMutation({
    mutationFn: () => api("/budgets", { body: { category_id: category ? Number(category) : null, amount } }),
    onSuccess: () => { setAmount(""); setErr(""); refresh(); },
    onError: (e: Error) => setErr(e.message),
  });
  const del = useMutation({ mutationFn: (id: number) => api(`/budgets/${id}`, { method: "DELETE" }), onSuccess: refresh });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Budgets</h1>
      <Card><CardContent className="p-5">
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
          <Field label="Category"><Select value={category} onChange={(e) => setCategory(e.target.value)}><option value="">Overall (all spending)</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>
          <Field label={`Monthly limit (${cur})`}><Input type="number" min="1" step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
          <Button disabled={add.isPending}>Add budget</Button>
        </form>
        {err && <p className="mt-2 text-sm text-destructive">{err}</p>}
      </CardContent></Card>
      <div className="grid gap-3 sm:grid-cols-2">
        {data.map((b) => (
          <Card key={b.id}><CardContent className="space-y-3 p-5">
            <div className="flex items-center justify-between">
              <p className="font-semibold">{b.category}</p>
              <Button variant="ghost" size="icon" aria-label="Delete" onClick={() => del.mutate(b.id)}><Trash2 className="h-3.5 w-3.5" /></Button>
            </div>
            <Progress value={b.percent} barClass={b.state === "over" ? "bg-red-500" : b.state === "warning" ? "bg-amber-500" : "bg-emerald-500"} />
            <div className="flex justify-between text-sm">
              <span className="tabular-nums">{money(b.spent, cur)} of {money(b.budget, cur)}</span>
              <span className={cn("font-medium", b.state === "over" ? "text-red-500" : b.state === "warning" ? "text-amber-500" : "text-muted-foreground")}>{b.percent}%</span>
            </div>
            {b.state !== "ok" && <p className="text-xs text-muted-foreground">{b.state === "over" ? "Over budget this month" : "Approaching the limit (80%+)"}</p>}
          </CardContent></Card>
        ))}
        {!data.length && <p className="text-muted-foreground">No budgets yet.</p>}
      </div>
    </div>
  );
}
