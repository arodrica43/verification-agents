export type Difficulty = 'easy' | 'medium' | 'hard';

export interface UseCase {
  id: string;
  text: string;
  tags?: string[];
  difficulty?: Difficulty;
}

export interface Technology {
  id: string;
  name: string;
  type: string;
  vendor?: string;
  bestFor: string[]; // array of useCase IDs
  rationale: string;
  tags?: string[];
}

export interface GameData {
  technologies: Technology[];
  useCases: UseCase[];
}