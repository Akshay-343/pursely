import { useQuery } from "@tanstack/react-query";
import { CreditCard, Landmark, LineChart, Moon, PiggyBank, Receipt, ShieldCheck, Smartphone, Sparkles, Sun, Target, Wallet } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Field } from "@/components/Field";
import GoogleButton from "@/components/GoogleButton";
import Logo from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authConfig, googleLogin, login, register } from "@/lib/api";
import { cn } from "@/lib/utils";

type Mode = "login" | "register";

const features = [
  { icon: Receipt, title: "Every transaction", text: "Categories, tags, receipts and CSV import." },
  { icon: CreditCard, title: "Subscriptions", text: "See what renews next and what it costs a year." },
  { icon: PiggyBank, title: "Budgets", text: "Monthly limits per category, with alerts." },
  { icon: Target, title: "Savings goals", text: "A monthly plan to hit every deadline." },
  { icon: LineChart, title: "Insights", text: "Month-end projections, trends and a PDF report." },
  { icon: Sparkles, title: "Ask Pursely", text: "AI tips on where your money is going." },
];

const perks = [
  { icon: ShieldCheck, text: "Private to your account" },
  { icon: Smartphone, text: "Installs like an app" },
  { icon: Landmark, text: "Bank, cash and cards" },
];

function ThemeToggle() {
  const [dark, setDark] = useState(document.documentElement.classList.contains("dark"));
  const toggle = () => {
    const d = !dark;
    setDark(d);
    document.documentElement.classList.toggle("dark", d);
    localStorage.setItem("mt_theme", d ? "dark" : "light");
  };
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}

/** The two cards tucked into the top of the wallet. Purely decorative; they lift while the form has focus. */
function PeekingCards({ mode }: { mode: Mode }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-x-8 top-0 h-36 select-none">
      <div className="absolute left-12 right-0 top-3 h-36 rotate-[5deg] rounded-xl bg-gradient-to-br from-amber-300 via-amber-400 to-orange-500 shadow-lg motion-safe:transition-transform motion-safe:duration-500 group-focus-within:-translate-y-2 group-hover:-translate-y-1" />
      <div className="absolute left-0 right-12 top-0 h-36 -rotate-[3deg] rounded-xl bg-gradient-to-br from-teal-400 via-emerald-600 to-emerald-800 p-4 text-white shadow-xl motion-safe:transition-transform motion-safe:duration-500 group-focus-within:-translate-y-5 group-hover:-translate-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold tracking-[0.25em]">PURSELY</span>
          <span className="text-[11px] font-medium text-white/80">{mode === "login" ? "Welcome back" : "New wallet"}</span>
        </div>
        <div className="mt-3 h-6 w-9 rounded-md bg-gradient-to-br from-amber-100 via-amber-300 to-amber-500 ring-1 ring-black/10" />
      </div>
    </div>
  );
}

