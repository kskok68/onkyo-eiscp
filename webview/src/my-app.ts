import { resolve } from 'aurelia';
import './styles.css';
import { ICommandDatabase, ISelectionState } from './services/tokens';

export class MyApp {
  readonly db = resolve(ICommandDatabase);
  readonly state = resolve(ISelectionState);

  binding(): void {
    this.state.ensureDefaults(this.db.allModels, this.db.zones);
  }
}
