import { Badge } from "@/components/ui/badge";
import type { JobStatus, PairStatus } from "@lama-batch-inpainting/shared";

const STYLES: Record<JobStatus | PairStatus, string> = {
  pending: "border-border text-muted-foreground",
  running: "border-primary/40 text-primary [animation:pulse-border_1.6s_ease-in-out_infinite]",
  completed: "border-[var(--success)]/40 text-[var(--success)]",
  failed: "border-destructive/40 text-destructive",
};

const LABELS: Record<JobStatus | PairStatus, string> = {
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

export function JobStatusBadge({ status }: { status: JobStatus | PairStatus }) {
  return (
    <Badge variant="outline" className={`gap-1 ${STYLES[status]}`}>
      {LABELS[status]}
    </Badge>
  );
}
