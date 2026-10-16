import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRightLeft, Trash2 } from "lucide-react";
import { useState } from "react";
import { Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api";
import { money, today } from "@/lib/utils";

type Bal = { id: number; name: string; type: string; currency: string; balance: string };
type Transfer = { id: number; from_account_id: number; to_account_id: number; amount: string; date: string; note: string | null };

export default function Accounts() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["balances"], queryFn: () => api<{ accounts: Bal[]; net_worth_by_currency: Record<string, string> }>("/accounts/balances") });
  const transfers = useQuery({ queryKey: ["transfers"], queryFn: () => api<Transfer[]>("/transfers") });
  const accounts = data?.accounts ?? [];
  const name = (id: number) => accounts.find((a) => a.id === id)?.name ?? "Deleted account";
  const [f, setF] = useState({ from: "", to: "", amount: "", date: today(), note: "" });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["balances"] }); qc.invalidateQueries({ queryKey: ["transfers"] }); };
  const add = useMutation({
    mutationFn: () => api("/transfers", { body: { from_account_id: Number(f.from), to_account_id: Number(f.to), amount: f.amount, date: f.date, note: f.note || null } }),
    onSuccess: () => { setF({ ...f, amount: "", note: "" }); refresh(); },
  });
  const del = useMutation({ mutationFn: (id: number) => api(`/transfers/${id}`, { method: "DELETE" }), onSuccess: refresh });
  const fromCur = accounts.find((a) => a.id === Number(f.from))?.currency;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Accounts</h1>
      <Card>
        <CardHeader><CardTitle>Net worth</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-x-8 gap-y-1">
          {data && Object.keys(data.net_worth_by_currency).length ? Object.entries(data.net_worth_by_currency).map(([c, v]) => (
            <p key={c} className="text-3xl font-bold tabular-nums">{money(v, c)}</p>
          )) : <p className="text-muted-foreground">Add an account in Settings to see balances.</p>}
        </CardContent>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {accounts.map((a) => (
          <Card key={a.id}><CardContent className="p-5">
            <p className="text-sm text-muted-foreground">{a.name} · {a.type}</p>
            <p className={`text-2xl font-bold tabular-nums ${Number(a.balance) < 0 ? "text-red-500" : ""}`}>{money(a.balance, a.currency)}</p>
          </CardContent></Card>
        ))}
      </div>
      <Card>
        <CardHeader><CardTitle>Transfer between accounts</CardTitle></CardHeader>
        <CardContent>
          <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
            <Field label="From"><Select required value={f.from} onChange={(e) => setF({ ...f, from: e.target.value, to: "" })}><option value="">Choose…</option>{accounts.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>)}</Select></Field>
            <Field label="To"><Select required value={f.to} onChange={(e) => setF({ ...f, to: e.target.value })}><option value="">Choose…</option>{accounts.filter((a) => String(a.id) !== f.from && (!fromCur || a.currency === fromCur)).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</Select></Field>
            <Field label="Amount"><Input type="number" min="0.01" step="0.01" required value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></Field>
            <Field label="Date"><Input type="date" required value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></Field>
            <div className="flex items-end"><Button className="w-full" disabled={add.isPending}><ArrowRightLeft className="h-4 w-4" /> Transfer</Button></div>
          </form>
          {add.error && <p className="mt-2 text-sm text-destructive">{add.error.message}</p>}
          <ul className="mt-4 divide-y text-sm">
            {transfers.data?.slice(0, 10).map((t) => (
              <li key={t.id} className="flex items-center justify-between py-2">
                <span>{t.date} · {name(t.from_account_id)} → {name(t.to_account_id)}</span>
                <span className="flex items-center gap-2"><span className="tabular-nums">{money(t.amount, accounts.find((a) => a.id === t.from_account_id)?.currency)}</span>
                  <Button variant="ghost" size="icon" aria-label="Delete transfer" onClick={() => del.mutate(t.id)}><Trash2 className="h-3.5 w-3.5" /></Button></span>
              </li>
            ))}
          </ul>
          {transfers.data && !transfers.data.length && <p className="mt-3 text-sm text-muted-foreground">No transfers yet. Transfers move money between your accounts and do not count as spending.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
