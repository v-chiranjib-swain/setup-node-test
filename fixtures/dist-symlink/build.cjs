const fs = require('node:fs');
const path = require('node:path');
const version = require('is-number/package.json').version;

const output = path.join(__dirname, 'dist');
fs.mkdirSync(output, { recursive: true });
fs.writeFileSync(
  path.join(output, 'dependency.json'),
  JSON.stringify({ 'is-number': version }, null, 2) + '\n'
);
fs.symlinkSync('../package.json', path.join(output, 'unsafe-link'));
