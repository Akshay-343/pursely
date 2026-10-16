import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Field } from "@/components/Field";
import GoogleButton from "@/components/GoogleButton";
import Logo from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { authConfig, demoLogin, googleLogin, login, register } from "@/lib/api";

export default function Login() {
  const nav = useNavigate();
  const loc = useLocation();
  const notice = (loc.state as { notice?: string } | null)?.notice;
  const cfg = useQuery({ queryKey: ["auth-config"], queryFn: authConfig, staleTime: Infinity, retry: 1 });
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [currency, setCurrency] = useState("INR");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      if (mode === "login") await login(email, password); else await register(email, password, currency.toUpperCase());
      nav("/", { replace: true });
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  async function onGoogle(credential: string) {
    setErr(""); setBusy(true);
    try { await googleLogin(credential); nav("/", { replace: true }); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  async function onDemo() {
    setErr(""); setBusy(true);
    try { await demoLogin(); nav("/", { replace: true }); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  const clientId = cfg.data?.google_client_id;

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardContent className="space-y-4 p-6">
          <h1><Logo className="text-xl" /></h1>
          <p className="text-sm text-muted-foreground">{mode === "login" ? "Sign in to your account" : "Create your account"}</p>
          {notice && <p role="status" className="rounded-md bg-emerald-500/15 px-3 py-2 text-sm text-emerald-600 dark:text-emerald-400">{notice}</p>}

          {cfg.data?.demo && mode === "login" && (
            <div className="space-y-1.5 rounded-md border border-primary/30 bg-primary/5 p-3">
              <Button variant="outline" className="w-full" disabled={busy} onClick={onDemo}>Try the demo, no sign-up needed</Button>
              <p className="text-center text-xs text-muted-foreground">A shared account with sample data. It resets daily.</p>
            </div>
          )}

          {clientId && (
            <>
              <GoogleButton clientId={clientId} onCredential={onGoogle} onError={setErr} />
              <div className="flex items-center gap-3 text-xs text-muted-foreground"><span className="h-px flex-1 bg-border" />or with email<span className="h-px flex-1 bg-border" /></div>
            </>
          )}

          <form className="space-y-3" onSubmit={submit}>
            <Field label="Email"><Input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
            <Field label="Password"><Input type="password" required minLength={8} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
            {mode === "register" && (
              <Field label="Default currency (ISO code)"><Input maxLength={3} minLength={3} required value={currency} onChange={(e) => setCurrency(e.target.value)} /></Field>
            )}
            {err && <p role="alert" className="text-sm text-destructive">{err}</p>}
            <Button className="w-full" disabled={busy}>{mode === "login" ? "Sign in" : "Sign up"}</Button>
          </form>
          <div className="flex items-center justify-between text-sm">
            <button className="text-primary hover:underline" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}>
              {mode === "login" ? "No account? Sign up" : "Have an account? Sign in"}
            </button>
            {mode === "login" && <Link to="/forgot-password" state={{ email }} className="text-muted-foreground hover:underline">Forgot password?</Link>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
