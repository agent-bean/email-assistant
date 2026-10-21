import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = fileURLToPath(new URL('..', import.meta.url));
const backend = fileURLToPath(new URL('../../backend/', import.meta.url));
const temp = mkdtempSync(join(tmpdir(), 'email-assistant-schema-'));
try {
  const schema = execFileSync('uv', ['run', '--locked', 'python', '-c',
    'import json; from email_assistant.api.main import app; print(json.dumps(app.openapi(), sort_keys=True, indent=2))'],
    { cwd: backend, encoding: 'utf8' });
  const input = join(temp, 'openapi.json');
  const output = join(temp, 'schema.d.ts');
  writeFileSync(input, schema);
  execFileSync('npm', ['exec', '--no', '--', 'openapi-typescript', input, '-o', output], { cwd: web, stdio: 'pipe' });
  const targets = [[join(backend, 'openapi.json'), schema], [join(web, 'src/api/schema.d.ts'), readFileSync(output, 'utf8')]];
  for (const [path, content] of targets) {
    if (process.argv.includes('--check')) {
      if (readFileSync(path, 'utf8') !== content) throw new Error('API contract drift: run npm run api:generate');
    } else writeFileSync(path, content);
  }
} finally { rmSync(temp, { recursive: true, force: true }); }
