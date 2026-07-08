"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Images, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { AssetImage } from "@/components/inpainting/asset-image";
import { ApiError } from "@/lib/api-client";
import { useCreateJob, useLibrary } from "@/lib/queries";

export function JobCreateForm() {
  const router = useRouter();
  const { data: items = [], isLoading, error, refetch } = useLibrary();
  const createJob = useCreateJob();

  const [label, setLabel] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const pairable = items.filter((i) => i.has_mask);

  const toggle = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const submit = () => {
    if (selected.size === 0) {
      toast.info("Select at least one paired source image.");
      return;
    }
    createJob.mutate(
      { label: label.trim() || null, source_keys: Array.from(selected) },
      {
        onSuccess: (job) => {
          toast.success("Job created");
          router.push(`/jobs/${job.id}`);
        },
        onError: (err) => {
          toast.error(
            err instanceof ApiError ? err.message : "Failed to create job"
          );
        },
      }
    );
  };

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} title="Couldn't load sources" onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">New inpainting job</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6 p-5">
        {/* Label — genuine free text is fine here. */}
        <div className="space-y-2">
          <Label htmlFor="job-label">Label</Label>
          <Input
            id="job-label"
            placeholder="e.g. Listing photos — remove watermarks"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="max-w-md"
          />
          <p className="text-xs text-muted-foreground">
            Optional. A name to recognize this run later — leave blank for an
            auto-generated one.
          </p>
        </div>

        {/* Source selection — a selector over the finite set actually present,
            never free text. Masks pair automatically by base filename. */}
        <div className="space-y-2">
          <Label>Source images</Label>
          <p className="text-xs text-muted-foreground">
            Pick sources that have a matching mask — only those can run. Masks
            pair automatically by base filename.
          </p>

          {isLoading ? (
            <div className="grid gap-2 pt-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : pairable.length === 0 ? (
            <EmptyState
              icon={Images}
              title="No paired sources yet"
              description="Upload a source image and a mask with the same base filename to get started."
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
            <div className="grid gap-2 pt-1">
              {pairable.map((item) => {
                const checked = selected.has(item.source_key);
                return (
                  <label
                    key={item.source_key}
                    className={[
                      "flex cursor-pointer items-center gap-3 rounded-md border p-2.5 transition-colors",
                      checked
                        ? "border-primary bg-[var(--accent-subtle)]"
                        : "border-border hover:border-foreground/20",
                    ].join(" ")}
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={() => toggle(item.source_key)}
                    />
                    <div className="w-12 shrink-0">
                      <AssetImage assetKey={item.source_key} alt={item.source_filename} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium" title={item.source_filename}>
                        {item.source_filename}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {item.size_human} · mask paired
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-border pt-4">
          <p className="text-xs text-muted-foreground">
            {selected.size} selected
          </p>
          <Button
            onClick={submit}
            disabled={createJob.isPending || selected.size === 0}
          >
            {createJob.isPending ? "Creating..." : "Create job"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
