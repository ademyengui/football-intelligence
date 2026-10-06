import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PossessionData } from '../models/match.model';

@Component({
  selector: 'app-possession-timeline',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-6 rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-xl">
      <!-- Summary Percentage Cards -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <!-- Team A -->
        <div class="flex flex-col items-center justify-center rounded-xl border border-blue-500/30 bg-blue-950/40 p-4">
          <span class="text-xs font-semibold uppercase tracking-wider text-blue-400">{{ teamAName }}</span>
          <span class="mt-1 text-3xl font-extrabold text-blue-400">{{ possessionData?.summary?.A_pct ?? 50 }}%</span>
          <span class="text-xs text-slate-400">Possession</span>
        </div>

        <!-- Team B -->
        <div class="flex flex-col items-center justify-center rounded-xl border border-rose-500/30 bg-rose-950/40 p-4">
          <span class="text-xs font-semibold uppercase tracking-wider text-rose-400">{{ teamBName }}</span>
          <span class="mt-1 text-3xl font-extrabold text-rose-400">{{ possessionData?.summary?.B_pct ?? 50 }}%</span>
          <span class="text-xs text-slate-400">Possession</span>
        </div>

        <!-- Unknown -->
        <div class="flex flex-col items-center justify-center rounded-xl border border-slate-600/30 bg-slate-800/40 p-4">
          <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Uncontested / Loose</span>
          <span class="mt-1 text-3xl font-extrabold text-slate-300">{{ possessionData?.summary?.unknown_pct ?? 0 }}%</span>
          <span class="text-xs text-slate-400">Total Match Share</span>
        </div>
      </div>

      <!-- Horizontal Possession Timeline Bar -->
      <div>
        <div class="mb-2 flex items-center justify-between text-xs font-medium text-slate-400">
          <span>0s</span>
          <span>Match Timeline (Color Bands)</span>
          <span>{{ totalDuration }}s</span>
        </div>

        <div class="relative h-10 w-full overflow-hidden rounded-lg bg-slate-950 border border-slate-800 flex">
          @for (inv of possessionData?.intervals ?? []; track $index) {
            <div
              class="h-full transition-all duration-200 relative group"
              [style.width.%]="getIntervalWidthPercent(inv.start_s, inv.end_s)"
              [ngClass]="{
                'bg-blue-600 hover:bg-blue-500': inv.state === 'A',
                'bg-rose-600 hover:bg-rose-500': inv.state === 'B',
                'bg-slate-700 hover:bg-slate-600': inv.state === 'unknown'
              }"
              [title]="getTooltip(inv)">
            </div>
          }
        </div>

        <!-- Timeline legend -->
        <div class="mt-4 flex items-center justify-center gap-6 text-xs text-slate-300">
          <div class="flex items-center gap-2">
            <span class="h-3 w-3 rounded-full bg-blue-500"></span>
            <span>{{ teamAName }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="h-3 w-3 rounded-full bg-rose-500"></span>
            <span>{{ teamBName }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="h-3 w-3 rounded-full bg-slate-600"></span>
            <span>Loose / Unknown</span>
          </div>
        </div>
      </div>
    </div>
  `
})
export class PossessionTimelineComponent {
  @Input() possessionData: PossessionData | null = null;
  @Input() totalDuration: number = 120;
  @Input() teamAName: string = 'Team A';
  @Input() teamBName: string = 'Team B';

  getIntervalWidthPercent(start: number, end: number): number {
    const dur = Math.max(0.1, end - start);
    const total = Math.max(1, this.totalDuration);
    return Math.min(100, (dur / total) * 100);
  }

  getTooltip(inv: any): string {
    const teamName = inv.state === 'A' ? this.teamAName : (inv.state === 'B' ? this.teamBName : 'Loose ball');
    return `${inv.start_s.toFixed(1)}s - ${inv.end_s.toFixed(1)}s (${teamName})`;
  }
}
