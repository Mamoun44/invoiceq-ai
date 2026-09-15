import { afterEach, describe, expect, it, vi } from 'vitest';
import { StoredInvoices } from './stored-invoices';

describe('StoredInvoices', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('clears the password and forwards only the logged-in bearer session', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ accessToken: 'test-session', user: { email: 'user@example.test', role: 'VIEWER', corporationId: 'A' } })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'ok', answer: 'AED 105', explanationSource: 'template' })));
    vi.stubGlobal('fetch', fetchMock);
    const panel = new StoredInvoices();
    panel.email = 'user@example.test'; panel.password = 'example-password';
    await panel.login();
    expect(panel.password).toBe('');
    panel.question = 'Total including tax for all statuses';
    await panel.ask();
    expect(fetchMock.mock.calls[1][0]).toBe('/api/api/invoices/ask');
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer test-session');
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ question: panel.question });
  });
  it('clears private results on an expired session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 401 })));
    const panel = new StoredInvoices();
    panel.session.set({ accessToken: 'expired', user: { email: 'user@example.test', role: 'VIEWER', corporationId: 'A' } });
    panel.question = 'invoice number 001';
    await panel.ask();
    expect(panel.session()).toBeNull();
    expect(panel.answer()).toBeNull();
    expect(panel.error()).toContain('Sign in');
  });
});
