const test = require('node:test');
const assert = require('node:assert/strict');
const BarModel = require('../../BarModel.js');

test('normalizePosition accepts the four edges and falls back to top', () => {
  assert.equal(BarModel.normalizePosition(' left '), 'left');
  assert.equal(BarModel.normalizePosition('bottom'), 'bottom');
  assert.equal(BarModel.normalizePosition('Left'), 'top');
  assert.equal(BarModel.normalizePosition(null), 'top');
});

test('entryId and entrySettings read string and object entries', () => {
  assert.equal(BarModel.entryId('omarchy.clock'), 'omarchy.clock');
  assert.equal(BarModel.entryId({ id: 'omarchy.clock', format: 'HH:mm' }), 'omarchy.clock');
  assert.equal(BarModel.entryId({ format: 'HH:mm' }), '');
  assert.equal(BarModel.entryId(null), '');
  assert.deepEqual(BarModel.entrySettings({ id: 'a', format: 'HH:mm' }), { format: 'HH:mm' });
  assert.deepEqual(BarModel.entrySettings('a'), {});
});

test('pinTrayToInner puts the tray at the edge that faces the bar center', () => {
  const tray = { id: 'omarchy.tray' };
  assert.deepEqual(BarModel.pinTrayToInner(['a', tray, 'b'], 'right'), [tray, 'a', 'b']);
  assert.deepEqual(BarModel.pinTrayToInner(['a', tray, 'b'], 'centerEnd'), [tray, 'a', 'b']);
  assert.deepEqual(BarModel.pinTrayToInner([tray, 'a'], 'left'), ['a', tray]);
  assert.deepEqual(BarModel.pinTrayToInner([tray, 'a'], 'centerBegin'), ['a', tray]);
  assert.deepEqual(BarModel.pinTrayToInner(null, 'left'), []);
});

test('entriesBefore and entriesAfter split a section at a widget', () => {
  const entries = ['a', { id: 'omarchy.clock' }, 'b', 'c'];
  assert.deepEqual(BarModel.entriesBefore(entries, 'omarchy.clock'), ['a']);
  assert.deepEqual(BarModel.entriesAfter(entries, 'omarchy.clock'), ['b', 'c']);
  assert.deepEqual(BarModel.entriesBefore(entries, 'missing'), []);
  assert.deepEqual(BarModel.entriesAfter(entries, 'missing'), []);
});

test('navigationRegions treats the center island as one section', () => {
  assert.deepEqual(BarModel.navigationRegions('center'), ['centerBegin', 'center', 'centerEnd']);
  assert.deepEqual(BarModel.navigationRegions('centerEnd'), ['centerBegin', 'center', 'centerEnd']);
  assert.deepEqual(BarModel.navigationRegions('left'), ['left']);
});

function layout(overrides = {}) {
  return { left: [], centerBegin: [], center: [], centerEnd: [], right: [], tray: [], ...overrides };
}

test('inlineSettingsDelta returns only settings changes, and null for anything structural', () => {
  const before = layout({ center: [{ id: 'omarchy.clock', format: 'HH:mm' }], right: ['omarchy.audio'] });
  const after = layout({ center: [{ id: 'omarchy.clock', format: 'dddd HH:mm' }], right: ['omarchy.audio'] });
  assert.deepEqual(BarModel.inlineSettingsDelta(before, after),
    [{ region: 'center', index: 0, entry: { id: 'omarchy.clock', format: 'dddd HH:mm' } }]);
  assert.deepEqual(BarModel.inlineSettingsDelta(before, before), []);

  assert.equal(BarModel.inlineSettingsDelta(before, layout({ right: ['omarchy.audio'] })), null, 'a removed widget');
  assert.equal(BarModel.inlineSettingsDelta(layout({ left: ['a', 'b'] }), layout({ left: ['b', 'a'] })), null, 'a move');
  assert.equal(BarModel.inlineSettingsDelta(
    layout({ left: [{ id: 'mine', exec: 'date' }] }), layout({ left: [{ id: 'mine', exec: 'uptime' }] })), null,
  'a custom module reads its entry directly');
  assert.equal(BarModel.inlineSettingsDelta(
    layout({ left: [{ id: 'x', a: 1 }], right: [{ id: 'x' }] }), layout({ left: [{ id: 'x', a: 2 }], right: [{ id: 'x' }] })),
  null, 'a duplicated id is ambiguous');
  assert.equal(BarModel.inlineSettingsDelta(null, before), null);
});

