import { Injectable, inject } from '@angular/core';
import { Observable, Subject, interval, switchMap, takeUntil, catchError, of } from 'rxjs';
import { environment } from '../../environments/environment';
import { ProgressMessage } from '../models/match.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class WebsocketService {
  private api = inject(ApiService);

  connectMatchProgress(matchId: string): Observable<ProgressMessage> {
    const subject = new Subject<ProgressMessage>();
    const wsUrl = `${environment.wsBaseUrl}/matches/${matchId}`;

    let socket: WebSocket | null = null;
    let fallbackActive = false;
    const stopPolling$ = new Subject<void>();

    const startPollingFallback = () => {
      if (fallbackActive) return;
      fallbackActive = true;
      console.log(`[WS] Fallback to HTTP polling for match ${matchId}`);

      interval(2000).pipe(
        takeUntil(stopPolling$),
        switchMap(() => this.api.getMatch(matchId).pipe(
          catchError(() => of(null))
        ))
      ).subscribe(match => {
        if (match) {
          const msg: ProgressMessage = {
            status: match.status,
            progress: match.progress,
            message: match.progress_message,
            error: match.error_message
          };
          subject.next(msg);
          if (match.status === 'completed' || match.status === 'failed') {
            stopPolling$.next();
            subject.complete();
          }
        }
      });
    };

    try {
      socket = new WebSocket(wsUrl);

      socket.onmessage = (event) => {
        try {
          const data: ProgressMessage = JSON.parse(event.data);
          subject.next(data);
          if (data.status === 'completed' || data.status === 'failed') {
            socket?.close();
            subject.complete();
          }
        } catch (e) {
          console.error('[WS] Parse error', e);
        }
      };

      socket.onerror = (err) => {
        console.warn('[WS] Socket error, triggering fallback', err);
        startPollingFallback();
      };

      socket.onclose = () => {
        if (!fallbackActive) {
          startPollingFallback();
        }
      };
    } catch (e) {
      console.warn('[WS] Connection failed, falling back to polling', e);
      startPollingFallback();
    }

    return subject.asObservable();
  }
}
