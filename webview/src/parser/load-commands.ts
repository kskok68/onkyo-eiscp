import { parse } from 'yaml';
import yamlText from '../../../eiscp-commands.yaml?raw';
import type { CommandDatabase, CommandDef, ValueDef, ValueKey } from '../types';

export function loadCommands(): CommandDatabase {
  const doc = parse(yamlText, { mapAsMap: true }) as unknown;

  const modelsets: Record<string, string[]> = {};
  const zoneNames: string[] = [];
  const commands: CommandDef[] = [];

  for (const [zoneKey, zoneVal] of getEntries(doc)) {
    const zone = String(zoneKey);

    if (zone === 'modelsets') {
      for (const [setKey, setVal] of getEntries(zoneVal)) {
        modelsets[String(setKey)] = toArray(setVal);
      }
      continue;
    }

    zoneNames.push(zone);

    for (const [codeKey, defVal] of getEntries(zoneVal)) {
      const code = String(codeKey);
      commands.push({
        zone,
        code,
        name: toStringValue(getProp(defVal, 'name')) ?? code,
        description: toStringValue(getProp(defVal, 'description')) ?? '',
        aliases: toArray(getProp(defVal, 'aliases')),
        values: parseValues(getProp(defVal, 'values')),
      });
    }
  }

  const allModels = Array.from(new Set(Object.values(modelsets).flat())).sort((a, b) => a.localeCompare(b));

  return {
    zones: zoneNames,
    commands,
    modelsets,
    allModels,
  };
}

function parseValues(valuesSource: unknown): ValueDef[] {
  const values: ValueDef[] = [];

  for (const [key, val] of getEntries(valuesSource)) {
    if (key == null) {
      continue;
    }

    values.push({
      key: classifyKey(key),
      names: toArray(getProp(val, 'name')),
      description: toStringValue(getProp(val, 'description')) ?? '',
      models: toArray(getProp(val, 'models')),
    });
  }

  return values;
}

function classifyKey(key: unknown): ValueKey {
  if (Array.isArray(key) && key.length === 2) {
    const start = Number(key[0]);
    const end = Number(key[1]);
    if (Number.isFinite(start) && Number.isFinite(end)) {
      return { kind: 'range', start, end };
    }
  }

  const s = String(key);
  if (/\{[^}]+\}/.test(s) || (/[a-z]{2,}/.test(s) && s.length > 3)) {
    return { kind: 'pattern', template: s };
  }

  return { kind: 'literal', value: s };
}

function getEntries(value: unknown): Array<[unknown, unknown]> {
  if (value instanceof Map) {
    return Array.from(value.entries());
  }

  if (value != null && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>);
  }

  return [];
}

function getProp(source: unknown, key: string): unknown {
  if (source instanceof Map) {
    return source.get(key);
  }

  if (source != null && typeof source === 'object') {
    return (source as Record<string, unknown>)[key];
  }

  return undefined;
}

function toArray(value: unknown): string[] {
  if (value == null) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.filter((item) => item != null).map(String);
  }

  return [String(value)];
}

function toStringValue(value: unknown): string | null {
  if (value == null) {
    return null;
  }

  return String(value);
}
