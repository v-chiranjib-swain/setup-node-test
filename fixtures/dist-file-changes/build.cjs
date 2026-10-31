const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const version = require('is-number/package.json').version;
const output = path.join(__dirname, 'dist');
const unrelated = path.join(__dirname, 'unrelated.txt');

fs.mkdirSync(output, {recursive: true});
fs.writeFileSync(path.join(output, 'dependency.json'), JSON.stringify({'is-number': version}, null, 2) + '\n');
fs.writeFileSync(path.join(output, 'added.txt'), `Generated with is-number ${version}\n`);
fs.unlinkSync(path.join(output, 'obsolete.txt'));
fs.writeFileSync(unrelated, 'Changed by build; must not be published.\n');
assert.equal(fs.readFileSync(unrelated, 'utf8'), 'Changed by build; must not be published.\n');
console.log('Generated addition, modification, and deletion; also changed tracked unrelated.txt.');
