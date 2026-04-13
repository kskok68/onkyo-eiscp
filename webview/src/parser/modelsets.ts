import type { CommandDef, ModelSetName, ValueDef } from '../types';

export function setsForModel(
  model: string | null,
  modelsets: Record<string, string[]>
): Set<ModelSetName> {
  if (!model) {
    return new Set(Object.keys(modelsets));
  }

  const out = new Set<ModelSetName>();
  for (const [setName, models] of Object.entries(modelsets)) {
    if (models.includes(model)) {
      out.add(setName);
    }
  }

  return out;
}

export function valueIsAvailable(
  value: ValueDef,
  allowed: Set<ModelSetName>,
  modelsets: Record<string, string[]>
): boolean {
  if (value.models.length === 0) {
    return true;
  }

  const knownModels = value.models.filter((setName) => setName in modelsets);
  if (knownModels.length === 0) {
    return true;
  }

  return knownModels.some((setName) => allowed.has(setName));
}

export function commandIsAvailable(
  command: CommandDef,
  allowed: Set<ModelSetName>,
  modelsets: Record<string, string[]>
): boolean {
  return command.values.some((value) => valueIsAvailable(value, allowed, modelsets));
}
