import { useEffect, useRef, useState } from "react";

declare global {
  interface Window { google?: any }
}

const SRC = "https://accounts.google.com/gsi/client";
let loader: Promise<void> | null = null;
function loadGsi(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  loader ??= new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = SRC; s.async = true; s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => { loader = null; reject(new Error("Could not load Google sign-in")); };
    document.head.appendChild(s);
  });
  return loader;
}

/** "Continue with Google" button (Google Identity Services). Renders nothing until the server reports a client ID. */
export default function GoogleButton({ clientId, onCredential, onError }: { clientId: string; onCredential: (c: string) => void; onError: (m: string) => void }) {
  const box = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let cancelled = false;
    loadGsi().then(() => {
      if (cancelled || !box.current) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (r: { credential?: string }) => (r.credential ? onCredential(r.credential) : onError("Google sign-in was cancelled")),
        ux_mode: "popup",
      });
      window.google.accounts.id.renderButton(box.current, {
        theme: "outline", size: "large", text: "continue_with", shape: "rectangular", width: Math.min(320, box.current.clientWidth || 320),
      });
    }).catch(() => setFailed(true));
    return () => { cancelled = true; };
  }, [clientId]); // eslint-disable-line react-hooks/exhaustive-deps
  if (failed) return <p className="text-center text-xs text-muted-foreground">Google sign-in could not load. Use your email instead.</p>;
  return <div ref={box} className="flex min-h-[44px] w-full justify-center" aria-label="Continue with Google" />;
}
