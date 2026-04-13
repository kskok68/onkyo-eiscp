import Fuse from 'fuse.js';
import { resolve } from 'aurelia';
import { commandIsAvailable, setsForModel } from '../parser/modelsets';
import { ICommandDatabase, ISelectionState } from '../services/tokens';
import type { CommandDef } from '../types';

export class CommandList {
  readonly db = resolve(ICommandDatabase);
  readonly state = resolve(ISelectionState);

  private readonly fuse = new Fuse<CommandDef>(this.db.commands, {
    ignoreLocation: true,
    threshold: 0.35,
    keys: [
      { name: 'code', weight: 0.4 },
      { name: 'name', weight: 0.4 },
      { name: 'aliases', weight: 0.15 },
      { name: 'description', weight: 0.05 },
    ],
  });

  get filteredCommands(): CommandDef[] {
    const allowed = setsForModel(this.state.model, this.db.modelsets);
    const search = this.state.search.trim();
    const searchResults = search
      ? this.fuse.search(search).map((result) => result.item)
      : this.db.commands;

    return searchResults.filter(
      (cmd) => cmd.zone === this.state.zone && commandIsAvailable(cmd, allowed, this.db.modelsets)
    );
  }

  get activeCode(): string | null {
    const filtered = this.filteredCommands;
    const current = this.state.selectedCode;

    if (current && filtered.some((cmd) => cmd.code === current)) {
      return current;
    }

    return filtered[0]?.code ?? null;
  }

  selectCommand(command: CommandDef): void {
    this.state.selectedCode = command.code;
  }

  isActive(command: CommandDef): boolean {
    return command.code === this.activeCode;
  }
}
