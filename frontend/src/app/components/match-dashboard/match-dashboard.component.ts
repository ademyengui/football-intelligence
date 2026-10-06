import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';

import { ApiService } from '../../services/api.service';
import { WebsocketService } from '../../services/websocket.service';
import { Match, MatchResults, TrackItem } from '../../models/match.model';
import { PitchHeatmapComponent } from '../../charts/pitch-heatmap.component';
import { PossessionTimelineComponent } from '../../charts/possession-timeline.component';

@Component({
  selector: 'app-match-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, PitchHeatmapComponent, PossessionTimelineComponent],
  template: `
    <div class="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <!-- Header Banner -->
      @if (match) {
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
          <div>
            <div class="flex items-center gap-3">
              <h1 class="text-2xl font-bold text-white tracking-tight">{{ match.original_filename }}</h1>
              <span class="rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-semibold uppercase text-slate-300">
                {{ match.pipeline_mode }}
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-1">
              Duration: {{ match.video_duration_s ? match.video_duration_s.toFixed(1) + 's' : 'N/A' }} |
              Resolution: {{ match.video_width && match.video_height ? match.video_width + 'x' + match.video_height : 'N/A' }} |
              FPS: {{ match.video_fps ? match.video_fps.toFixed(1) : 'N/A' }}
            </p>
          </div>

          <!-- Actions & Status -->
          <div class="flex items-center gap-3">
            @if (results) {
              <a
                [href]="api.getExportTracksUrl(match.id)"
                download
                class="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition">
                <svg class="h-4 w-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Tracks CSV
              </a>

              <a
                [href]="api.getExportPossessionUrl(match.id)"
                download
                class="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition">
                <svg class="h-4 w-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Possession CSV
              </a>
            }

            <a routerLink="/matches" class="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white transition">
              Back to List
            </a>
          </div>
        </div>
      }

      <!-- Naive Calibration Warning Banner -->
      @if (results && results.meta.calibration === 'naive') {
        <div class="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-950/40 p-4 text-xs font-medium text-amber-300 shadow-lg">
          <svg class="h-5 w-5 shrink-0 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>Positions and distances are approximate: pitch calibration is not yet enabled. Distances are prefixed with "≈".</span>
        </div>
      }

      <!-- Non-Terminal Status & Progress Card -->
      @if (match && match.status !== 'completed' && match.status !== 'failed') {
        <div class="rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-xl text-center space-y-6">
          <div class="inline-flex h-16 w-16 items-center justify-center rounded-2xl border border-blue-500/30 bg-blue-950/40 text-blue-400">
            <svg class="h-8 w-8 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>

          <div class="space-y-2">
            <h3 class="text-lg font-bold text-white uppercase tracking-wider">Processing Match Analytics</h3>
            <p class="text-sm text-slate-400">{{ match.progress_message || 'Running tracking & classification pipeline...' }}</p>
          </div>

          <div class="mx-auto max-w-md space-y-2">
            <div class="flex justify-between text-xs font-semibold text-slate-300">
              <span>Pipeline Progress</span>
              <span>{{ match.progress }}%</span>
            </div>
            <div class="h-3 w-full overflow-hidden rounded-full bg-slate-950 border border-slate-800">
              <div class="h-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-300" [style.width.%]="match.progress"></div>
            </div>
          </div>

          @if (match.status === 'uploaded') {
            <button
              type="button"
              (click)="retryProcessing()"
              class="mt-4 rounded-xl bg-blue-600 px-6 py-2.5 text-xs font-semibold text-white shadow-lg hover:bg-blue-500 transition">
              Start Processing
            </button>
          }
        </div>
      }

      <!-- Failed Job Card with Retry Button -->
      @if (match && match.status === 'failed') {
        <div class="rounded-2xl border border-rose-500/30 bg-rose-950/30 p-8 shadow-xl space-y-6 text-center">
          <div class="inline-flex h-16 w-16 items-center justify-center rounded-2xl border border-rose-500/40 bg-rose-900/40 text-rose-400">
            <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>

          <div class="space-y-2 max-w-xl mx-auto">
            <h3 class="text-lg font-bold text-rose-300">Pipeline Execution Failed</h3>
            <p class="text-xs font-mono text-rose-400/90 rounded-xl bg-rose-950/60 p-4 border border-rose-900/60 text-left overflow-x-auto">
              {{ match.error_message || 'An unexpected error occurred during processing.' }}
            </p>
          </div>

          <button
            type="button"
            (click)="retryProcessing()"
            class="inline-flex items-center gap-2 rounded-xl bg-rose-600 px-6 py-3 text-xs font-bold text-white shadow-lg shadow-rose-600/30 hover:bg-rose-500 transition">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Retry Pipeline Job
          </button>
        </div>
      }

      <!-- Completed Dashboard View (3 Tabs) -->
      @if (results) {
        <!-- Tabs & Team Customization Bar -->
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <!-- Tab Navigation -->
          <div class="flex gap-2 rounded-xl border border-slate-800 bg-slate-900 p-1.5">
            <button
              type="button"
              (click)="activeTab = 'heatmaps'"
              class="rounded-lg px-4 py-2 text-xs font-semibold transition"
              [ngClass]="activeTab === 'heatmaps' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-white'">
              Heatmaps
            </button>
            <button
              type="button"
              (click)="activeTab = 'stats'"
              class="rounded-lg px-4 py-2 text-xs font-semibold transition"
              [ngClass]="activeTab === 'stats' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-white'">
              Player Stats
            </button>
            <button
              type="button"
              (click)="activeTab = 'possession'"
              class="rounded-lg px-4 py-2 text-xs font-semibold transition"
              [ngClass]="activeTab === 'possession' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-white'">
              Possession
            </button>
          </div>

          <!-- Team Labels Swap/Rename Bar -->
          <div class="flex items-center gap-3 text-xs">
            <button
              type="button"
              (click)="swapTeamColors()"
              class="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 font-medium text-slate-300 hover:bg-slate-700 transition">
              Swap Colors
            </button>
            <div class="flex items-center gap-1.5">
              <span class="h-3 w-3 rounded-full bg-blue-500"></span>
              <input
                type="text"
                [(ngModel)]="teamAName"
                class="w-24 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500">
            </div>
            <div class="flex items-center gap-1.5">
              <span class="h-3 w-3 rounded-full bg-rose-500"></span>
              <input
                type="text"
                [(ngModel)]="teamBName"
                class="w-24 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white focus:outline-none focus:ring-1 focus:ring-rose-500">
            </div>
          </div>
        </div>

        <!-- Tab 1: Heatmaps -->
        @if (activeTab === 'heatmaps') {
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  (click)="heatmapViewMode = 'A'; selectedTrackId = null"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold border"
                  [ngClass]="heatmapViewMode === 'A' ? 'bg-blue-950 text-blue-400 border-blue-500/40' : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'">
                  {{ teamAName }} Team Heatmap
                </button>
                <button
                  type="button"
                  (click)="heatmapViewMode = 'B'; selectedTrackId = null"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold border"
                  [ngClass]="heatmapViewMode === 'B' ? 'bg-rose-950 text-rose-400 border-rose-500/40' : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'">
                  {{ teamBName }} Team Heatmap
                </button>
              </div>

              <!-- Track Selector Dropdown -->
              <div class="flex items-center gap-2">
                <label class="text-xs font-medium text-slate-400">Individual Track:</label>
                <select
                  [ngModel]="selectedTrackId"
                  (ngModelChange)="onTrackSelected($event)"
                  class="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500">
                  <option [value]="null">Select Track...</option>
                  @for (t of eligibleTracks; track t.track_id) {
                    <option [value]="t.track_id">
                      Track #{{ t.track_id }} ({{ getTeamLabel(t.team) }}, {{ t.duration_s.toFixed(1) }}s)
                    </option>
                  }
                </select>
              </div>
            </div>

            <!-- Pitch Heatmap Plotly Display -->
            <app-pitch-heatmap
              [heatmapData]="activeHeatmapGrid"
              [title]="activeHeatmapTitle"
              [colorscale]="activeColorscale">
            </app-pitch-heatmap>
          </div>
        }

        <!-- Tab 2: Stats Table -->
        @if (activeTab === 'stats') {
          <div class="space-y-6">
            <!-- Filter Controls -->
            <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
              <!-- Minimum Duration Slider -->
              <div class="flex items-center gap-4 w-full sm:w-auto">
                <label class="text-xs font-medium text-slate-300 whitespace-nowrap">
                  Min Track Duration: <strong class="text-blue-400">{{ minDurationSlider }}s</strong>
                </label>
                <input
                  type="range"
                  min="0"
                  max="120"
                  step="1"
                  [(ngModel)]="minDurationSlider"
                  class="h-2 w-48 accent-blue-500">
              </div>

              <!-- Team Filter Buttons -->
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  (click)="teamFilter = 'all'"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold border"
                  [ngClass]="teamFilter === 'all' ? 'bg-blue-600 text-white border-blue-500' : 'bg-slate-800 text-slate-400 border-slate-700'">
                  All Teams
                </button>
                <button
                  type="button"
                  (click)="teamFilter = 'A'"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold border"
                  [ngClass]="teamFilter === 'A' ? 'bg-blue-950 text-blue-400 border-blue-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'">
                  {{ teamAName }}
                </button>
                <button
                  type="button"
                  (click)="teamFilter = 'B'"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold border"
                  [ngClass]="teamFilter === 'B' ? 'bg-rose-950 text-rose-400 border-rose-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'">
                  {{ teamBName }}
                </button>
              </div>
            </div>

            <!-- Sortable Tracks Table -->
            <div class="overflow-hidden rounded-xl border border-slate-800 bg-slate-900 shadow-xl">
              <table class="w-full text-left text-sm text-slate-300">
                <thead class="bg-slate-950 text-xs uppercase text-slate-400 border-b border-slate-800">
                  <tr>
                    <th scope="col" class="px-6 py-3 cursor-pointer select-none" (click)="sort('track_id')">Track Label</th>
                    <th scope="col" class="px-6 py-3 cursor-pointer select-none" (click)="sort('team')">Team</th>
                    <th scope="col" class="px-6 py-3">Role</th>
                    <th scope="col" class="px-6 py-3 cursor-pointer select-none" (click)="sort('duration_s')">Duration (s)</th>
                    <th scope="col" class="px-6 py-3 cursor-pointer select-none" (click)="sort('distance_m')">Distance</th>
                    <th scope="col" class="px-6 py-3">Avg Position (x, y)</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/60">
                  @for (t of filteredTracks; track t.track_id) {
                    <tr class="hover:bg-slate-800/40 transition">
                      <td class="px-6 py-3 font-semibold text-white">Track #{{ t.track_id }}</td>
                      <td class="px-6 py-3">
                        <span
                          class="inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold"
                          [ngClass]="{
                            'bg-blue-950 text-blue-400 border border-blue-500/30': t.team === 'A',
                            'bg-rose-950 text-rose-400 border border-rose-500/30': t.team === 'B',
                            'bg-slate-800 text-slate-400': !t.team
                          }">
                          {{ getTeamLabel(t.team) }}
                        </span>
                      </td>
                      <td class="px-6 py-3 text-xs capitalize text-slate-400">{{ t.role }} ({{ t.detector_hint }})</td>
                      <td class="px-6 py-3 text-xs font-mono text-slate-300">{{ t.duration_s.toFixed(1) }}s</td>
                      <td class="px-6 py-3 text-xs font-mono text-slate-200">
                        {{ results.meta.calibration === 'naive' ? '≈ ' : '' }}{{ t.distance_m.toFixed(1) }} m
                      </td>
                      <td class="px-6 py-3 text-xs font-mono text-slate-400">
                        ({{ t.avg_pos_m[0].toFixed(1) }}, {{ t.avg_pos_m[1].toFixed(1) }})
                      </td>
                    </tr>
                  }
                </tbody>

                <!-- Totals Row -->
                <tfoot class="bg-slate-950 font-bold text-xs text-slate-200 border-t border-slate-800">
                  <tr>
                    <td class="px-6 py-3">Totals ({{ filteredTracks.length }} tracks)</td>
                    <td class="px-6 py-3">-</td>
                    <td class="px-6 py-3">-</td>
                    <td class="px-6 py-3 font-mono">{{ totalFilteredDuration.toFixed(1) }}s</td>
                    <td class="px-6 py-3 font-mono text-blue-400">
                      {{ results.meta.calibration === 'naive' ? '≈ ' : '' }}{{ totalFilteredDistance.toFixed(1) }} m
                    </td>
                    <td class="px-6 py-3">-</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        }

        <!-- Tab 3: Possession Timeline -->
        @if (activeTab === 'possession') {
          <app-possession-timeline
            [possessionData]="results.possession"
            [totalDuration]="results.meta.duration_s"
            [teamAName]="teamAName"
            [teamBName]="teamBName">
          </app-possession-timeline>
        }
      }
    </div>
  `
})
export class MatchDashboardComponent implements OnInit, OnDestroy {
  public api = inject(ApiService);
  private ws = inject(WebsocketService);
  private route = inject(ActivatedRoute);

