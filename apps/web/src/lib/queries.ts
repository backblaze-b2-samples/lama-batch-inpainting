"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  approveJob,
  createJob,
  deleteFile,
  deleteJob,
  getAssetUrl,
  getFiles,
  getFileStats,
  getInpaintingStats,
  getJob,
  getJobApprovals,
  getJobs,
  getLibrary,
  getPreviewUrl,
  getUploadActivity,
  runJob,
} from "@/lib/api-client";
import type {
  FileMetadata,
  InpaintingStats,
  Job,
  JobApprovals,
  JobCreateRequest,
  LibraryItem,
} from "@lama-batch-inpainting/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  // Inpainting
  library: () => [...qk.all, "library"] as const,
  jobs: () => [...qk.all, "jobs"] as const,
  job: (id: string) => [...qk.all, "jobs", id] as const,
  jobApprovals: (id: string) => [...qk.all, "jobs", id, "approvals"] as const,
  inpaintingStats: () => [...qk.all, "inpainting-stats"] as const,
  asset: (key: string) => [...qk.all, "asset", key] as const,
};

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Inpainting ---

export function useLibrary() {
  return useQuery<LibraryItem[], ApiError>({
    queryKey: qk.library(),
    queryFn: getLibrary,
  });
}

export function useJobs() {
  return useQuery<Job[], ApiError>({
    queryKey: qk.jobs(),
    queryFn: getJobs,
  });
}

export function useJob(id: string | undefined) {
  return useQuery<Job, ApiError>({
    queryKey: qk.job(id ?? ""),
    queryFn: () => getJob(id as string),
    enabled: !!id,
    // While a run is in progress the backend persists per-pair progress to B2,
    // so poll to surface it live. Polling stops the moment the job leaves the
    // "running" state (completed/failed) — no wasted requests when idle.
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 1500 : false,
  });
}

// Persistent per-output approval state for the job review page. Fetched once
// (no polling) and refetched when useApproveJob invalidates it, so the
// "Approved" badge survives reload/return without a transient toast.
export function useJobApprovals(id: string | undefined) {
  return useQuery<JobApprovals, ApiError>({
    queryKey: qk.jobApprovals(id ?? ""),
    queryFn: () => getJobApprovals(id as string),
    enabled: !!id,
  });
}

export function useInpaintingStats() {
  return useQuery<InpaintingStats, ApiError>({
    queryKey: qk.inpaintingStats(),
    queryFn: getInpaintingStats,
  });
}

// Inline presigned URL for rendering an asset in the review UI.
export function useAssetUrl(key: string | undefined) {
  return useQuery({
    queryKey: qk.asset(key ?? ""),
    queryFn: () => getAssetUrl(key as string),
    enabled: !!key,
    staleTime: 60_000,
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: JobCreateRequest) => createJob(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.jobs() });
      qc.invalidateQueries({ queryKey: qk.inpaintingStats() });
    },
  });
}

export function useRunJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => runJob(id),
    // Optimistically flip the cached job to "running" so the UI shows a distinct
    // in-progress state and useJob starts polling immediately — before the first
    // server tick lands. Rolled back if the run request itself fails to start.
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: qk.job(id) });
      const previous = qc.getQueryData<Job>(qk.job(id));
      if (previous) {
        qc.setQueryData<Job>(qk.job(id), { ...previous, status: "running" });
      }
      return { previous };
    },
    onError: (_err, id, context) => {
      if (context?.previous) {
        qc.setQueryData(qk.job(id), context.previous);
      }
    },
    onSuccess: (job) => {
      qc.invalidateQueries({ queryKey: qk.job(job.id) });
      qc.invalidateQueries({ queryKey: qk.jobs() });
      qc.invalidateQueries({ queryKey: qk.inpaintingStats() });
    },
  });
}

export function useApproveJob(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (outputKeys?: string[]) => approveJob(id, outputKeys),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.job(id) });
      qc.invalidateQueries({ queryKey: qk.jobApprovals(id) });
      qc.invalidateQueries({ queryKey: qk.inpaintingStats() });
    },
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteJob(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.jobs() });
      qc.invalidateQueries({ queryKey: qk.inpaintingStats() });
    },
  });
}
