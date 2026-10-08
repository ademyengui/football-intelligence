export interface Match {
  id: string;
  original_filename: string;
  video_path?: string | null;
  status: 'uploaded' | 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  progress_message?: string | null;
  error_message?: string | null;
  pipeline_mode: 'real' | 'imported';
  video_fps?: number | null;
  video_width?: number | null;
  video_height?: number | null;
  video_duration_s?: number | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface TrackItem {
  track_id: number;
  team?: 'A' | 'B' | null;
  role: 'outfield' | 'other';
  detector_hint: 'player' | 'goalkeeper' | 'referee' | 'unknown';
  first_t: number;
  last_t: number;
  duration_s: number;
  n_samples: number;
  distance_m: number;
  avg_pos_m: [number, number];
}

export interface HeatmapGrid {
  width: number;
  height: number;
  bin_m: number;
}

export interface HeatmapsData {
  grid: HeatmapGrid;
  teams: {
    A: number[][];
    B: number[][];
  };
  tracks: {
    [trackId: string]: number[][];
  };
}

export interface PossessionInterval {
  start_s: number;
  end_s: number;
  state: 'A' | 'B' | 'unknown';
}

export interface PossessionSummary {
  A_pct: number;
  B_pct: number;
  unknown_pct: number;
}

export interface PossessionData {
  intervals: PossessionInterval[];
  summary: PossessionSummary;
}

export interface ResultsMeta {
  pipeline_mode: string;
  calibration: string;
  duration_s: number;
  sample_fps: number;
  frame_size: [number, number];
}

export interface MatchResults {
  schema_version: number;
  meta: ResultsMeta;
  tracks: TrackItem[];
  heatmaps: HeatmapsData;
  possession: PossessionData;
}

export interface HealthResponse {
  status: string;
  pipeline_mode: string;
}

export interface ProgressMessage {
  status: string;
  progress: number;
  message?: string | null;
  error?: string | null;
}
