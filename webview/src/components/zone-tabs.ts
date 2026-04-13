import { resolve } from 'aurelia';
import { ICommandDatabase, ISelectionState } from '../services/tokens';

export class ZoneTabs {
  readonly db = resolve(ICommandDatabase);
  readonly state = resolve(ISelectionState);

  selectZone(zone: string): void {
    if (this.state.zone !== zone) {
      this.state.zone = zone;
      this.state.selectedCode = null;
    }
  }

  isActive(zone: string): boolean {
    return this.state.zone === zone;
  }
}
