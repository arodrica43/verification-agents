import { Component, computed, effect, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DragDropModule } from '@angular/cdk/drag-drop';
import { DEFAULT_DATA } from './data';
import { GameData, Technology, UseCase } from './types';
import { StorageService } from './storage.service';
import { ToolbarComponent } from './components/toolbar/toolbar.component';
import { EditorComponent } from './components/editor/editor.component';
import { AnswerKeyComponent } from './components/answer-key/answer-key.component';
import { T2CComponent } from './components/t2c/t2c.component';
import { C2TComponent } from './components/c2t/c2t.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, DragDropModule, ToolbarComponent, EditorComponent, AnswerKeyComponent, T2CComponent, C2TComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'Big Data Match Game';

  data = signal<GameData>(DEFAULT_DATA);
  mode = signal<'t2c'|'c2t'>('t2c');
  difficulty = signal<'all'|'easy'|'medium'|'hard'>('all');
  showEditor = signal(false);
  seed = signal(0);
  timerOn = signal(false);
  seconds = signal(0);
  interval?: any;

  constructor(private store: StorageService){
    const saved = this.store.load();
    if (saved) this.data.set(saved);
    effect(() => this.store.save(this.data()));
  }

  startTimer(){
    if (this.interval) return;
    this.timerOn.set(true);
    this.interval = setInterval(()=>this.seconds.update(v=>v+1), 1000);
  }
  stopTimer(){ if (this.interval){ clearInterval(this.interval); this.interval = undefined; } this.timerOn.set(false); }
  resetTimer(){ this.stopTimer(); this.seconds.set(0); }

  toggleEditor(){ this.showEditor.update(v=>!v); }
  setMode(m:'t2c'|'c2t'){ this.mode.set(m); this.resetTimer(); }
  setDifficulty(d:'all'|'easy'|'medium'|'hard'){ this.difficulty.set(d); }
  shuffle(){ this.seed.update(v=>v+1); this.resetTimer(); }

  filteredTechs = computed<Technology[]>(() => {
    const d = this.difficulty();
    if (d==='all') return this.data().technologies.slice();
    const set = new Set(this.data().useCases.filter(u=>u.difficulty===d).map(u=>u.id));
    return this.data().technologies.filter(t=>t.bestFor.some(id=>set.has(id)));
  });

  filteredCases = computed<UseCase[]>(() => {
    const d = this.difficulty();
    return this.data().useCases.filter(u=> d==='all' ? true : u.difficulty===d);
  });

  replaceData(newData: GameData){ this.data.set(newData); this.resetTimer(); }
  exportData(){ const blob = new Blob([JSON.stringify(this.data(), null, 2)], {type:'application/json'}); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'bigdata-match-data.json'; a.click(); URL.revokeObjectURL(url); }
  importData(file: File){ const r = new FileReader(); r.onload = ()=>{ try{ this.replaceData(JSON.parse(String(r.result))); }catch{ alert('Invalid JSON'); } }; r.readAsText(file); }
  resetSample(){ this.replaceData(DEFAULT_DATA); this.store.clear(); }
}