  match: Match | null = null;
  results: MatchResults | null = null;
  activeTab: 'heatmaps' | 'stats' | 'possession' = 'heatmaps';

  teamAName = 'Team A';
  teamBName = 'Team B';

  // Heatmap tab state
  heatmapViewMode: 'A' | 'B' | 'track' = 'A';
  selectedTrackId: number | null = null;

  // Stats tab state
  minDurationSlider = 10;
  teamFilter: 'all' | 'A' | 'B' = 'all';
  sortColumn: keyof TrackItem = 'distance_m';
  sortAsc = false;

  private wsSub?: Subscription;

  ngOnInit(): void {
    const matchId = this.route.snapshot.paramMap.get('id');
    if (matchId) {
      this.loadMatch(matchId);
    }
  }

  ngOnDestroy(): void {
    this.wsSub?.unsubscribe();
  }

  loadMatch(matchId: string): void {
    this.api.getMatch(matchId).subscribe({
      next: (m) => {
        this.match = m;
        if (m.status === 'completed') {
          this.loadResults(matchId);
        } else if (m.status !== 'failed') {
          this.subscribeProgress(matchId);
        }
      },
      error: (err) => console.error('Error loading match', err)
    });
  }

  subscribeProgress(matchId: string): void {
    this.wsSub = this.ws.connectMatchProgress(matchId).subscribe({
      next: (msg) => {
        if (this.match) {
          this.match.status = msg.status as any;
          this.match.progress = msg.progress;
          this.match.progress_message = msg.message;
          this.match.error_message = msg.error;
        }
        if (msg.status === 'completed') {
          this.loadResults(matchId);
        }
      }
    });
  }

