import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CdkDrag, CdkDropList, CdkDragDrop, DragDropModule, transferArrayItem } from '@angular/cdk/drag-drop';
import { Technology, UseCase } from '../../types';

function shuffle<T>(arr:T[], seed:number){ const a=arr.slice(); let s=seed+1; for (let i=a.length-1;i>0;i--){ s=(s*9301+49297)%233280; const j=Math.floor((s/233280)*(i+1)); [a[i],a[j]]=[a[j],a[i]]; } return a; }

@Component({
  selector: 'app-t2c',
  standalone: true,
  imports: [CommonModule, DragDropModule],
  templateUrl: './t2c.component.html',
  styleUrls: ['./t2c.component.css']
})
export class T2CComponent {
  @Input() techs: Technology[] = [];
  @Input() cases: UseCase[] = [];
  @Input() set seed(v:number){ this.mix(v); }

  source = signal<Technology[]>([]);
  targets = signal<Record<string, Technology[]>>({}); // caseId -> array (keep one)
  scored = signal<{score:number,total:number, details:{tech:Technology, picked?:string, correct:boolean}[]}|null>(null);

  mix(seed:number){
    this.source.set(shuffle(this.techs, seed));
    const map: Record<string, Technology[]> = {};
    this.cases.forEach(c => map[c.id] = []);
    this.targets.set(map);
    this.scored.set(null);
  }

  drop(event: CdkDragDrop<Technology[]>, caseId?: string){
    if (!event.container || !event.previousContainer) return;
    if (event.container === event.previousContainer) return;
    const prev = event.previousContainer.data;
    const curr = event.container.data;
    if (caseId){ curr.splice(0, curr.length); } // keep only one
    transferArrayItem(prev, curr, event.previousIndex, event.currentIndex);
  }

  submit(){
    const details = this.techs.map(t => {
      let chosen: string | undefined;
      for (const cid of Object.keys(this.targets())){
        if (this.targets()[cid].some(x=>x.id===t.id)) { chosen = cid; break; }
      }
      const correct = chosen ? t.bestFor.includes(chosen) : false;
      return { tech: t, picked: chosen, correct };
    });
    const score = details.filter(d=>d.correct).length;
    this.scored.set({ score, total: this.techs.length, details });
  }

  reset(){ this.mix(0); }
}