import { resolve } from 'aurelia';
import { ISelectionState } from '../services/tokens';

export class SearchBar {
  readonly state = resolve(ISelectionState);

  clear(): void {
    this.state.search = '';
  }
}
