import { cn } from "@/lib/utils";

export function Progress({ value, className, barClass }: { value: number; className?: string; barClass?: string }) {
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-secondary", className)}>
      <div className={cn("h-full rounded-full bg-primary transition-all", barClass)} style={{ width: `${Math.min(100, value)}%` }} />
    </div>
  );
}
