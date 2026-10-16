import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CreditCard, Landmark, LayoutDashboard, LineChart, LogOut, MoreHorizontal, Moon, PiggyBank, Plus, Receipt, Settings, Sun, Target } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import Logo from "@/components/Logo";
import TransactionDialog from "@/components/TransactionDialog";
import { Button } from "@/components/ui/button";
import { api, tokens, type User } from "@/lib/api";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/subscriptions", label: "Subscriptions", icon: CreditCard },
  { to: "/budgets", label: "Budgets", icon: PiggyBank },
  { to: "/insights", label: "Insights", icon: LineChart },
  { to: "/goals", label: "Goals", icon: Target },
  { to: "/accounts", label: "Accounts", icon: Landmark },
  { to: "/settings", label: "Settings", icon: Settings },
];
const primary = nav.slice(0, 4);
const more = nav.slice(4);

type Note = { id: number; message: string; read: boolean };

function Bell_() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const { data = [] } = useQuery({ queryKey: ["notifications"], queryFn: () => api<Note[]>("/notifications"), refetchInterval: 60_000 });
  const unread = data.filter((n) => !n.read).length;
  const readAll = useMutation({
    mutationFn: () => api("/notifications/read-all", { method: "POST", body: {} }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
  return (
    <div className="relative">
      <Button variant="ghost" size="icon" aria-label="Notifications" onClick={() => { setOpen(!open); if (!open && unread) readAll.mutate(); }}>
        <Bell className="h-4 w-4" />
        {unread > 0 && <span className="absolute right-0 top-0 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] text-white">{unread}</span>}
      </Button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-72 rounded-lg border bg-card p-2 shadow-lg">
          {data.length === 0 && <p className="p-3 text-sm text-muted-foreground">No notifications</p>}
          {data.map((n) => <p key={n.id} className={cn("rounded-md p-2 text-sm", !n.read && "bg-accent")}>{n.message}</p>)}
        </div>
      )}
    </div>
  );
}

export default function Layout({ user }: { user: User }) {
  const [adding, setAdding] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [installEvt, setInstallEvt] = useState<any>(null);
  useEffect(() => {
    const h = (e: Event) => { e.preventDefault(); setInstallEvt(e); };
    window.addEventListener("beforeinstallprompt", h);
    if (new URLSearchParams(location.search).get("add") === "1") { setAdding(true); history.replaceState(null, "", "/"); }
    return () => window.removeEventListener("beforeinstallprompt", h);
  }, []);
  const [dark, setDark] = useState(document.documentElement.classList.contains("dark"));
  const toggle = () => {
    const d = !dark;
    setDark(d);
    document.documentElement.classList.toggle("dark", d);
    localStorage.setItem("mt_theme", d ? "dark" : "light");
  };
  return (
    <div className="min-h-screen md:flex">
      <aside className="hidden w-56 shrink-0 flex-col border-r bg-card p-4 md:flex">
        <Logo className="mb-6 text-lg" />
        <nav className="flex flex-1 flex-col gap-1">
          {nav.map(({ to, label, icon: I }) => (
            <NavLink key={to} to={to} end={to === "/"}
              className={({ isActive }) => cn("flex items-center gap-2 rounded-md px-3 py-2 text-sm", isActive ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground hover:bg-accent")}>
              <I className="h-4 w-4" /> {label}
            </NavLink>
          ))}
        </nav>
        <p className="truncate px-3 pb-2 text-xs text-muted-foreground">{user.email}</p>
        <Button variant="ghost" className="justify-start" onClick={() => { tokens.clear(); window.dispatchEvent(new Event("mt-logout")); }}>
          <LogOut className="h-4 w-4" /> Log out
        </Button>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col pb-20 md:pb-0">
        <header className="flex items-center justify-end gap-2 border-b px-4 py-2.5 md:px-8">
          <Logo className="mr-auto md:hidden" />
          {installEvt && <Button variant="outline" size="sm" onClick={async () => { installEvt.prompt(); await installEvt.userChoice; setInstallEvt(null); }}>Install app</Button>}
          <Button onClick={() => setAdding(true)}><Plus className="h-4 w-4" /> Add</Button>
          <Bell_ />
          <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">{dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</Button>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 p-4 md:p-8"><Outlet /></main>
      </div>
      {moreOpen && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setMoreOpen(false)}>
          <div className="absolute inset-x-3 bottom-16 grid grid-cols-4 gap-2 rounded-lg border bg-card p-3 shadow-lg" onClick={(e) => e.stopPropagation()}>
            {more.map(({ to, label, icon: I }) => (
              <NavLink key={to} to={to} onClick={() => setMoreOpen(false)} className="flex flex-col items-center gap-1 rounded-md p-2 text-xs hover:bg-accent"><I className="h-5 w-5" />{label}</NavLink>
            ))}
            <button className="flex flex-col items-center gap-1 rounded-md p-2 text-xs hover:bg-accent" onClick={() => { tokens.clear(); window.dispatchEvent(new Event("mt-logout")); }}><LogOut className="h-5 w-5" />Log out</button>
          </div>
        </div>
      )}
      <nav className="fixed inset-x-0 bottom-0 z-30 flex justify-around border-t bg-card pb-[env(safe-area-inset-bottom)] pt-1.5 md:hidden">
        {primary.map(({ to, label, icon: I }) => (
          <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => cn("flex flex-col items-center gap-0.5 px-2 py-1 text-[10px]", isActive ? "text-primary" : "text-muted-foreground")}>
            <I className="h-5 w-5" />{label}
          </NavLink>
        ))}
        <button onClick={() => setMoreOpen(!moreOpen)} className="flex flex-col items-center gap-0.5 px-2 py-1 text-[10px] text-muted-foreground"><MoreHorizontal className="h-5 w-5" />More</button>
      </nav>
      <TransactionDialog open={adding} onOpenChange={setAdding} />
    </div>
  );
}
