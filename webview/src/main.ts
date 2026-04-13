import Aurelia, { Registration } from 'aurelia';
import { MyApp } from './my-app';
import { loadCommands } from './parser/load-commands';
import { SelectionState } from './services/selection';
import { ICommandDatabase, ISelectionState } from './services/tokens';

const db = loadCommands();

Aurelia
  .register(
    Registration.instance(ICommandDatabase, db),
    Registration.singleton(ISelectionState, SelectionState)
  )
  .app(MyApp)
  .start();
