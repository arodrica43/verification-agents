import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-toolbar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './toolbar.component.html',
  styleUrls: ['./toolbar.component.css']
})
export class ToolbarComponent {
  @Input() mode: 't2c'|'c2t' = 't2c';
  @Input() difficulty: 'all'|'easy'|'medium'|'hard' = 'all';
  @Input() timerOn = false;
  @Input() seconds = 0;
  @Output() modeChange = new EventEmitter<'t2c'|'c2t'>();
  @Output() difficultyChange = new EventEmitter<'all'|'easy'|'medium'|'hard'>();
  @Output() shuffle = new EventEmitter<void>();
  @Output() startTimer = new EventEmitter<void>();
  @Output() stopTimer = new EventEmitter<void>();
  @Output() exportJson = new EventEmitter<void>();
  @Output() importJson = new EventEmitter<File>();
  @Output() resetSample = new EventEmitter<void>();
  @Output() openEditor = new EventEmitter<void>();

  onImport(e: Event){ const f = (e.target as HTMLInputElement).files?.[0]; if (f) this.importJson.emit(f); }
}