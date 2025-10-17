import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Technology, UseCase } from '../../types';

@Component({
  selector: 'app-answer-key',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './answer-key.component.html',
  styleUrls: ['./answer-key.component.css']
})
export class AnswerKeyComponent {
  @Input() techs: Technology[] = [];
  @Input() cases: UseCase[] = [];
}