const fs = require('node:fs');
const path = require('node:path');

const output = path.join(__dirname, 'dist');
fs.mkdirSync(output, { recursive: true });
fs.writeFileSync(
  path.join(output, 'generated.json'),
  JSON.stringify({ fixture: 'stable-output' }, null, 2) + '\n'
);
