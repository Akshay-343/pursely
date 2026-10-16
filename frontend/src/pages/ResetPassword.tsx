import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { resetPassword, tokens } from "@/lib/api";

export default function ResetPassword() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  // Keep the token in memory only: strip it from the address bar so it does not linger in history or leak via Referer.
  const [token] = useState(params.get("token") ?? "");
  useEffect(() => { if (params.has("token")) history.replaceState(null, "", "/reset-password"); }, [params]);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) { setErr("The two passwords do not match."); return; }
    setErr(""); setBusy(true);
    try {
      await resetPassword(token, password);
      tokens.clear(); // any session from before the reset is invalid anyway
      nav("/login", { replace: true, state: { notice: "Password changed. Sign in with your new password." } });
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardContent className="space-y-4 p-6">
          <h1 className="text-xl font-bold">Choose a new password</h1>
          {!token ? (
            <>
              <p role="alert" className="text-sm text-destructive">This reset link is missing its token. Open the link from your email again, or request a new one.</p>
              <Link to="/forgot-password" className="block text-sm text-primary hover:underline">Request a new link</Link>
            </>
          ) : (
            <form className="space-y-3" onSubmit={submit}>
              <Field label="New password (8+ characters)"><Input type="password" required minLength={8} maxLength={72} autoFocus autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
              <Field label="Confirm new password"><Input type="password" required minLength={8} maxLength={72} autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} /></Field>
              {err && <p role="alert" className="text-sm text-destructive">{err} {/expired|invalid/.test(err) && <Link to="/forgot-password" className="underline">Request a new link</Link>}</p>}
              <Button className="w-full" disabled={busy}>{busy ? "Saving…" : "Change password"}</Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
