import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { GameData } from '../../types';

@Component({
  selector: 'app-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.css']
})
export class EditorComponent {
  @Input() data!: GameData;
  @Output() save = new EventEmitter<GameData>();
  @Output() close = new EventEmitter<void>();
  text = '';
  ngOnInit(){ this.text = JSON.stringify(this.data, null, 2); }
  onSave(){ try{ this.save.emit(JSON.parse(this.text)); this.close.emit(); } catch(e:any){ alert('JSON error: '+e.message); } }
}