import { bindable } from 'aurelia';
import { compose } from '../compose/compose-raw';
import type { CommandDef, ValueDef } from '../types';

export class ValueRow {
  @bindable command!: CommandDef;
  @bindable value!: ValueDef;

  userInput = '';
  copyStatus = '';

  binding(): void {
    this.initializeInput();
  }

  valueChanged(): void {
    this.initializeInput(true);
  }

  get keyDisplay(): string {
    if (this.value.key.kind === 'range') {
      return `${this.value.key.start}..${this.value.key.end}`;
    }

    if (this.value.key.kind === 'pattern') {
      return this.value.key.template;
    }

    return this.value.key.value;
  }

  get placeholder(): string {
    if (this.value.key.kind === 'range') {
      return `Integer ${this.value.key.start}..${this.value.key.end}`;
    }

    if (this.value.key.kind === 'pattern') {
      return this.value.key.template;
    }

    return '';
  }

  get result() {
    if (this.value.key.kind === 'literal') {
      return compose(this.command, this.value);
    }

    return compose(this.command, this.value, this.userInput);
  }

  async copy(): Promise<void> {
    if (!this.result.ok) {
      return;
    }

    try {
      await navigator.clipboard.writeText(this.result.raw);
      this.copyStatus = 'Copied';
      window.setTimeout(() => {
        this.copyStatus = '';
      }, 1200);
    } catch {
      this.copyStatus = 'Clipboard failed';
    }
  }

  private initializeInput(force = false): void {
    if (!this.value) {
      return;
    }

    if (this.value.key.kind === 'pattern') {
      if (force || !this.userInput) {
        this.userInput = this.value.key.template;
      }
      return;
    }

    if (force) {
      this.userInput = '';
    }
  }
}
