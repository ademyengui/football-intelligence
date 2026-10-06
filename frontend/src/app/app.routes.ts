import { Routes } from '@angular/router';
import { UploadComponent } from './components/upload/upload.component';
import { MatchesListComponent } from './components/matches-list/matches-list.component';
import { MatchDashboardComponent } from './components/match-dashboard/match-dashboard.component';

export const routes: Routes = [
  { path: '', component: UploadComponent },
  { path: 'matches', component: MatchesListComponent },
  { path: 'matches/:id', component: MatchDashboardComponent },
  { path: '**', redirectTo: '' }
];
