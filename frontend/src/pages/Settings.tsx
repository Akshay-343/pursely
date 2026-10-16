import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useAccounts, useCategories, useMe } from "@/lib/hooks";

function AddRow({ children, onSubmit, error }: { children: React.ReactNode; onSubmit: () => void; error?: string }) {
  return (
    <form className="mt-4 flex flex-wrap items-end gap-2 border-t pt-4" onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
      {children}<Button size="sm">Add</Button>
      {error && <p className="w-full text-sm text-destructive">{error}</p>}
    </form>
  );
}

function Categories() {
  const qc = useQueryClient();
  const { data = [] } = useCategories();
  const [f, setF] = useState({ name: "", kind: "expense", color: "#6366f1" });
  const done = () => qc.invalidateQueries({ queryKey: ["categories"] });
  const add = useMutation({ mutationFn: () => api("/categories", { body: f }), onSuccess: () => { setF({ ...f, name: "" }); done(); } });
  const del = useMutation({ mutationFn: (id: number) => api(`/categories/${id}`, { method: "DELETE" }), onSuccess: done });
  return (
    <Card><CardHeader><CardTitle>Categories</CardTitle></CardHeader><CardContent>
      <div className="flex flex-wrap gap-2">
        {data.map((c) => (
          <span key={c.id} className="inline-flex items-center gap-2 rounded-full border py-1 pl-3 pr-1 text-sm">
            <i className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />{c.name}<span className="text-xs text-muted-foreground">{c.kind}</span>
            <button aria-label={`Delete ${c.name}`} className="rounded-full p-1 hover:bg-accent" onClick={() => confirm(`Delete ${c.name}? Its transactions become uncategorized.`) && del.mutate(c.id)}><Trash2 className="h-3 w-3" /></button>
          </span>
        ))}
      </div>
      <AddRow onSubmit={() => add.mutate()} error={add.error?.message}>
        <Field label="Name"><Input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Type"><Select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}><option>expense</option><option>income</option></Select></Field>
        <Field label="Color"><Input type="color" className="w-14 p-1" value={f.color} onChange={(e) => setF({ ...f, color: e.target.value })} /></Field>
      </AddRow>
    </CardContent></Card>
  );
}

function Accounts() {
  const qc = useQueryClient();
  const cur = useMe().data!.default_currency;
  const { data = [] } = useAccounts();
  const [f, setF] = useState({ name: "", type: "bank", currency: cur, opening_balance: "0" });
  const done = () => qc.invalidateQueries({ queryKey: ["accounts"] });
  const add = useMutation({ mutationFn: () => api("/accounts", { body: { ...f, currency: f.currency.toUpperCase() } }), onSuccess: () => { setF({ ...f, name: "" }); done(); } });
  const del = useMutation({ mutationFn: (id: number) => api(`/accounts/${id}`, { method: "DELETE" }), onSuccess: done });
  return (
    <Card><CardHeader><CardTitle>Accounts</CardTitle></CardHeader><CardContent>
      <ul className="divide-y text-sm">
        {data.map((a) => (
          <li key={a.id} className="flex items-center justify-between py-2">
            <span>{a.name} <span className="text-xs text-muted-foreground">· {a.type} · {a.currency}</span></span>
            <Button variant="ghost" size="icon" aria-label={`Delete ${a.name}`} onClick={() => confirm(`Delete ${a.name}?`) && del.mutate(a.id)}><Trash2 className="h-3.5 w-3.5" /></Button>
          </li>
        ))}
      </ul>
      <AddRow onSubmit={() => add.mutate()} error={add.error?.message}>
        <Field label="Name"><Input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Type"><Select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}>{["bank", "cash", "credit card", "wallet"].map((t) => <option key={t}>{t}</option>)}</Select></Field>
        <Field label="Currency"><Input className="w-20" maxLength={3} minLength={3} required value={f.currency} onChange={(e) => setF({ ...f, currency: e.target.value })} /></Field>
      </AddRow>
    </CardContent></Card>
  );
}

function Profile() {
  const qc = useQueryClient();
  const me = useMe().data!;
  const [cur, setCur] = useState(me.default_currency);
  const save = useMutation({ mutationFn: () => api("/auth/me", { method: "PATCH", body: { default_currency: cur.toUpperCase() } }), onSuccess: () => qc.invalidateQueries() });
  return (
    <Card><CardHeader><CardTitle>Profile</CardTitle></CardHeader><CardContent>
      <p className="mb-3 text-sm">{me.email}</p>
      <form className="flex items-end gap-2" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <Field label="Default currency (dashboard totals)"><Input className="w-24" maxLength={3} minLength={3} value={cur} onChange={(e) => setCur(e.target.value)} /></Field>
        <Button size="sm" disabled={save.isPending}>Save</Button>
      </form>
      <p className="mt-2 text-xs text-muted-foreground">Dashboard totals include transactions in this currency (and ones with no account). No currency conversion.</p>
    </CardContent></Card>
  );
}

export default function Settings() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>
      <Profile /><Categories /><Accounts />
    </div>
  );
}
