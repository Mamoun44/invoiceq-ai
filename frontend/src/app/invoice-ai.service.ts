import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface InvoiceExplainRequest {
  invoice: Record<string, unknown>;
  invoiceqError: Record<string, unknown>;
  question: string;
}

export type InvoiceAiEventType = 'status' | 'token' | 'done' | 'error';

export interface InvoiceAiEvent {
  type: InvoiceAiEventType;
  data: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class InvoiceAiService {
  private readonly streamUrl = '/api/test-ai/explain/stream';

  streamExplanation(request: InvoiceExplainRequest): Observable<InvoiceAiEvent> {
    return new Observable((subscriber) => {
      const abortController = new AbortController();

      void this.consumeStream(request, abortController.signal, (event) => {
        subscriber.next(event);
        if (event.type === 'done' || event.type === 'error') {
          subscriber.complete();
        }
      }).catch((error: unknown) => {
        if (!abortController.signal.aborted) {
          subscriber.error(error);
        }
      });

      return () => abortController.abort();
    });
  }

  private async consumeStream(
    request: InvoiceExplainRequest,
    signal: AbortSignal,
    emit: (event: InvoiceAiEvent) => void,
  ): Promise<void> {
    const response = await fetch(this.streamUrl, {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal,
    });

    if (!response.ok) {
      const details = await response.text();
      throw new Error(`AI request failed (${response.status}): ${details}`);
    }
    if (!response.body) {
      throw new Error('The AI response did not contain a stream.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n');

      let boundary = buffer.indexOf('\n\n');
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        this.parseEvent(block, emit);
        boundary = buffer.indexOf('\n\n');
      }

      if (done) {
        if (buffer.trim()) {
          this.parseEvent(buffer, emit);
        }
        break;
      }
    }
  }

  private parseEvent(block: string, emit: (event: InvoiceAiEvent) => void): void {
    let eventType: InvoiceAiEventType = 'token';
    const dataLines: string[] = [];

    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) {
        eventType = line.slice(6).trim() as InvoiceAiEventType;
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart());
      }
    }

    if (dataLines.length === 0) {
      return;
    }

    const parsedData: unknown = JSON.parse(dataLines.join('\n'));
    const data =
      typeof parsedData === 'object' && parsedData !== null
        ? (parsedData as Record<string, unknown>)
        : { value: parsedData };

    emit({ type: eventType, data });
  }
}
