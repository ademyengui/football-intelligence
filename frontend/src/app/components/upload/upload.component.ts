import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Injectable_Unused()
@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="mx-auto max-w-4xl space-y-8 px-4 py-8">
      <!-- Header Banner -->
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl backdrop-blur-sm">
        <div>
          <h1 class="text-2xl font-bold text-white tracking-tight">Upload Match Video</h1>
          <p class="text-sm text-slate-400 mt-1">Upload a broadcast match video clip (.mp4, .mkv up to 2 GB) for automated AI analytics.</p>
        </div>
        <div class="flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-950/40 px-3 py-1.5 text-xs font-semibold text-blue-400">
          <span class="h-2 w-2 rounded-full bg-blue-400 animate-pulse"></span>
          <span>Pipeline Mode: <strong class="uppercase">{{ pipelineMode }}</strong></span>
        </div>
      </div>

      <!-- Upload Box -->
      <div
        class="relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-12 text-center transition-all duration-300"
        [ngClass]="{
          'border-blue-500 bg-blue-950/20 scale-[1.01]': isDragging,
          'border-slate-700 bg-slate-900/60 hover:border-slate-500': !isDragging && !isUploading,
          'opacity-60 pointer-events-none': isUploading
        }"
        (dragover)="onDragOver($event)"
        (dragleave)="onDragLeave($event)"
        (drop)="onDrop($event)">

        <input
          #fileInput
          type="file"
          accept=".mp4,.mkv"
          class="hidden"
          (change)="onFileSelected($event)">

        <!-- Upload Icon -->
        <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-700 bg-slate-800/80 text-blue-400 shadow-lg">
          <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>

        <h3 class="text-lg font-semibold text-white">Drag and drop your broadcast video file here</h3>
        <p class="mt-1 text-sm text-slate-400">Supports MP4 and MKV containers (max 2 GB)</p>

        <button
          type="button"
          (click)="fileInput.click()"
          [disabled]="isUploading"
          class="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Browse Local Files
        </button>

        <!-- Progress Bar -->
        @if (isUploading) {
          <div class="mt-8 w-full max-w-md space-y-2">
            <div class="flex justify-between text-xs font-medium text-slate-300">
              <span>Streaming video to server...</span>
              <span>{{ uploadProgress }}%</span>
            </div>
            <div class="h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div class="h-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-200" [style.width.%]="uploadProgress"></div>
            </div>
          </div>
        }

        <!-- Error Message Alert -->
        @if (errorMessage) {
          <div class="mt-6 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-950/50 p-4 text-xs font-medium text-rose-300 shadow-md">
            <svg class="h-5 w-5 shrink-0 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ errorMessage }}</span>
          </div>
        }
      </div>
    </div>
  `
})
export class UploadComponent implements OnInit {
  private api = inject(ApiService);
  private router = inject(Router);

  pipelineMode = 'real';
  isDragging = false;
  isUploading = false;
  uploadProgress = 0;
  errorMessage: string | null = null;

  ngOnInit(): void {
    this.api.getHealth().subscribe({
      next: (res) => this.pipelineMode = res.pipeline_mode,
      error: () => this.pipelineMode = 'real'
    });
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;

    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      this.handleFile(event.dataTransfer.files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFile(input.files[0]);
    }
  }

  private handleFile(file: File): void {
    this.errorMessage = null;

    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (ext !== '.mp4' && ext !== '.mkv') {
      this.errorMessage = `Invalid file format '${ext}'. Please upload an .mp4 or .mkv video file.`;
      return;
    }

    const maxBytes = 2 * 1024 * 1024 * 1024; // 2 GB
    if (file.size > maxBytes) {
      this.errorMessage = `File size (${(file.size / (1024 * 1024 * 1024)).toFixed(2)} GB) exceeds the 2 GB limit.`;
      return;
    }

    this.isUploading = true;
    this.uploadProgress = 0;

    this.api.uploadMatch(file).subscribe({
      next: (res) => {
        this.uploadProgress = res.progress;
        if (res.match) {
          const matchId = res.match.id;
          // Auto-start processing and navigate
          this.api.processMatch(matchId).subscribe({
            next: () => this.router.navigate(['/matches', matchId]),
            error: (err) => {
              console.error('Failed to start processing', err);
              this.router.navigate(['/matches', matchId]);
            }
          });
        }
      },
      error: (err) => {
        this.isUploading = false;
        this.errorMessage = err.error?.detail || 'Failed to upload video file. Please check server logs.';
      }
    });
  }
}

function Injectable_Unused() { return (target: any) => target; }
