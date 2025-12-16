import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

export function loadScriptIntoContext(scriptPath, context = {}) {
  const abs = path.isAbsolute(scriptPath) ? scriptPath : path.resolve(process.cwd(), scriptPath);
  const code = fs.readFileSync(abs, 'utf-8');

  const ctx = vm.createContext({
    console,
    URL,
    setTimeout,
    clearTimeout,
    // Default: disable intervals unless test explicitly wants them
    setInterval: () => 0,
    clearInterval: () => {},
    ...context,
  });

  // Execute as a script in the provided context.
  vm.runInContext(code, ctx, { filename: abs });

  // Allow tests to mutate top-level `let` variables inside the context
  // (they are not exposed as properties on `ctx`).
  ctx.__eval = (js) => vm.runInContext(String(js), ctx);
  return ctx;
}
