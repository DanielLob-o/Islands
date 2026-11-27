const test = require('node:test');
const assert = require('node:assert/strict');
const { functionSource, read, Util } = require('../helpers/qml-functions.cjs');

// islandNumber reads `islandSettings` without a qualifier, so each test gives its own.
function islandNumber(islandSettings) {
  const factory = new Function('Util', 'islandSettings', `return (${functionSource('Bar.qml', 'islandNumber')});`);
  return factory(Util, islandSettings);
}

test('islandNumber clamps numbers and falls back for anything that is not one', () => {
  assert.equal(islandNumber({ opacity: 0.5 })('opacity', 1, 0, 1), 0.5);
  assert.equal(islandNumber({ opacity: '0.25' })('opacity', 1, 0, 1), 0.25, 'a string written without --json');
  assert.equal(islandNumber({ opacity: 2 })('opacity', 1, 0, 1), 1);
  assert.equal(islandNumber({ radius: -5 })('radius', -1, -1, 999), -1);
  assert.equal(islandNumber({ opacity: null })('opacity', 1, 0, 1), 1);
  assert.equal(islandNumber({ opacity: '' })('opacity', 1, 0, 1), 1);
  assert.equal(islandNumber({ opacity: 'half' })('opacity', 1, 0, 1), 1);
  assert.equal(islandNumber({})('padding', 10, 0, 64), 10);
});

test('colorHex writes a color as #rrggbb and clamps each channel', () => {
  const Qt = { color: () => { throw new Error('only used for strings'); } };
  const colorHex = new Function('Util', 'Qt', `return (${functionSource('Bar.qml', 'colorHex')});`)(Util, Qt);
  assert.equal(colorHex({ r: 1, g: 0.5, b: 0 }), '#ff8000');
  assert.equal(colorHex({ r: 0, g: 0, b: 0.05 }), '#00000d');
  assert.equal(colorHex({ r: 2, g: -1, b: 1 }), '#ff00ff');
});

test('the README documents every islands setting that Bar.qml reads', () => {
  const bar = read('Bar.qml');
  const readme = read('README.md');
  const keys = new Set([
    ...[...bar.matchAll(/islandNumber\("(\w+)"/g)].map(m => m[1]),
    ...[...bar.matchAll(/islandSettings\.(\w+)/g)].map(m => m[1]),
  ]);
  assert.ok(keys.size > 0);
  const missing = [...keys].filter(key => !readme.includes(`\`${key}\``));
  assert.deepEqual(missing, [], 'settings missing from the README table');
});
