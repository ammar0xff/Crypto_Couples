export const OPERATION_STATUSES = [
  "queued",
  "uploading",
  "processing",
  "completed",
  "failed",
  "cancelled",
  "expired",
] as const;

export type OperationStatus = (typeof OPERATION_STATUSES)[number];

export const OPERATION_KINDS = ["split", "reveal"] as const;
export type OperationKind = (typeof OPERATION_KINDS)[number];

export const MEDIA_TYPES = ["image", "audio", "video", "file"] as const;
export type MediaType = (typeof MEDIA_TYPES)[number];

export const METHOD_NAMES = [
  "stack",
  "xor",
  "additive",
  "shamir",
] as const;
export type MethodName = (typeof METHOD_NAMES)[number];

export interface ErrorPayload {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface ResultFile {
  name: string;
  size: number;
}

export interface OperationSummary {
  id: string;
  kind: OperationKind;
  media: MediaType;
  method: string | null;
  status: OperationStatus;
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
}

export interface OperationDetail extends OperationSummary {
  input_names: string[];
  result_files: ResultFile[];
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  error: ErrorPayload | null;
}

export interface OperationListResponse {
  operations: OperationSummary[];
}

export interface HistoryEntry {
  id: string;
  kind: OperationKind;
  media: MediaType;
  method: string | null;
  file_name: string | null;
  status: OperationStatus;
  created_at: string;
  duration_ms: number | null;
  result_count: number | null;
}

export interface HistoryResponse {
  history: HistoryEntry[];
}

export interface HealthResponse {
  status: string;
  engine: string;
  version: string;
  timestamp: string;
}

export interface FfmpegStatus {
  available: boolean;
  path: string | null;
  version: string | null;
}

export interface ApiErrorBody {
  error?: ErrorPayload;
}

export interface ProgressEvent {
  type: "progress" | "completed" | "cancelled";
  progress: number;
  message: string;
  error?: ErrorPayload | null;
}

export interface ErrorEvent {
  type: "error";
  error: ErrorPayload;
  progress?: number;
  message?: string;
}

export type OperationEvent = ProgressEvent | ErrorEvent;