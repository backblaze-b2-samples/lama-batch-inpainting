export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- LaMa batch inpainting ---

export type JobStatus = "pending" | "running" | "completed" | "failed";
export type PairStatus = "pending" | "completed" | "failed";

export interface JobPair {
  source_key: string;
  source_filename: string;
  mask_key: string | null;
  output_key: string | null;
  status: PairStatus;
  error: string | null;
}

export interface Job {
  id: string;
  label: string | null;
  status: JobStatus;
  created_at: string;
  completed_at: string | null;
  model: string;
  device: string | null;
  pairs: JobPair[];
}

export interface JobCreateRequest {
  label?: string | null;
  source_keys: string[];
}

export interface ApproveRequest {
  output_keys?: string[] | null;
}

export interface LibraryItem {
  source_key: string;
  source_filename: string;
  size_bytes: number;
  size_human: string;
  uploaded_at: string;
  has_mask: boolean;
  mask_key: string | null;
}

export interface PrefixBytes {
  prefix: string;
  bytes: number;
  count: number;
}

export interface InpaintingStats {
  total_jobs: number;
  completed_jobs: number;
  images_inpainted: number;
  approved_count: number;
  source_bytes: number;
  mask_bytes: number;
  output_bytes: number;
  approved_bytes: number;
  // Object-count amplification (source + mask + output per source) — the ~3x story.
  object_amplification: number;
  // Byte ratio ((output + masks) / source bytes) — secondary detail, stays near 1x.
  amplification_ratio: number;
  by_prefix: PrefixBytes[];
}

export interface JobApprovals {
  job_id: string;
  approved_output_keys: string[];
}
