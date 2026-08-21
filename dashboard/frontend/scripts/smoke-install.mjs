// npm v12 install-scripts smoke test (card 0c00d7eb)
//
// npm 12 bloquea los install scripts de dependencias por defecto y reporta
// exit 0 silencioso: si el binario nativo de esbuild no llegó por optional
// platform deps NI por postinstall aprobado, el fallo aparece en runtime.
// Este smoke corre post-install en CI/Docker y FALLA el build si esbuild o
// vite no cargan, cerrando el camino del silent-failure.
//
// Uso: node scripts/smoke-install.mjs   (tras npm ci / npm install)

const failures = [];

// --- esbuild: cargar módulo + invocar el binario nativo de verdad ---
// import() puede resolver el JS aunque el binario falte; transformSync()
// solo funciona si el binario nativo existe y ejecuta.
try {
  const esbuild = await import('esbuild');
  const out = esbuild.transformSync('const answer = 6 * 7;', { loader: 'js' });
  if (!out.code || !out.code.includes('answer')) {
    throw new Error(`salida inesperada de transformSync: ${JSON.stringify(out.code)}`);
  }
  console.log(`[smoke] esbuild OK — binario nativo responde (${out.code.trim().length} bytes)`);
} catch (err) {
  failures.push(`esbuild: ${err.message}`);
}

// --- vite: carga del módulo (v5 es ESM-only, no require()) ---
try {
  const vite = await import('vite');
  const version = vite.version ?? 'unknown';
  console.log(`[smoke] vite OK — módulo carga (v${version})`);
} catch (err) {
  failures.push(`vite: ${err.message}`);
}

if (failures.length > 0) {
  console.error('[smoke] FALLO post-install — módulos no operativos:');
  for (const f of failures) console.error(`  - ${f}`);
  console.error('[smoke] Causa probable: install script bloqueado por npm v12 sin allowScripts aprobado.');
  process.exit(1);
}

console.log('[smoke] SMOKE-OK: esbuild + vite operativos post-install');
