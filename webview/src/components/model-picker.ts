import Fuse from 'fuse.js';
import { observable, resolve } from 'aurelia';
import { ICommandDatabase, ISelectionState } from '../services/tokens';

export class ModelPicker {
  readonly db = resolve(ICommandDatabase);
  readonly state = resolve(ISelectionState);

  @observable query = '';
  showSuggestions = false;

  private readonly fuse: Fuse<string>;

  constructor() {
    this.fuse = new Fuse(this.db.allModels, {
      threshold: 0.35,
      ignoreLocation: true,
    });
    this.query = this.state.model ?? '';
  }

  binding(): void {
    this.query = this.state.model ?? this.db.allModels[0] ?? '';
    this.updateSuggestions();
  }

  queryChanged(): void {
    this.updateSuggestions();
  }

  suggestions: string[] = [];

  private updateSuggestions(): void {
    const q = this.query.trim();
    if (!q) {
      this.suggestions = this.db.allModels.slice(0, 25);
    } else {
      this.suggestions = this.fuse.search(q, { limit: 25 }).map((result) => result.item);
    }
  }

  chooseModel(model: string): void {
    this.state.model = model;
    this.query = model;
    this.showSuggestions = false;
  }

  applyQuery(): void {
    const normalized = this.query.trim().toLowerCase();
    if (!normalized) {
      return;
    }

    const exactMatch = this.db.allModels.find((model) => model.toLowerCase() === normalized);
    if (exactMatch) {
      this.chooseModel(exactMatch);
      return;
    }

    const bestMatch = this.suggestions[0];
    if (bestMatch) {
      this.chooseModel(bestMatch);
    }
  }

  useDefault(): void {
    if (this.db.allModels.length > 0) {
      this.chooseModel(this.db.allModels[0]);
    }
  }

  hideSuggestionsSoon(): void {
    window.setTimeout(() => {
      this.showSuggestions = false;
    }, 120);
  }
}
