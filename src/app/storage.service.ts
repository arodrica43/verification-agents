import { Injectable } from '@angular/core';
import { GameData } from './types';

const KEY = 'bd-match-angular-data-v1';

@Injectable({ providedIn: 'root' })
export class StorageService {
  load(): GameData | null {
    try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; }
  }
  save(data: GameData) { localStorage.setItem(KEY, JSON.stringify(data)); }
  clear(){ localStorage.removeItem(KEY); }
}