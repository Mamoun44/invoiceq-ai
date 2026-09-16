import { TestBed } from '@angular/core/testing';
import { InvoiceAiService } from './invoice-ai.service';
import { afterEach, vi } from 'vitest';

describe('InvoiceAiService', () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

  const request = { invoice: {}, invoiceqError: {}, question: 'Help' };

  it('reports an interrupted stream instead of waiting forever', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      'event: status\ndata: {"message":"Analyzing"}\n\n',
    )));
    const service = new InvoiceAiService();
    const error = await new Promise<Error>((resolve) => {
      service.streamExplanation(request).subscribe({ error: resolve });
    });
    expect(error.message).toContain('interrupted');
  });

  it('times out and aborts a stalled request', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockImplementation(() => new Promise(() => {}));
    vi.stubGlobal('fetch', fetchMock);
    const onError = vi.fn();
    new InvoiceAiService().streamExplanation(request).subscribe({ error: onError });
    await vi.advanceTimersByTimeAsync(60000);
    expect(onError).toHaveBeenCalledOnce();
    expect(onError.mock.calls[0][0].message).toContain('too long');
    expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(true);
  });

  it('completes normally on a done event', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('event: done\ndata: {}\n\n')));
    await new Promise<void>((resolve, reject) => {
      new InvoiceAiService().streamExplanation(request).subscribe({ complete: resolve, error: reject });
    });
  });
  it('should be created', () => {
    TestBed.configureTestingModule({});
    expect(TestBed.inject(InvoiceAiService)).toBeTruthy();
  });
});
