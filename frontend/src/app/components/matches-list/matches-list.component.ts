import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { ApiService } from '../../services/api.service';
import { Match } from '../../models/match.model';

@Component({
  selector: 'app-matches-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="mx-auto max-w-6xl space-y-6 px-4 py-8">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-white tracking-tight">Match Analytics List</h1>
          <p class="text-sm text-slate-400 mt-1">View processed broadcast clips, track progress, or launch new analysis jobs.</p>
        </div>
        <a
          routerLink="/"
          class="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 hover:bg-blue-500 transition">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Upload New Match
        </a>
      </div>

      <!-- Matches Table -->
      @if (loading && matches.length === 0) {
        <div class="space-y-4 rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-400">
          <div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-500 border-r-transparent"></div>
          <p class="text-sm">Loading matches...</p>
        </div>
      } @else if (matches.length === 0) {
        <div class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-12 text-center">
          <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-800 bg-slate-800/50 text-slate-400">
            <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-white">No matches found</h3>
          <p class="mt-1 text-sm text-slate-400">Upload your first broadcast match clip to start generating player heatmaps and analytics.</p>
          <a
            routerLink="/"
            class="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-blue-500 transition">
            Upload Match Clip
          </a>
        </div>
      } @else {
        <div class="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 shadow-xl">
          <table class="w-full text-left text-sm text-slate-300">
            <thead class="bg-slate-950 text-xs uppercase text-slate-400 border-b border-slate-800">
              <tr>
                <th scope="col" class="px-6 py-4">Filename</th>
                <th scope="col" class="px-6 py-4">Status</th>
                <th scope="col" class="px-6 py-4">Progress</th>
                <th scope="col" class="px-6 py-4">Mode</th>
                <th scope="col" class="px-6 py-4">Created</th>
                <th scope="col" class="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/60">
              @for (match of matches; track match.id) {
                <tr class="hover:bg-slate-800/40 transition">
                  <!-- Filename -->
                  <td class="px-6 py-4 font-medium text-white">
                    <a [routerLink]="['/matches', match.id]" class="hover:text-blue-400 hover:underline">
                      {{ match.original_filename }}
                    </a>
                  </td>

                  <!-- Status Chip -->
                  <td class="px-6 py-4">
                    <span
                      class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold capitalize"
                      [ngClass]="{
                        'bg-blue-950 text-blue-400 border border-blue-500/30': match.status === 'completed',
                        'bg-amber-950 text-amber-400 border border-amber-500/30': match.status === 'processing' || match.status === 'queued',
                        'bg-slate-800 text-slate-300 border border-slate-700': match.status === 'uploaded',
                        'bg-rose-950 text-rose-400 border border-rose-500/30': match.status === 'failed'
                      }">
                      <span class="h-1.5 w-1.5 rounded-full" [ngClass]="{
                        'bg-blue-400': match.status === 'completed',
                        'bg-amber-400 animate-ping': match.status === 'processing',
                        'bg-slate-400': match.status === 'uploaded' || match.status === 'queued',
                        'bg-rose-400': match.status === 'failed'
                      }"></span>
                      {{ match.status }}
                    </span>
                  </td>

                  <!-- Progress Bar -->
                  <td class="px-6 py-4">
                    <div class="flex items-center gap-3">
                      <div class="h-2 w-24 overflow-hidden rounded-full bg-slate-800">
                        <div
                          class="h-full bg-blue-500 transition-all duration-300"
                          [style.width.%]="match.progress">
                        </div>
                      </div>
                      <span class="text-xs font-semibold text-slate-400">{{ match.progress }}%</span>
                    </div>
                  </td>

                  <!-- Mode Badge -->
                  <td class="px-6 py-4">
                    <span class="rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium uppercase text-slate-300">
                      {{ match.pipeline_mode }}
                    </span>
                  </td>

                  <!-- Created Time -->
                  <td class="px-6 py-4 text-xs text-slate-400">
                    {{ formatDate(match.created_at) }}
                  </td>

                  <!-- Actions -->
                  <td class="px-6 py-4 text-right">
                    <div class="flex items-center justify-end gap-3">
                      <a
                        [routerLink]="['/matches', match.id]"
                        class="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-semibold text-blue-400 hover:bg-slate-700 hover:text-blue-300 transition">
                        Open
                      </a>
                      <button
                        type="button"
                        (click)="confirmDelete(match)"
                        [disabled]="match.status === 'processing'"
                        class="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-semibold text-rose-400 hover:bg-rose-950 hover:text-rose-300 transition disabled:opacity-30">
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }

      <!-- Delete Confirmation Modal -->
      @if (matchToDelete) {
        <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <div class="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <h3 class="text-lg font-bold text-white">Delete Match Record</h3>
            <p class="text-sm text-slate-400">
              Are you sure you want to delete <strong class="text-slate-200">{{ matchToDelete.original_filename }}</strong>? This will permanently delete database records and stored video files.
            </p>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                (click)="matchToDelete = null"
                class="rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700">
                Cancel
              </button>
              <button
                type="button"
                (click)="executeDelete()"
                class="rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-500">
                Confirm Delete
              </button>
            </div>
          </div>
        </div>
      }
    </div>
  `
})
export class MatchesListComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);

  matches: Match[] = [];
  loading = true;
  matchToDelete: Match | null = null;
  private pollSub?: Subscription;

  ngOnInit(): void {
    this.loadMatches();
    // Poll every 5s while page is active
    this.pollSub = interval(5000).subscribe(() => this.loadMatches(false));
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }

  loadMatches(showLoading = true): void {
    if (showLoading) this.loading = true;
    this.api.listMatches().subscribe({
      next: (data) => {
        this.matches = data;
        this.loading = false;
      },
      error: () => this.loading = false
    });
  }

  confirmDelete(match: Match): void {
    this.matchToDelete = match;
  }

  executeDelete(): void {
    if (!this.matchToDelete) return;
    const matchId = this.matchToDelete.id;
    this.matchToDelete = null;

    this.api.deleteMatch(matchId).subscribe({
      next: () => this.loadMatches(false),
      error: (err) => alert(err.error?.detail || 'Failed to delete match')
    });
  }

  formatDate(isoString: string): string {
    try {
      return new Date(isoString).toLocaleString();
    } catch {
      return isoString;
    }
  }
}
