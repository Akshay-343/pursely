import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Input, Select } from "@/components/ui/input";
import { api, type Tx } from "@/lib/api";
import { useAccounts, useCategories } from "@/lib/hooks";
import { today } from "@/lib/utils";

export default function TransactionDialog({ open, onOpenChange, tx }: { open: boolean; onOpenChange: (o: boolean) => void; tx?: Tx | null }) {
  const qc = useQueryClient();
  const cats = useCategories().data ?? [];
  const accounts = useAccounts().data ?? [];
  const [f, setF] = useState({ kind: "expense", amount: "", date: today(), category_id: "", account_id: "", note: "", tags: "" });
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    setErr("");
    setF(tx
      ? { kind: tx.kind, amount: tx.amount, date: tx.date, category_id: String(tx.category_id ?? ""), account_id: String(tx.account_id ?? ""), note: tx.note ?? "", tags: tx.tags.join(", ") }
      : { kind: "expense", amount: "", date: today(), category_id: "", account_id: String(accounts[0]?.id ?? ""), note: "", tags: "" });
  }, [open, tx]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = useMutation({
    mutationFn: () => {
      const body = {
        kind: f.kind, amount: f.amount, date: f.date, note: f.note || null,
        category_id: f.category_id ? Number(f.category_id) : null,
        account_id: f.account_id ? Number(f.account_id) : null,
        tags: f.tags.split(",").map((t) => t.trim()).filter(Boolean),
      };
      return tx ? api(`/transactions/${tx.id}`, { method: "PUT", body }) : api("/transactions", { body });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["budget-status"] });
      onOpenChange(false);
    },
    onError: (e: Error) => setErr(e.message),
  });

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={tx ? "Edit transaction" : "Add transaction"}>
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
          <div className="grid grid-cols-2 gap-1 rounded-md bg-secondary p-1">
            {(["expense", "income"] as const).map((k) => (
              <button type="button" key={k} onClick={() => setF({ ...f, kind: k, category_id: "" })}
                className={`rounded-sm py-1.5 text-sm capitalize ${f.kind === k ? "bg-background shadow font-medium" : "text-muted-foreground"}`}>{k}</button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Amount"><Input type="number" step="0.01" min="0.01" required autoFocus value={f.amount} onChange={set("amount")} /></Field>
            <Field label="Date"><Input type="date" required value={f.date} onChange={set("date")} /></Field>
          </div>
          <Field label="Category">
            <Select value={f.category_id} onChange={set("category_id")}>
              <option value="">Uncategorized</option>
              {cats.filter((c) => c.kind === f.kind).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </Field>
          <Field label="Account">
            <Select value={f.account_id} onChange={set("account_id")}>
              <option value="">None</option>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>)}
            </Select>
          </Field>
          <Field label="Note"><Input value={f.note} onChange={set("note")} placeholder="Optional" /></Field>
          <Field label="Tags (comma separated)"><Input value={f.tags} onChange={set("tags")} /></Field>
          {err && <p className="text-sm text-destructive">{err}</p>}
          <Button type="submit" className="w-full" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save"}</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
