import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, PiggyBank, RefreshCw, Send, Sparkles, ThumbsUp } from "lucide-react";
import { Fragment, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { aiAsk, aiTips, type AiTurn } from "@/lib/api";
import { useAiEnabled } from "@/lib/hooks";
import { cn } from "@/lib/utils";

const kinds = {
  saving: { icon: PiggyBank, tone: "text-primary bg-primary/10" },
  warning: { icon: AlertTriangle, tone: "text-amber-600 bg-amber-500/10 dark:text-amber-400" },
  positive: { icon: ThumbsUp, tone: "text-emerald-600 bg-emerald-500/10 dark:text-emerald-400" },
};

export function AiTips() {
  const enabled = useAiEnabled();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["ai-tips"], queryFn: () => aiTips(), enabled, staleTime: 10 * 60_000, retry: false });
  const refresh = useMutation({ mutationFn: () => aiTips(true), onSuccess: (d) => qc.setQueryData(["ai-tips"], d) });
  if (!enabled) return null;
  const busy = q.isLoading || refresh.isPending;
  const err = (refresh.error ?? q.error) as Error | null;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-primary" /> AI tips</CardTitle>
        <Button variant="ghost" size="icon" aria-label="Refresh tips" disabled={busy} onClick={() => refresh.mutate()}>
          <RefreshCw className={cn("h-4 w-4", busy && "animate-spin")} />
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {busy && !q.data ? <p className="text-sm text-muted-foreground">Looking through your spending…</p>
          : err && !q.data ? <p className="text-sm text-muted-foreground">{err.message}</p>
          : q.data && (
            <>
              <p className="text-sm">{q.data.summary}</p>
              {q.data.tips.length > 0 && (
                <ul className="grid gap-3 sm:grid-cols-2">
                  {q.data.tips.map((t) => {
                    const k = kinds[t.kind] ?? kinds.saving;
                    return (
                      <li key={t.title} className="flex gap-3 rounded-md border p-3">
                        <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-full", k.tone)}><k.icon className="h-4 w-4" /></span>
                        <div className="min-w-0"><p className="text-sm font-medium">{t.title}</p><p className="text-xs text-muted-foreground">{t.detail}</p></div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </>
          )}
        {err && q.data && <p className="text-xs text-red-500">{err.message}</p>}
      </CardContent>
    </Card>
  );
}

const suggestions = ["How can I reduce my spending?", "Am I on track this month?", "Which subscriptions should I review?", "How much could I save each month?"];

export function AskAi() {
  const enabled = useAiEnabled();
  const [thread, setThread] = useState<AiTurn[]>([]);
  const [text, setText] = useState("");
  const ask = useMutation({
    mutationFn: (question: string) => aiAsk(question, thread),
    onSuccess: (d, question) => { setThread((t) => [...t, { role: "user", content: question }, { role: "assistant", content: d.answer }]); setText(""); },
  });
  if (!enabled) return null;
  const send = (question: string) => { if (question.trim().length >= 2 && !ask.isPending) ask.mutate(question.trim()); };

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-primary" /> Ask Pursely</CardTitle>
        {thread.length > 0 && <Button variant="ghost" size="sm" onClick={() => { setThread([]); ask.reset(); }}>Clear</Button>}
      </CardHeader>
      <CardContent className="space-y-3">
        {thread.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button key={s} disabled={ask.isPending} onClick={() => send(s)}
                className="rounded-full border px-3 py-1 text-xs text-muted-foreground hover:bg-accent disabled:opacity-50">{s}</button>
            ))}
          </div>
        )}
        {thread.map((m, i) => (
          <div key={i} className={cn("rounded-lg px-3 py-2 text-sm", m.role === "user" ? "ml-auto w-fit max-w-[85%] bg-primary text-primary-foreground" : "bg-muted")}>
            {m.role === "user" ? m.content : <Answer text={m.content} />}
          </div>
        ))}
        {ask.isPending && <p className="text-sm text-muted-foreground">Thinking…</p>}
        {ask.error && <p className="text-sm text-red-500">{(ask.error as Error).message}</p>}
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); send(text); }}>
          <Input value={text} maxLength={500} placeholder="Ask about your spending, budgets or savings" aria-label="Question" onChange={(e) => setText(e.target.value)} />
          <Button type="submit" size="icon" className="h-9 w-9 shrink-0" aria-label="Send" disabled={ask.isPending || text.trim().length < 2}><Send className="h-4 w-4" /></Button>
        </form>
        <p className="text-xs text-muted-foreground">Answers are generated from a summary of your data and can be wrong. Not financial advice.</p>
      </CardContent>
    </Card>
  );
}

/** Renders the small subset of Markdown the model uses: paragraphs, "-"/"*"/"1." lists and **bold**. */
function Answer({ text }: { text: string }) {
  const bold = (s: string) => s.split(/\*\*(.+?)\*\*/g).map((p, i) => (i % 2 ? <strong key={i}>{p}</strong> : <Fragment key={i}>{p}</Fragment>));
  const blocks: { list: boolean; lines: string[] }[] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) { blocks.push({ list: false, lines: [] }); continue; }
    const item = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)$/);
    const last = blocks[blocks.length - 1];
    if (last && last.list === !!item && (item || last.lines.length)) last.lines.push(item ? item[1] : line);
    else blocks.push({ list: !!item, lines: [item ? item[1] : line] });
  }
  return (
    <div className="space-y-2">
      {blocks.filter((b) => b.lines.length).map((b, i) => b.list
        ? <ul key={i} className="list-disc space-y-1 pl-5">{b.lines.map((l, j) => <li key={j}>{bold(l)}</li>)}</ul>
        : <p key={i}>{b.lines.map((l, j) => <Fragment key={j}>{j > 0 && " "}{bold(l)}</Fragment>)}</p>)}
    </div>
  );
}
