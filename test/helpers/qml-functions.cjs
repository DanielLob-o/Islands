// Loads production functions out of the plugin's QML and JS files, so unit tests run
// the real code with fake inputs. This proves the logic, not QML bindings or rendering.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..', '..');

function read(file) {
  return fs.readFileSync(path.join(ROOT, file), 'utf8');
}

// The index just past the brace that closes the one at `open`. Skips strings and comments.
function closingBrace(source, open) {
  let depth = 0;
  for (let i = open; i < source.length; i++) {
    const c = source[i];
    if (c === '"' || c === "'" || c === '`') {
      for (i++; i < source.length && source[i] !== c; i++) if (source[i] === '\\') i++;
    } else if (source.startsWith('//', i)) {
      i = source.indexOf('\n', i);
      if (i === -1) break;
    } else if (c === '{') {
      depth++;
    } else if (c === '}' && --depth === 0) {
      return i + 1;
    }
  }
  throw new Error('unbalanced braces');
}

// The text of `function name(...) { ... }` as it appears in the file.
function functionSource(file, name) {
  const source = read(file);
  const match = new RegExp(`^[ \\t]*function ${name}\\s*\\(`, 'm').exec(source);
  if (!match) throw new Error(`function ${name} not found in ${file}`);
  const start = match.index + match[0].indexOf('function');
  return source.slice(start, closingBrace(source, source.indexOf('{', match.index + match[0].length)));
}

// Puts the named functions from `file` on scope.root, with scope's other keys as globals.
function load(file, names, scope) {
  const keys = Object.keys(scope);
  for (const name of names) {
    const factory = new Function(...keys, `return (${functionSource(file, name)});`);
    scope.root[name] = factory(...keys.map(key => scope[key]));
  }
  return scope.root;
}

// A `.pragma library` JS file, evaluated as QML would, with its top-level names returned.
function library(file) {
  const context = vm.createContext({});
  vm.runInContext(read(file).replace(/^\.pragma library\s*$/m, ''), context, { filename: file });
  return context;
}

// What Omarchy's Util and Translations provide, enough for the plugin's logic.
const Util = {
  clamp: (value, min, max) => Math.max(min, Math.min(max, value)),
  shellQuote: value => `'${String(value).replace(/'/g, `'\\''`)}'`,
};

// QML strings have Qt's arg(): it fills the lowest-numbered %N placeholder.
if (!String.prototype.arg) {
  Object.defineProperty(String.prototype, 'arg', {
    value(value) {
      const numbers = [...this.matchAll(/%(\d+)/g)].map(m => Number(m[1]));
      if (numbers.length === 0) return String(this);
      return this.replace(new RegExp(`%${Math.min(...numbers)}(?!\\d)`, 'g'), String(value));
    },
  });
}

// A stand-in for Commons.Translations that reads i18n/en.json with English plural rules.
function strings() {
  const catalog = JSON.parse(read('i18n/en.json'));
  const t = key => (typeof catalog[key] === 'object' ? catalog[key].other : catalog[key]) ?? key;
  const tn = (key, count) => {
    const entry = catalog[key];
    if (typeof entry !== 'object') return t(key);
    return (count === 1 ? entry.one : undefined) ?? entry.other;
  };
  return { t, tn };
}

const I18n = { formatNumber: value => String(value), rightToLeft: false };

module.exports = { ROOT, read, functionSource, load, library, strings, I18n, Util };
