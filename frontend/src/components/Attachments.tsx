import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Paperclip, X } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, fetchBlobUrl, type Attachment } from "@/lib/api";

const MAX_MB = 5;

export function validateFile(f: File): string | null {
  if (!/^(image\/(jpeg|png|webp|gif)|application\/pdf)$/.test(f.type)) return "Only JPG, PNG, WebP, GIF or PDF files";
  if (f.size > MAX_MB * 1024 * 1024) return `File is larger than ${MAX_MB} MB`;
  return null;
}

export async function uploadAttachment(txId: number, f: File) {
  const form = new FormData();
  form.append("file", f);
  return api(`/transactions/${txId}/attachments`, { form });
}

/** Existing attachments of a saved transaction: list, open, upload, delete. */
export function SavedAttachments({ txId }: { txId: number }) {
  const qc = useQueryClient();
  const key = ["attachments", txId];
  const { data = [] } = useQuery({ queryKey: key, queryFn: () => api<Attachment[]>(`/transactions/${txId}/attachments`) });
  const input = useRef<HTMLInputElement>(null);
  const [err, setErr] = useState("");

  async function open(a: Attachment) {
    try { window.open(await fetchBlobUrl(`/attachments/${a.id}`), "_blank"); } catch (e: any) { setErr(e.message); }
  }
  async function add(files: FileList | null) {
    setErr("");
    for (const f of Array.from(files ?? [])) {
      const bad = validateFile(f);
      if (bad) { setErr(bad); continue; }
      try { await uploadAttachment(txId, f); } catch (e: any) { setErr(e.message); }
    }
    qc.invalidateQueries({ queryKey: key });
  }
  async function remove(a: Attachment) {
    await api(`/attachments/${a.id}`, { method: "DELETE" });
    qc.invalidateQueries({ queryKey: key });
  }
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Receipts</span>
        <input ref={input} type="file" hidden multiple accept="image/*,application/pdf" onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
        <Button type="button" variant="outline" size="sm" onClick={() => input.current?.click()}><Paperclip className="h-3.5 w-3.5" /> Attach</Button>
      </div>
      {data.map((a) => (
        <div key={a.id} className="flex items-center gap-2 rounded-md border px-2 py-1.5 text-sm">
          <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
          <button type="button" className="min-w-0 flex-1 truncate text-left hover:underline" onClick={() => open(a)}>{a.filename}</button>
          <button type="button" aria-label={`Remove ${a.filename}`} onClick={() => remove(a)}><X className="h-4 w-4" /></button>
        </div>
      ))}
      {err && <p className="text-sm text-destructive">{err}</p>}
    </div>
  );
}

/** Files picked before the transaction exists; uploaded by the parent after save. */
export function PendingAttachments({ files, setFiles }: { files: File[]; setFiles: (f: File[]) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [err, setErr] = useState("");
  function add(list: FileList | null) {
    setErr("");
    const ok = [...files];
    for (const f of Array.from(list ?? [])) {
      const bad = validateFile(f);
      if (bad) setErr(bad); else if (ok.length < 5) ok.push(f);
    }
    setFiles(ok);
  }
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Receipts</span>
        <input ref={input} type="file" hidden multiple accept="image/*,application/pdf" onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
        <Button type="button" variant="outline" size="sm" onClick={() => input.current?.click()}><Paperclip className="h-3.5 w-3.5" /> Attach</Button>
      </div>
      {files.map((f, i) => (
        <div key={i} className="flex items-center gap-2 rounded-md border px-2 py-1.5 text-sm">
          <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="min-w-0 flex-1 truncate">{f.name}</span>
          <button type="button" aria-label={`Remove ${f.name}`} onClick={() => setFiles(files.filter((_, j) => j !== i))}><X className="h-4 w-4" /></button>
        </div>
      ))}
      {err && <p className="text-sm text-destructive">{err}</p>}
    </div>
  );
}
