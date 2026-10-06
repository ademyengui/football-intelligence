import { Layout, Shape } from 'plotly.js-dist-min';

export const PITCH_CONFIG = {
  width_m: 105,
  height_m: 68,
  bg_color: '#0f172a',
  pitch_color: '#020617',
  line_color: '#475569',
  line_width: 2,
  team_a_color: '#3b82f6',
  team_b_color: '#ef4444',
  unknown_color: '#64748b'
};

/**
 * Generates Plotly shapes for standard 105m x 68m football pitch markings.
 */
export function getPitchShapes(): Partial<Shape>[] {
  const lc = PITCH_CONFIG.line_color;
  const lw = PITCH_CONFIG.line_width;

  return [
    // Pitch outer boundary
    {
      type: 'rect',
      x0: 0,
      y0: 0,
      x1: 105,
      y1: 68,
      line: { color: lc, width: lw }
    },
    // Halfway line
    {
      type: 'line',
      x0: 52.5,
      y0: 0,
      x1: 52.5,
      y1: 68,
      line: { color: lc, width: lw }
    },
    // Centre circle (radius 9.15m at 52.5, 34)
    {
      type: 'circle',
      x0: 52.5 - 9.15,
      y0: 34 - 9.15,
      x1: 52.5 + 9.15,
      y1: 34 + 9.15,
      line: { color: lc, width: lw }
    },
    // Centre spot
    {
      type: 'circle',
      x0: 52.5 - 0.3,
      y0: 34 - 0.3,
      x1: 52.5 + 0.3,
      y1: 34 + 0.3,
      fillcolor: lc,
      line: { color: lc, width: 1 }
    },
    // Left Penalty Box (16.5m from endline, 40.32m wide centered at y=34)
    {
      type: 'rect',
      x0: 0,
      y0: 34 - 20.16,
      x1: 16.5,
      y1: 34 + 20.16,
      line: { color: lc, width: lw }
    },
    // Right Penalty Box
    {
      type: 'rect',
      x0: 105 - 16.5,
      y0: 34 - 20.16,
      x1: 105,
      y1: 34 + 20.16,
      line: { color: lc, width: lw }
    },
    // Left Goal Box (5.5m from endline, 18.32m wide centered at y=34)
    {
      type: 'rect',
      x0: 0,
      y0: 34 - 9.16,
      x1: 5.5,
      y1: 34 + 9.16,
      line: { color: lc, width: lw }
    },
    // Right Goal Box
    {
      type: 'rect',
      x0: 105 - 5.5,
      y0: 34 - 9.16,
      x1: 105,
      y1: 34 + 9.16,
      line: { color: lc, width: lw }
    }
  ];
}

export function getDefaultLayout(title: string = ''): Partial<Layout> {
  return {
    title: { text: title, font: { color: '#f8fafc', size: 16 } },
    paper_bgcolor: PITCH_CONFIG.bg_color,
    plot_bgcolor: PITCH_CONFIG.pitch_color,
    font: { color: '#94a3b8' },
    xaxis: {
      range: [0, 105],
      showgrid: false,
      zeroline: false,
      title: { text: 'Length (metres)' },
      scaleanchor: 'y',
      scaleratio: 1
    },
    yaxis: {
      range: [68, 0], // Top-left origin: 0 at top, 68 at bottom
      showgrid: false,
      zeroline: false,
      title: { text: 'Width (metres)' }
    },
    shapes: getPitchShapes(),
    margin: { l: 40, r: 40, t: 40, b: 40 },
    autosize: true
  };
}
