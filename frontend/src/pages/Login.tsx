import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { login, register } from "@/lib/api";

export default function Login() {
  const nav = useNavigate();
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

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardContent className="space-y-4 p-6">
          <h1 className="text-xl font-bold">💸 Money Tracker</h1>
          <p className="text-sm text-muted-foreground">{mode === "login" ? "Sign in to your account" : "Create your account"}</p>
          <form className="space-y-3" onSubmit={submit}>
            <Field label="Email"><Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
            <Field label="Password"><Input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
            {mode === "register" && (
              <Field label="Default currency (ISO code)"><Input maxLength={3} minLength={3} required value={currency} onChange={(e) => setCurrency(e.target.value)} /></Field>
            )}
            {err && <p className="text-sm text-destructive">{err}</p>}
            <Button className="w-full" disabled={busy}>{mode === "login" ? "Sign in" : "Sign up"}</Button>
          </form>
          <button className="text-sm text-primary hover:underline" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}>
            {mode === "login" ? "No account? Sign up" : "Have an account? Sign in"}
          </button>
        </CardContent>
      </Card>
    </div>
  );
}
