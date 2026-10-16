import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { forgotPassword } from "@/lib/api";

export default function ForgotPassword() {
  const [email, setEmail] = useState((useLocation().state as { email?: string } | null)?.email ?? "");
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(""); setBusy(true);
    try { await forgotPassword(email); setSent(true); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardContent className="space-y-4 p-6">
          <h1 className="text-xl font-bold">Forgot your password?</h1>
          {sent ? (
            <>
              <p role="status" className="text-sm">If an account exists for <b>{email}</b>, we've sent a link to reset your password. It works for 30 minutes. Check your spam folder if it doesn't arrive.</p>
              <Button variant="outline" className="w-full" onClick={() => setSent(false)}>Use a different email</Button>
            </>
          ) : (
            <form className="space-y-3" onSubmit={submit}>
              <p className="text-sm text-muted-foreground">Enter your email and we'll send you a link to choose a new password.</p>
              <Field label="Email"><Input type="email" required autoFocus autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
              {err && <p role="alert" className="text-sm text-destructive">{err}</p>}
              <Button className="w-full" disabled={busy}>{busy ? "Sending…" : "Send reset link"}</Button>
            </form>
          )}
          <Link to="/login" className="block text-sm text-primary hover:underline">Back to sign in</Link>
        </CardContent>
      </Card>
    </div>
  );
}
