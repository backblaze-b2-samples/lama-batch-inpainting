"use client";

import { Layers } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useInpaintingStats } from "@/lib/queries";
import { humanizeBytes } from "@/lib/utils";

const PREFIX_COLOR: Record<string, string> = {
  source: "var(--chart-1)",
  masks: "var(--chart-2)",
  output: "var(--chart-3)",
  approved: "var(--chart-4)",
};

const PREFIX_LABEL: Record<string, string> = {
  source: "Source",
  masks: "Masks",
  output: "Output",
  approved: "Approved",
};

export function PrefixBytesChart() {
  const { data: stats, isLoading, error, refetch } = useInpaintingStats();

  const rows = stats?.by_prefix ?? [];
  const max = Math.max(1, ...rows.map((r) => r.bytes));
  const hasData = rows.some((r) => r.bytes > 0);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Storage by prefix</CardTitle>
        <CardDescription className="text-xs">
          Every source keeps its mask and gains a full-resolution output — a
          remediation project stores several times its input.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : !hasData ? (
          <EmptyState
            icon={Layers}
            title="No storage yet"
            description="Upload sources and run a job to see the amplification story."
          />
        ) : (
          <div className="space-y-4">
            {rows.map((row) => (
              <div key={row.prefix} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{PREFIX_LABEL[row.prefix]}</span>
                  <span className="font-mono text-xs text-muted-foreground tabular-nums">
                    {humanizeBytes(row.bytes)} · {row.count} file
                    {row.count === 1 ? "" : "s"}
                  </span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.max(2, (row.bytes / max) * 100)}%`,
                      backgroundColor: PREFIX_COLOR[row.prefix],
                    }}
                  />
                </div>
              </div>
            ))}
            {stats && (
              <div className="space-y-1 border-t border-border pt-3 text-xs text-muted-foreground">
                <p>
                  Object amplification:{" "}
                  <span className="font-semibold text-foreground">
                    {stats.object_amplification.toFixed(1)}×
                  </span>{" "}
                  — every source retains its mask and gains an inpainted output
                  (≈3 stored objects per source).
                </p>
                <p>
                  Byte amplification:{" "}
                  <span className="font-semibold text-foreground">
                    {stats.amplification_ratio.toFixed(2)}×
                  </span>{" "}
                  — (output + masks) relative to source bytes.
                </p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
