See the RELEASING.md for the process
The webview is in Aurelia 2 and you build the dist with `bun run build` or to do development `bun run start`.  The webview technically reads the raw yaml file but for dist it gets embedded into the index.html (so it can work even as a local file).
