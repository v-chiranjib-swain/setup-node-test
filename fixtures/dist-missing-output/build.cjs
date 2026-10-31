const fs = require('node:fs');
const path = require('node:path');

require('is-number');
const output = path.join(__dirname, 'dist');
if (fs.existsSync(output)) {
  throw new Error('Missing-output fixture unexpectedly contains a dist directory.');
}
console.log('Build succeeded without creating the configured output directory.');