  loadResults(matchId: string): void {
    this.api.getMatchResults(matchId).subscribe({
      next: (r) => this.results = r,
      error: (err) => console.error('Error loading results', err)
    });
  }

  retryProcessing(): void {
    if (!this.match) return;
    const matchId = this.match.id;
    this.api.processMatch(matchId).subscribe({
      next: (m) => {
        this.match = m;
        this.results = null;
        this.subscribeProgress(matchId);
      },
      error: (err) => alert(err.error?.detail || 'Failed to retry job')
    });
  }

  swapTeamColors(): void {
    const tmp = this.teamAName;
    this.teamAName = this.teamBName;
    this.teamBName = tmp;
  }

  getTeamLabel(team?: 'A' | 'B' | null): string {
    if (team === 'A') return this.teamAName;
    if (team === 'B') return this.teamBName;
    return 'Other';
  }

  // --- Heatmap Computed Getters ---

  get eligibleTracks(): TrackItem[] {
    if (!this.results) return [];
    return this.results.tracks.filter(t => t.duration_s >= this.minDurationSlider);
  }

  onTrackSelected(rawVal: any): void {
    const val = rawVal ? Number(rawVal) : null;
    this.selectedTrackId = val;
    if (val !== null) {
      this.heatmapViewMode = 'track';
    }
  }