test('custom modules: type, safe names and paths', () => {
  assert.equal(BarModel.customModuleType({ id: 'a', exec: 'date' }), 'command');
  assert.equal(BarModel.customModuleType({ id: 'a', source: '~/a.qml' }), 'qml');
  assert.equal(BarModel.customModuleType({ id: 'a', type: 'qml', exec: 'x' }), 'qml');
  assert.equal(BarModel.customModuleType('omarchy.clock'), '');

  assert.equal(BarModel.customModuleSafeName('weather'), true);
  assert.equal(BarModel.customModuleSafeName('../etc'), false);
  assert.equal(BarModel.customModuleSafeName('/abs'), false);
  assert.equal(BarModel.customModuleSafeName(''), false);

  assert.equal(BarModel.customModulePath({ id: 'weather' }, '/h', '/h/.config/omarchy'), '/h/.config/omarchy/bar/modules/weather.qml');
  assert.equal(BarModel.customModulePath({ id: 'w', source: '~/m.qml' }, '/h', '/c'), '/h/m.qml');
  assert.equal(BarModel.customModulePath({ id: 'w', source: '$HOME/m.qml' }, '/h', '/c'), '/h/m.qml');
  assert.equal(BarModel.customModulePath({ id: '../x' }, '/h', '/c'), '', 'an unsafe name gets no path');
});

const slot = (name, drawn = true) => ({ name, visible: drawn, width: drawn ? 20 : 0, height: drawn ? 20 : 0 });

test('pickDrawnSlot prefers the copy on screen over its placeholder', () => {
  const placeholder = slot('placeholder', false);
  const drawn = slot('drawn');
  assert.equal(BarModel.pickDrawnSlot([placeholder, drawn]), drawn);
  assert.equal(BarModel.pickDrawnSlot([placeholder]), placeholder);
  assert.equal(BarModel.pickDrawnSlot([]), null);
});

test('pickPanelSlot: an open panel wins, then the focused monitor', () => {
  const a = slot('a');
  const b = slot('b');
  assert.equal(BarModel.pickPanelSlot([
    { slot: a, screenName: 'DP-1', opened: false },
    { slot: b, screenName: 'HDMI-A-1', opened: true },
  ], 'DP-1'), b);
  assert.equal(BarModel.pickPanelSlot([
    { slot: a, screenName: 'DP-1', opened: false },
    { slot: b, screenName: 'HDMI-A-1', opened: false },
  ], 'HDMI-A-1'), b);
  assert.equal(BarModel.pickPanelSlot([{ slot: a, screenName: 'DP-1' }], 'eDP-1'), a, 'a monitor with no bar');
});

test('nearestDropTarget picks the closest edge along the bar', () => {
  const a = slot('a');
  const b = slot('b');
  const rows = [{ slot: a, x: 0, y: 0, width: 100, height: 30 }, { slot: b, x: 120, y: 0, width: 50, height: 30 }];
  assert.deepEqual(BarModel.nearestDropTarget(rows, { x: 90, y: 5 }, false), { slot: a, after: true });
  assert.deepEqual(BarModel.nearestDropTarget(rows, { x: 115, y: 5 }, false), { slot: b, after: false });
  assert.deepEqual(BarModel.nearestDropTarget(rows, { x: 500, y: 5 }, false), { slot: b, after: true });
  assert.equal(BarModel.nearestDropTarget(rows, { y: 5 }, false), null);
  assert.equal(BarModel.nearestDropTarget([{ slot: a, x: 0, width: 0 }], { x: 0 }, false), null, 'no size, no target');
});
