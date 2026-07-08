"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { ArrowLeft, Play, Check, Trash2, Cpu } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { AssetImage } from "@/components/inpainting/asset-image";
import { JobStatusBadge } from "./job-status-badge";
import { ApiError } from "@/lib/api-client";
import { useApproveJob, useDeleteJob, useJob, useRunJob } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import type { JobPair } from "@lama-batch-inpainting/shared";

function PairColumn({
  label,
  assetKey,
  alt,
}: {
  label: string;
  assetKey: string | null;
  alt: string;
}) {
  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <AssetImage assetKey={assetKey} alt={alt} />
    </div>
  );
}

export function JobDetail({ id }: { id: string }) {
  const router = useRouter();
  const { data: job, isLoading, error, refetch } = useJob(id);
  const runJob = useRunJob();
  const approveJob = useApproveJob(id);
  const deleteJob = useDeleteJob();
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (error) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <ErrorState
        error={error}
        title={notFound ? "Job not found" : undefined}
        onRetry={notFound ? undefined : () => refetch()}
      />
    );
  }

  if (isLoading || !job) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  const completedPairs = job.pairs.filter(
    (p) => p.status === "completed" && p.output_key
  );

  const runInpainting = () =>
    runJob.mutate(job.id, {
      onSuccess: (j) =>
        toast.success(
          `Inpainting finished — ${j.pairs.filter((p) => p.status === "completed").length}/${j.pairs.length} images (device: ${j.device})`
        ),
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Run failed"),
    });

  const approveOne = (pair: JobPair) =>
    approveJob.mutate(pair.output_key ? [pair.output_key] : undefined, {
      onSuccess: () => toast.success(`${pair.source_filename} approved`),
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Approve failed"),
    });

  const approveAll = () =>
    approveJob.mutate(undefined, {
      onSuccess: () => toast.success("All outputs approved"),
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Approve failed"),
    });

  const remove = () =>
    deleteJob.mutate(job.id, {
      onSuccess: () => {
        toast.success("Job deleted");
        router.push("/jobs");
      },
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Delete failed"),
      onSettled: () => setConfirmDelete(false),
    });

  return (
    <div className="space-y-6">
      <Link
        href="/jobs"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All jobs
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0 space-y-2">
          <h1 className="page-title">{job.label ?? `Job ${job.id.slice(0, 8)}`}</h1>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <JobStatusBadge status={job.status} />
            <span>{job.pairs.length} image{job.pairs.length === 1 ? "" : "s"}</span>
            <span aria-hidden>·</span>
            <span>Created {formatDate(job.created_at)}</span>
            {job.device && (
              <span className="inline-flex items-center gap-1">
                <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
                {job.device}
              </span>
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {job.status === "pending" && (
            <Button onClick={runInpainting} disabled={runJob.isPending}>
              <Play className="h-3.5 w-3.5" aria-hidden="true" />
              {runJob.isPending ? "Running inpainting..." : "Run inpainting"}
            </Button>
          )}
          {completedPairs.length > 0 && (
            <Button
              variant="outline"
              onClick={approveAll}
              disabled={approveJob.isPending}
            >
              <Check className="h-3.5 w-3.5" aria-hidden="true" />
              Approve all
            </Button>
          )}
          <Button
            variant="outline"
            className="text-destructive hover:text-destructive"
            onClick={() => setConfirmDelete(true)}
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            Delete
          </Button>
        </div>
      </div>

      {runJob.isPending && (
        <p className="text-sm text-muted-foreground" aria-live="polite">
          Running LaMa locally over {job.pairs.length} pair
          {job.pairs.length === 1 ? "" : "s"} — this can take a moment per image.
        </p>
      )}

      <div className="space-y-4">
        {job.pairs.map((pair) => (
          <Card key={pair.source_key}>
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3 space-y-0">
              <CardTitle
                className="min-w-0 truncate text-sm font-medium"
                title={pair.source_filename}
              >
                {pair.source_filename}
              </CardTitle>
              <div className="flex items-center gap-2">
                <JobStatusBadge status={pair.status} />
                {pair.status === "completed" && pair.output_key && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => approveOne(pair)}
                    disabled={approveJob.isPending}
                  >
                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                    Approve
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-5">
              {pair.error && (
                <p className="mb-3 text-xs text-destructive">{pair.error}</p>
              )}
              <div className="grid gap-4 sm:grid-cols-3">
                <PairColumn
                  label="Source"
                  assetKey={pair.source_key}
                  alt={`Source ${pair.source_filename}`}
                />
                <PairColumn
                  label="Mask"
                  assetKey={pair.mask_key}
                  alt={`Mask for ${pair.source_filename}`}
                />
                <PairColumn
                  label="Inpainted output"
                  assetKey={pair.output_key}
                  alt={`Inpainted ${pair.source_filename}`}
                />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this job?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently deletes the job record and every inpainted output
              under its <code>images/output/{job.id}/</code> prefix. Source
              images, masks, and approved copies are not touched.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteJob.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={remove}
              disabled={deleteJob.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteJob.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
