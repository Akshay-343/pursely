import { cn } from "@/lib/utils";

export default function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2 font-bold tracking-tight", className)}>
      <img src="/favicon.svg" alt="" className="h-7 w-7" />
      Pursely
    </span>
  );
}
