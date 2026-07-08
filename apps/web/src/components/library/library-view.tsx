"use client";

import Link from "next/link";
import { Images, CheckCircle2, AlertCircle, Upload, Wand2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { AssetImage } from "@/components/inpainting/asset-image";
import { useLibrary } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

export function LibraryView() {
  const { data: items = [], isLoading, error, refetch } = useLibrary();
  const paired = items.filter((i) => i.has_mask).length;

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState
            error={error}
            title="Couldn't load the library"
            onRetry={() => refetch()}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4 space-y-0">
        <div>
          <CardTitle className="card-title">Source images</CardTitle>
          {!isLoading && (
            <p className="mt-1 text-xs text-muted-foreground">
              {items.length} source{items.length === 1 ? "" : "s"} · {paired}{" "}
              with a matching mask
            </p>
          )}
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/jobs/new">
            <Wand2 className="h-3.5 w-3.5" aria-hidden="true" />
            New job
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="aspect-square w-full rounded-md" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            icon={Images}
            title="No source images yet"
            description="Upload a source image (and its mask) to build your library."
            action={
              <Button asChild size="sm">
                <Link href="/upload">
                  <Upload aria-hidden="true" className="h-3.5 w-3.5" />
                  Upload images
                </Link>
              </Button>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {items.map((item) => (
              <div
                key={item.source_key}
                className="flex flex-col gap-2 rounded-md border border-border p-2.5 animate-fade-in-up"
              >
                <AssetImage assetKey={item.source_key} alt={item.source_filename} />
                <div className="min-w-0">
                  <p
                    className="truncate text-sm font-medium"
                    title={item.source_filename}
                  >
                    {item.source_filename}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {item.size_human} · {formatDate(item.uploaded_at)}
                  </p>
                </div>
                {item.has_mask ? (
                  <Badge
                    variant="outline"
                    className="w-fit gap-1 border-[var(--success)]/40 text-[var(--success)]"
                  >
                    <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                    Mask paired
                  </Badge>
                ) : (
                  <Badge variant="outline" className="w-fit gap-1 text-muted-foreground">
                    <AlertCircle className="h-3 w-3" aria-hidden="true" />
                    No mask
                  </Badge>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
