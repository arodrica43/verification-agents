import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Technology, UseCase } from '../../types';

@Component({
  selector: 'app-c2t',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './c2t.component.html',
  styleUrls: ['./c2t.component.css']
})
export class C2TComponent {
  @Input() techs: Technology[] = [];
  @Input() cases: UseCase[] = [];
  @Input() set seed(v:number){ this.mix(v); }

  picks = signal<Record<string, Set<string>>>({}); // caseId -> set of techIds
  results = signal<{avgF1:number, detail: Record<string, number> }|null>(null);

  mix(_seed:number){ this.picks.set({}); this.results.set(null); }

  toggle(caseId:string, techId:string){
    const map = { ...this.picks() };
    const s = new Set(map[caseId] || []);
    s.has(techId) ? s.delete(techId) : s.add(techId);
    map[caseId] = s; this.picks.set(map);
  }

  isSel(caseId:string, techId:string){ return this.picks()[caseId]?.has(techId); }

  submit(){
    let sumF1 = 0; const detail: Record<string, number> = {};
    for (const c of this.cases){
      const picked = this.picks()[c.id] || new Set<string>();
      const correct = new Set(this.techs.filter(t=>t.bestFor.includes(c.id)).map(t=>t.id));
      const tp = [...picked].filter(id=>correct.has(id)).length;
      const fp = [...picked].filter(id=>!correct.has(id)).length;
      const fn = [...correct].filter(id=>!picked.has(id)).length;
      const precision = tp+fp===0?0:tp/(tp+fp);
      const recall = tp+fn===0?0:tp/(tp+fn);
      const f1 = precision+recall===0?0:(2*precision*recall)/(precision+recall);
      detail[c.id] = f1; sumF1 += f1;
    }
    this.results.set({ avgF1: sumF1 / this.cases.length, detail });
  }

  reset(){ this.mix(0); }
}