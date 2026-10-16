import { cn } from "@/lib/utils";

export default function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2 font-bold tracking-tight", className)}>
      <img src="/icon-192.png" alt="" className="h-8 w-8" />
      Pursely
    </span>
  );
}
