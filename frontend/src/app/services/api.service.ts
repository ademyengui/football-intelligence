import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType, HttpRequest } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { Match, MatchResults, HealthResponse } from '../models/match.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiBaseUrl;

  assetUrl(path: string | null | undefined): string {
    if (!path) return '';
    return path.startsWith('http') ? path : `${this.baseUrl}${path}`;
  }

  getHealth(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.baseUrl}/health`);
  }

  listMatches(): Observable<Match[]> {
    return this.http.get<Match[]>(`${this.baseUrl}/matches`);
  }

  getMatch(id: string): Observable<Match> {
    return this.http.get<Match>(`${this.baseUrl}/matches/${id}`);
  }

  uploadMatch(file: File): Observable<{ progress: number; match?: Match }> {
    const formData = new FormData();
    formData.append('file', file);

    const req = new HttpRequest('POST', `${this.baseUrl}/matches`, formData, {
      reportProgress: true
    });

    return this.http.request<Match>(req).pipe(
      map((event: HttpEvent<Match>) => {
        if (event.type === HttpEventType.UploadProgress) {
          const total = event.total || file.size || 1;
          const progress = Math.round((100 * event.loaded) / total);
          return { progress };
        } else if (event.type === HttpEventType.Response) {
          return { progress: 100, match: event.body || undefined };
        }
        return { progress: 0 };
      })
    );
  }

  processMatch(id: string): Observable<Match> {
    return this.http.post<Match>(`${this.baseUrl}/matches/${id}/process`, {});
  }

  getMatchResults(id: string): Observable<MatchResults> {
    return this.http.get<MatchResults>(`${this.baseUrl}/matches/${id}/results`);
  }

  deleteMatch(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/matches/${id}`);
  }

  getExportTracksUrl(id: string): string {
    return `${this.baseUrl}/matches/${id}/export.csv?kind=tracks`;
  }

  getExportPossessionUrl(id: string): string {
    return `${this.baseUrl}/matches/${id}/export.csv?kind=possession`;
  }
}
