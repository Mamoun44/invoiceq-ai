import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { vi } from 'vitest';
import { ChatWidgetComponent } from './chat-widget';
import { InvoiceAiService } from '../../invoice-ai.service';

describe('Guest chat input', () => {
  async function setup() {
    const streamExplanation = vi.fn().mockReturnValue(of({ type: 'done', data: {} }));
    await TestBed.configureTestingModule({
      imports: [ChatWidgetComponent],
      providers: [{ provide: InvoiceAiService, useValue: { streamExplanation } }],
    }).compileComponents();
    const fixture = TestBed.createComponent(ChatWidgetComponent);
    fixture.detectChanges();
    return { widget: fixture.componentInstance, streamExplanation };
  }

  it('sends a general question without invented invoice context', async () => {
    const { widget, streamExplanation } = await setup();
    widget.userQuery = 'What is currencyIsoCode?';
    widget.submitCheck();
    expect(streamExplanation).toHaveBeenCalledWith({
      question: 'What is currencyIsoCode?', invoice: null, invoiceqError: null,
    });
  });

  it('sends exactly the supplied objects and allows clearing them', async () => {
    const { widget, streamExplanation } = await setup();
    widget.userQuery = 'Why did this fail?';
    widget.invoiceJson = '{"invoiceNumber":"USER-1"}';
    widget.errorJson = '{"httpStatus":400}';
    widget.submitCheck();
    expect(streamExplanation).toHaveBeenCalledWith({
      question: 'Why did this fail?', invoice: { invoiceNumber: 'USER-1' }, invoiceqError: { httpStatus: 400 },
    });
    widget.clearDetails();
    expect(widget.invoiceJson).toBe('');
    expect(widget.errorJson).toBe('');
  });

  it('blocks invalid JSON and non-object values without losing the question', async () => {
    const { widget, streamExplanation } = await setup();
    for (const invalid of ['{broken', '[]', 'null', '42']) {
      widget.userQuery = 'Check this invoice';
      widget.invoiceJson = invalid;
      widget.submitCheck();
      expect(widget.inputError).toContain('Invoice JSON');
      expect(widget.userQuery).toBe('Check this invoice');
      expect(widget.isStreaming).toBe(false);
    }
    widget.invoiceJson = '{}';
    widget.errorJson = '[';
    widget.submitCheck();
    expect(widget.inputError).toContain('Error response JSON');
    expect(streamExplanation).not.toHaveBeenCalled();
  });
});
