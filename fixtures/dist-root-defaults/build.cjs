const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const version = require('is-number/package.json').version;
const output = path.join(root, 'dist');
fs.mkdirSync(output, {recursive: true});
fs.writeFileSync(path.join(output, 'dependency.json'), JSON.stringify({'is-number': version}, null, 2) + '\n');
console.log(`Root build generated dist for is-number ${version}.`);
