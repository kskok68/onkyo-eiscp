import { DI } from 'aurelia';
import type { CommandDatabase } from '../types';

export interface SelectionStateApi {
  model: string | null;
  zone: string;
  search: string;
  selectedCode: string | null;
  ensureDefaults(allModels: string[], zones: string[]): void;
}

export const ICommandDatabase = DI.createInterface<CommandDatabase>('ICommandDatabase');
export const ISelectionState = DI.createInterface<SelectionStateApi>('ISelectionState');
