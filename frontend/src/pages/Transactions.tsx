import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Pencil, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import TransactionDialog from "@/components/TransactionDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { api, download, type Tx } from "@/lib/api";
import { useAccounts, useCategories } from "@/lib/hooks";
import { cn, money } from "@/lib/utils";

export default function Transactions() {
  const qc = useQueryClient();
  const cats = useCategories().data ?? [];
  const accounts = useAccounts().data ?? [];
  const [f, setF] = useState({ q: "", kind: "", category_id: "", account_id: "", from: "", to: "", tag: "" });
  const [page, setPage] = useState(1);
  const [edit, setEdit] = useState<Tx | null>(null);
  const [msg, setMsg] = useState("");
  const file = useRef<HTMLInputElement>(null);

  const params = new URLSearchParams({ page: String(page), page_size: "20" });
  Object.entries(f).forEach(([k, v]) => v && params.set(k, v));
  const { data } = useQuery({ queryKey: ["transactions", params.toString()], queryFn: () => api<{ items: Tx[]; total: number }>(`/transactions?${params}`) });

  const del = useMutation({
    mutationFn: (id: number) => api(`/transactions/${id}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["transactions"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); },
  });

  async function onImport(e: React.ChangeEvent<HTMLInputElement>) {
    const fl = e.target.files?.[0];
    if (!fl) return;
    const form = new FormData(); form.append("file", fl);
    try {
      const r = await api("/transactions/import", { form });
      setMsg(`Imported ${r.created} rows${r.errors.length ? `, ${r.errors.length} skipped` : ""}`);
      qc.invalidateQueries();
    } catch (err: any) { setMsg(err.message); }
    e.target.value = "";
  }

  const up = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => { setPage(1); setF({ ...f, [k]: e.target.value }); };
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / 20));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Transactions</h1>
        <div className="flex gap-2">
          <input ref={file} type="file" accept=".csv" hidden onChange={onImport} />
          <Button variant="outline" size="sm" onClick={() => file.current?.click()}><Upload className="h-4 w-4" /> Import CSV</Button>
          <Button variant="outline" size="sm" onClick={() => download("/transactions/export.csv", "transactions.csv")}><Download className="h-4 w-4" /> Export</Button>
        </div>
      </div>
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      <Card className="grid gap-2 p-3 sm:grid-cols-2 lg:grid-cols-7">
        <Input placeholder="Search notes…" value={f.q} onChange={up("q")} className="lg:col-span-2" />
        <Select value={f.kind} onChange={up("kind")}><option value="">All types</option><option value="expense">Expense</option><option value="income">Income</option></Select>
        <Select value={f.category_id} onChange={up("category_id")}><option value="">All categories</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select>
        <Select value={f.account_id} onChange={up("account_id")}><option value="">All accounts</option>{accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</Select>
        <Input type="date" value={f.from} onChange={up("from")} aria-label="From" />
        <Input type="date" value={f.to} onChange={up("to")} aria-label="To" />
      </Card>
      <Card className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b text-left text-xs text-muted-foreground">
            <tr><th className="p-3">Date</th><th>Description</th><th>Category</th><th>Account</th><th className="text-right">Amount</th><th className="w-20" /></tr>
          </thead>
          <tbody>
            {data?.items.map((t) => (
              <tr key={t.id} className="border-b last:border-0 hover:bg-accent/40">
                <td className="p-3 whitespace-nowrap">{t.date}</td>
                <td><div>{t.note || "—"}</div><div className="flex gap-1">{t.tags.map((g) => <Badge key={g} variant="secondary">{g}</Badge>)}</div></td>
                <td>{t.category ? <span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-full" style={{ background: t.category.color }} />{t.category.name}</span> : "—"}</td>
                <td>{t.account?.name ?? "—"}</td>
                <td className={cn("text-right tabular-nums font-medium", t.kind === "income" && "text-emerald-500")}>{t.kind === "income" ? "+" : "−"}{money(t.amount, t.account?.currency)}</td>
                <td className="pr-2 text-right">
                  <Button variant="ghost" size="icon" aria-label="Edit" onClick={() => setEdit(t)}><Pencil className="h-3.5 w-3.5" /></Button>
                  <Button variant="ghost" size="icon" aria-label="Delete" onClick={() => confirm("Delete this transaction?") && del.mutate(t.id)}><Trash2 className="h-3.5 w-3.5" /></Button>
                </td>
              </tr>
            ))}
            {data && !data.items.length && <tr><td colSpan={6} className="p-8 text-center text-muted-foreground">No transactions match.</td></tr>}
          </tbody>
        </table>
      </Card>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>{data?.total ?? 0} total</span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</Button>
          <span>{page} / {pages}</span>
          <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button>
        </div>
      </div>
      <TransactionDialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)} tx={edit} />
    </div>
  );
}
