import { Component, ElementRef, Input, OnChanges, SimpleChanges, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import Plotly from 'plotly.js-dist-min';
import { getDefaultLayout } from './chart-config';

@Component({
  selector: 'app-pitch-heatmap',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative w-full overflow-hidden rounded-xl border border-slate-700 bg-slate-900 p-2 shadow-xl">
      <div #plotlyContainer class="h-[450px] w-full"></div>
    </div>
  `
})
export class PitchHeatmapComponent implements AfterViewInit, OnChanges {
  @ViewChild('plotlyContainer') container!: ElementRef<HTMLDivElement>;

  @Input() heatmapData: number[][] = []; // 68 rows of 105 cols
  @Input() title: string = '';
  @Input() colorscale: string = 'Viridis'; // 'Viridis' | 'Blues' | 'Reds' | 'Hot'

  private isInitialized = false;

  ngAfterViewInit(): void {
    this.isInitialized = true;
    this.renderChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (this.isInitialized && (changes['heatmapData'] || changes['colorscale'] || changes['title'])) {
      this.renderChart();
    }
  }

  private renderChart(): void {
    if (!this.container || !this.heatmapData || this.heatmapData.length === 0) {
      return;
    }

    const layout = getDefaultLayout(this.title);

    // Build Plotly Heatmap trace
    const data: Plotly.Data[] = [
      {
        z: this.heatmapData,
        x: Array.from({ length: 105 }, (_, i) => i + 0.5),
        y: Array.from({ length: 68 }, (_, i) => i + 0.5),
        type: 'heatmap',
        colorscale: this.colorscale,
        showscale: true,
        hoverongaps: false,
        hovertemplate: 'x: %{x:.1f} m<br>y: %{y:.1f} m<br>Density: %{z:.3f}<extra></extra>',
        colorbar: {
          title: { text: 'Density', font: { color: '#94a3b8' } },
          tickfont: { color: '#94a3b8' },
          len: 0.8
        }
      }
    ];

    const config: Partial<Plotly.Config> = {
      responsive: true,
      displayModeBar: false
    };

    Plotly.react(this.container.nativeElement, data, layout, config);
  }
}