export default function Login() {
  const nav = useNavigate();
  const loc = useLocation();
  const notice = (loc.state as { notice?: string } | null)?.notice;
  const cfg = useQuery({ queryKey: ["auth-config"], queryFn: authConfig, staleTime: Infinity, retry: 1 });
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [currency, setCurrency] = useState("INR");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);

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

  function switchTo(m: Mode, focus = false) {
    setMode(m); setErr("");
    if (focus) emailRef.current?.focus();
  }

  const clientId = cfg.data?.google_client_id;

  return (
    <div className="relative min-h-screen overflow-x-hidden">
      {/* Background: soft brand glows over a faded dot grid. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(hsl(var(--border))_1px,transparent_1px)] [background-size:22px_22px] [mask-image:radial-gradient(ellipse_at_top,black_20%,transparent_70%)]" />
        <div className="absolute -left-40 -top-40 h-[28rem] w-[28rem] rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute -bottom-48 -right-24 h-[30rem] w-[30rem] rounded-full bg-amber-400/15 blur-3xl" />
      </div>

      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 md:px-8">
        <Logo className="text-lg" />
        <div className="flex items-center gap-1">
          {mode === "login" && (
            <Button variant="ghost" size="sm" onClick={() => switchTo("register", true)}>Create account</Button>
          )}
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-x-16 gap-y-10 px-4 pb-12 pt-2 md:px-8 lg:grid-cols-[minmax(0,1fr)_26rem] lg:pt-10">
        {/* Hero */}
        <section className="space-y-5 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-4 motion-safe:duration-700 lg:col-start-1 lg:row-start-1 lg:self-end">
          <span className="inline-flex items-center gap-2 rounded-full border bg-card/70 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur">
            <Wallet className="h-3.5 w-3.5 text-primary" /> Personal finance, calmly done
          </span>
          <h1 className="text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl lg:text-6xl">
            Your money,<br />
            <span className="bg-gradient-to-r from-primary via-emerald-500 to-amber-500 bg-clip-text text-transparent">neatly kept.</span>
          </h1>
          <p className="max-w-xl text-base text-muted-foreground sm:text-lg">
            Track spending, tame subscriptions, stick to budgets and save toward your goals, all in one wallet that fits in your pocket.
          </p>
          <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
            {perks.map(({ icon: I, text }) => (
              <li key={text} className="flex items-center gap-1.5"><I className="h-4 w-4 text-primary" />{text}</li>
            ))}
          </ul>
        </section>

        {/* Wallet login box */}
        <section aria-label={mode === "login" ? "Sign in" : "Create account"} className="group relative mx-auto w-full max-w-md pt-20 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-8 motion-safe:duration-700 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:self-center">
          <PeekingCards mode={mode} />

          {/* Leather body with stitching */}
          <div className="relative rounded-[1.75rem] bg-gradient-to-br from-emerald-700 via-emerald-900 to-teal-950 p-2.5 shadow-2xl shadow-emerald-950/30">
            <div className="rounded-[1.35rem] border-2 border-dashed border-white/25 p-2">
              {/* Pocket holding the form */}
              <div className="space-y-4 rounded-2xl bg-card p-5 text-card-foreground shadow-[inset_0_2px_6px_rgba(0,0,0,0.08)] sm:p-6">
                <div className="grid grid-cols-2 rounded-lg bg-muted p-1 text-sm font-medium">
                  {(["login", "register"] as const).map((m) => (
                    <button key={m} type="button" aria-pressed={mode === m} onClick={() => switchTo(m)}
                      className={cn("rounded-md py-1.5 transition-colors", mode === m ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}>
                      {m === "login" ? "Sign in" : "Create account"}
                    </button>
                  ))}
                </div>

                <div>
                  <h2 className="text-lg font-semibold">{mode === "login" ? "Open your wallet" : "Get your free wallet"}</h2>
                  <p className="text-sm text-muted-foreground">{mode === "login" ? "Sign in to pick up where you left off." : "Takes less than a minute to set up."}</p>
                </div>

                {notice && <p role="status" className="rounded-md bg-emerald-500/15 px-3 py-2 text-sm text-emerald-600 dark:text-emerald-400">{notice}</p>}

                {clientId && (
                  <>
                    <GoogleButton clientId={clientId} onCredential={onGoogle} onError={setErr} />
                    <div className="flex items-center gap-3 text-xs text-muted-foreground"><span className="h-px flex-1 bg-border" />or with email<span className="h-px flex-1 bg-border" /></div>
                  </>
                )}

                <form className="space-y-3" onSubmit={submit}>
                  <Field label="Email"><Input ref={emailRef} type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
                  <Field label="Password"><Input type="password" required minLength={8} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
                  {mode === "register" && (
                    <Field label="Default currency (ISO code)"><Input maxLength={3} minLength={3} required value={currency} onChange={(e) => setCurrency(e.target.value)} /></Field>
                  )}
                  {err && <p role="alert" className="text-sm text-destructive">{err}</p>}
                  <Button className="w-full" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</Button>
                </form>

                {mode === "login" && (
                  <Link to="/forgot-password" state={{ email }} className="block text-center text-sm text-muted-foreground hover:underline">Forgot password?</Link>
                )}
              </div>
            </div>

            {/* Clasp strap */}
            <div aria-hidden className="absolute -right-2 top-1/2 flex h-20 w-7 -translate-y-1/2 items-center justify-center rounded-l-xl bg-gradient-to-b from-emerald-800 to-emerald-950 shadow-md ring-1 ring-white/10">
              <span className="h-3.5 w-3.5 rounded-full bg-gradient-to-br from-amber-100 to-amber-500 shadow-inner ring-1 ring-black/20" />
            </div>
          </div>
        </section>

        {/* Features */}
        <section aria-label="Features" className="motion-safe:animate-in motion-safe:fade-in motion-safe:duration-1000 lg:col-start-1 lg:row-start-2 lg:self-start">
          <ul className="grid gap-3 sm:grid-cols-2">
            {features.map(({ icon: I, title, text }) => (
              <li key={title} className="flex gap-3 rounded-xl border bg-card/60 p-3.5 backdrop-blur transition-colors hover:border-primary/40">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><I className="h-[18px] w-[18px]" /></span>
                <span>
                  <span className="block text-sm font-semibold">{title}</span>
                  <span className="block text-sm text-muted-foreground">{text}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="mx-auto max-w-6xl px-4 pb-8 text-xs text-muted-foreground md:px-8">© {new Date().getFullYear()} Pursely</footer>
    </div>
  );
}
