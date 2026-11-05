const fs = require('node:fs');
const path = require('node:path');

const version = require('is-number/package.json').version;
const output = path.join(__dirname, 'dist');
fs.mkdirSync(output, {recursive: true});
fs.writeFileSync(path.join(output, 'dependency.json'), JSON.stringify({'is-number': version}, null, 2) + '\n');
fs.writeFileSync(path.join(output, 'added.txt'), `Generated with is-number ${version}\n`);
fs.unlinkSync(path.join(output, 'obsolete.txt'));
fs.writeFileSync(path.join(__dirname, 'unrelated.txt'), 'Build modified this file; do not publish.\n');
console.log('Generated changes and an unrelated tracked-file modification.');
