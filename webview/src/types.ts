export type ModelSetName = string;

export type ValueKey =
  | { kind: 'literal'; value: string }
  | { kind: 'range'; start: number; end: number }
  | { kind: 'pattern'; template: string };

export interface ValueDef {
  key: ValueKey;
  names: string[];
  description: string;
  models: ModelSetName[];
}

export interface CommandDef {
  zone: string;
  code: string;
  name: string;
  description: string;
  aliases: string[];
  values: ValueDef[];
}

export interface CommandDatabase {
  zones: string[];
  commands: CommandDef[];
  modelsets: Record<ModelSetName, string[]>;
  allModels: string[];
}
