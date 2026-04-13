import type { SelectionStateApi } from './tokens';

const MODEL_KEY = 'eiscp.model';
const ZONE_KEY = 'eiscp.zone';

export class SelectionState implements SelectionStateApi {
  private _model: string | null;
  private _zone: string;

  search = '';
  selectedCode: string | null = null;

  constructor() {
    this._model = normalizeNullable(localStorage.getItem(MODEL_KEY));
    this._zone = localStorage.getItem(ZONE_KEY) ?? 'main';
  }

  get model(): string | null {
    return this._model;
  }

  set model(value: string | null) {
    this._model = normalizeNullable(value);
    if (this._model) {
      localStorage.setItem(MODEL_KEY, this._model);
    } else {
      localStorage.removeItem(MODEL_KEY);
    }
  }

  get zone(): string {
    return this._zone;
  }

  set zone(value: string) {
    const next = value.trim();
    this._zone = next || 'main';
    localStorage.setItem(ZONE_KEY, this._zone);
  }

  ensureDefaults(allModels: string[], zones: string[]): void {
    if (!this._model && allModels.length > 0) {
      this.model = allModels[0];
    }

    if (zones.length > 0 && !zones.includes(this._zone)) {
      this.zone = zones[0];
    }
  }
}

function normalizeNullable(value: string | null): string | null {
  const normalized = (value ?? '').trim();
  return normalized.length > 0 ? normalized : null;
}
