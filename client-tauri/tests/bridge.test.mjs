import assert from 'node:assert/strict';
import { test } from 'node:test';
import { subscribeBridge } from '../src/apps/backtest/bridge.ts';

const state = (revision, status = 'connected') => ({ revision, status, error: null });
const tick = () => new Promise((resolve) => setImmediate(resolve));
const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

function harness(initialState = state(2)) {
  const listeners = new Map();
  const calls = [];
  const connections = [];
  const events = [];
  const errors = [];
  const replies = new Map([
    ['backtest_get_connection', initialState],
    ['backtest_get_snapshot', null],
  ]);
  const api = {
    async listen(name, handler) {
      listeners.set(name, handler);
      return () => listeners.delete(name);
    },
    async invoke(command) { calls.push(command); return replies.get(command); },
  };
  return {
    api, replies, listeners, calls, connections, events, errors,
    start: () => subscribeBridge(api, (s) => connections.push(s), (e) => events.push(e), (e) => errors.push(e)),
    emit: (name, payload) => listeners.get(name)?.({ payload }),
  };
}

test('late window gets connection and requests both catalogs; reconnect refreshes them', async () => {
  const h = harness();
  const sub = h.start();
  await sub.ready;
  assert.deepEqual(h.connections, [state(2)]);
  assert.equal(h.calls.filter((x) => x === 'backtest_list_data').length, 1);
  h.emit('backtest:connection', state(3, 'disconnected'));
  h.emit('backtest:connection', state(4, 'connecting'));
  h.emit('backtest:connection', state(5));
  h.emit('backtest:connection', state(5));
  assert.equal(h.calls.filter((x) => x === 'backtest_list_data').length, 2);
  assert.equal(h.calls.filter((x) => x === 'backtest_list_strategies').length, 2);
  sub.dispose();
  assert.equal(h.listeners.size, 0);
});

test('late initial response cannot overwrite newer connection event', async () => {
  const pending = deferred();
  const h = harness(pending.promise);
  const sub = h.start();
  await tick();
  h.emit('backtest:connection', state(5));
  pending.resolve(state(3, 'disconnected'));
  await sub.ready;
  assert.deepEqual(h.connections, [state(5)]);
  sub.dispose();
});

test('old connection payloads and errors do not affect a new connection', async () => {
  const pending = deferred();
  const h = harness();
  h.replies.set('backtest_list_data', pending.promise);
  const sub = h.start();
  await sub.ready;
  h.emit('backtest:connection', state(3, 'disconnected'));
  h.replies.set('backtest_list_data', undefined);
  h.emit('backtest:connection', state(5));
  pending.reject(new Error('old command'));
  h.emit('backtest:event', { revision: 2, payload: '{bad json' });
  h.emit('backtest:event', { revision: 5, payload: JSON.stringify({ type: 'data_list', data: [] }) });
  await tick();
  assert.equal(h.errors.length, 0);
  assert.equal(h.events.length, 1);
  sub.dispose();
});

test('unmount during asynchronous listener registration removes late listener', async () => {
  const pending = deferred();
  const h = harness();
  let cleaned = 0;
  h.api.listen = () => pending.promise;
  const sub = h.start();
  sub.dispose();
  pending.resolve(() => { cleaned++; });
  await sub.ready;
  assert.equal(cleaned, 1);
  assert.equal(h.calls.length, 0);
});

test('partial initialization failure removes subscriptions and reports error', async () => {
  const h = harness();
  const listen = h.api.listen;
  h.api.listen = (name, handler) => name === 'backtest:connection'
    ? Promise.reject(new Error('listen failed')) : listen(name, handler);
  const sub = h.start();
  await sub.ready;
  assert.equal(h.listeners.size, 0);
  assert.match(h.errors[0].message, /listen failed/);
});

test('cached snapshot never overwrites newer live session data', async () => {
  const h = harness();
  const pending = deferred();
  h.replies.set('backtest_get_snapshot', pending.promise);
  const sub = h.start();
  await tick();
  h.emit('backtest:event', { revision: 2, payload: JSON.stringify({ type: 'ready', total_bars: 73 }) });
  pending.resolve({ revision: 2, payload: JSON.stringify({ type: 'snapshot', bars: [] }) });
  await sub.ready;
  assert.deepEqual(h.events.map((e) => e.type), ['ready']);
  sub.dispose();
});
