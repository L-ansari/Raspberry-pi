import assert from 'node:assert/strict';
import { test } from 'node:test';
import { sendGreenhouseMessage } from '../src/services/api.js';

test('chat validates input before making a request', async (t) => {
  let requests = 0;
  t.mock.method(globalThis, 'fetch', async () => { requests++; });
  for (const message of ['', '   ', null, 'x'.repeat(2001)]) {
    await assert.rejects(sendGreenhouseMessage(message), /1 and 2,000/);
  }
  assert.equal(requests, 0);
});

test('chat sends only the question and language and supports cancellation', async (t) => {
  const controller = new AbortController();
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.match(url, /\/api\/llm\/chat\/$/);
    assert.equal(options.method, 'POST');
    assert.deepEqual(JSON.parse(options.body), { message: 'Check the greenhouse', language: 'en' });
    assert.equal(options.signal, controller.signal);
    return Response.json({ status: 'success', reply: '  Check the readings.  ', context_used: { latest_reading: false } });
  });
  const result = await sendGreenhouseMessage('  Check the greenhouse  ', 'en', { signal: controller.signal });
  assert.equal(result.reply, 'Check the readings.');
  assert.equal(result.context_used.latest_reading, false);
});

test('chat rejects unsuccessful, empty, or malformed responses', async (t) => {
  const fixtures = [
    [() => Response.json({ error: 'Model unavailable' }, { status: 503 }), /Model unavailable/],
    [() => Response.json({ errors: { message: ['Invalid question'] } }, { status: 400 }), /Invalid question/],
    [() => Response.json({ error: 'Unexpected failure' }), /Unexpected failure/],
    [() => Response.json({ status: 'success', reply: '   ' }), /empty answer/],
    [() => Response.json({ status: 'success', reply: 12 }), /invalid/],
    [() => Response.json(null), /invalid/],
    [() => new Response('<html>Error</html>', { status: 502 }), /invalid response/],
  ];
  for (const [response, error] of fixtures) {
    t.mock.method(globalThis, 'fetch', async () => response());
    await assert.rejects(sendGreenhouseMessage('What are the conditions?'), error);
    t.mock.restoreAll();
  }
});

test('chat propagates network and cancellation failures', async (t) => {
  for (const error of [new TypeError('Failed to fetch'), new DOMException('Aborted', 'AbortError')]) {
    t.mock.method(globalThis, 'fetch', async () => { throw error; });
    await assert.rejects(sendGreenhouseMessage('What are the conditions?'), (result) => result === error);
    t.mock.restoreAll();
  }
});

test('chat preserves the service status for a friendly unavailable message', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({ error: 'Ollama unavailable' }, { status: 503 }));
  await assert.rejects(sendGreenhouseMessage('What are the conditions?'), (error) => error.status === 503);
});
