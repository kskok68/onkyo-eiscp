import { resolve } from 'aurelia';
import { commandIsAvailable, setsForModel, valueIsAvailable } from '../parser/modelsets';
import { ICommandDatabase, ISelectionState } from '../services/tokens';
import type { CommandDef, ValueDef } from '../types';

export class CommandDetail {
  readonly db = resolve(ICommandDatabase);
  readonly state = resolve(ISelectionState);

  get selectedCommand(): CommandDef | null {
    const allowed = setsForModel(this.state.model, this.db.modelsets);
    const candidates = this.db.commands.filter(
      (command) =>
        command.zone === this.state.zone &&
        commandIsAvailable(command, allowed, this.db.modelsets)
    );

    if (candidates.length === 0) {
      return null;
    }

    return candidates.find((command) => command.code === this.state.selectedCode) ?? candidates[0];
  }

  get availableValues(): ValueDef[] {
    const selected = this.selectedCommand;
    if (!selected) {
      return [];
    }

    const allowed = setsForModel(this.state.model, this.db.modelsets);
    return selected.values.filter((value) => valueIsAvailable(value, allowed, this.db.modelsets));
  }

  get aliasesText(): string {
    const selected = this.selectedCommand;
    if (!selected || selected.aliases.length === 0) {
      return '—';
    }

    return selected.aliases.join(', ');
  }
}
