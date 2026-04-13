import type { CommandDef, ValueDef } from '../types';

export type ComposeResult =
  | { ok: true; raw: string; prettyZone: string; prettyCommand: string; prettyArg: string }
  | { ok: false; error: string };

export function compose(cmd: CommandDef, value: ValueDef, userInput?: string): ComposeResult {
  switch (value.key.kind) {
    case 'literal':
      return finish(cmd, value, value.key.value);

    case 'range': {
      if (userInput == null || userInput.trim() === '') {
        return err('Enter a value');
      }

      const n = Number(userInput);
      if (!Number.isInteger(n)) {
        return err('Enter an integer');
      }

      if (n < value.key.start || n > value.key.end) {
        return err(`Out of range ${value.key.start}..${value.key.end}`);
      }

      if (cmd.code === 'SWL' || cmd.code === 'CTL') {
        const absHex = Math.abs(n).toString(16).toUpperCase().padStart(2, '0');
        if (n === 0) {
          return finish(cmd, value, '00');
        }
        return finish(cmd, value, `${n > 0 ? '+' : '-'}${absHex}`);
      }

      const hex = n.toString(16).toUpperCase().padStart(2, '0');
      return finish(cmd, value, hex);
    }

    case 'pattern': {
      const filled = userInput ?? value.key.template;
      return finish(cmd, value, filled);
    }
  }
}

function finish(cmd: CommandDef, value: ValueDef, encoded: string): ComposeResult {
  return {
    ok: true,
    raw: cmd.code + encoded,
    prettyZone: cmd.zone,
    prettyCommand: cmd.name,
    prettyArg: value.names[0] ?? encoded,
  };
}

function err(error: string): ComposeResult {
  return { ok: false, error };
}