  get activeHeatmapGrid(): number[][] {
    if (!this.results) return [];
    if (this.selectedTrackId !== null && this.results.heatmaps.tracks[String(this.selectedTrackId)]) {
      return this.results.heatmaps.tracks[String(this.selectedTrackId)];
    }
    if (this.heatmapViewMode === 'B') {
      return this.results.heatmaps.teams.B || [];
    }
    return this.results.heatmaps.teams.A || [];
  }

  get activeHeatmapTitle(): string {
    if (this.selectedTrackId !== null) {
      return `Heatmap for Track #${this.selectedTrackId}`;
    }
    return this.heatmapViewMode === 'B' ? `${this.teamBName} Team Heatmap` : `${this.teamAName} Team Heatmap`;
  }

  get activeColorscale(): string {
    if (this.selectedTrackId !== null) return 'Hot';
    return this.heatmapViewMode === 'B' ? 'Reds' : 'Blues';
  }

  // --- Stats Table Computed Getters ---

  get filteredTracks(): TrackItem[] {
    if (!this.results) return [];
    let list = this.results.tracks.filter(t => t.duration_s >= this.minDurationSlider);

    if (this.teamFilter === 'A') {
      list = list.filter(t => t.team === 'A');
    } else if (this.teamFilter === 'B') {
      list = list.filter(t => t.team === 'B');
    }

    return list.sort((a, b) => {
      const valA = a[this.sortColumn] ?? 0;
      const valB = b[this.sortColumn] ?? 0;
      if (valA < valB) return this.sortAsc ? -1 : 1;
      if (valA > valB) return this.sortAsc ? 1 : -1;
      return 0;
    });
  }

  get totalFilteredDistance(): number {
    return this.filteredTracks.reduce((acc, t) => acc + t.distance_m, 0);
  }

  get totalFilteredDuration(): number {
    return this.filteredTracks.reduce((acc, t) => acc + t.duration_s, 0);
  }

  sort(col: keyof TrackItem): void {
    if (this.sortColumn === col) {
      this.sortAsc = !this.sortAsc;
    } else {
      this.sortColumn = col;
      this.sortAsc = false;
    }
  }
}
