import { Component, OnDestroy, ChangeDetectorRef, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import {
  InvoiceAiEvent,
  InvoiceAiService,
  InvoiceExplainRequest,
} from '../../invoice-ai.service';

interface InvoiceContext {
  invoice: Record<string, unknown>;
  invoiceqError: Record<string, unknown>;
}

interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  statusText?: string;
  aiText?: string;
}

@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-widget.html',
  styleUrls: ['./chat-widget.css']
})

export class ChatWidgetComponent implements OnDestroy {
  @Input() activeInvoice: InvoiceContext = {
    invoice: {
      invoiceNumber: 'INV-2026-991',
      currencyIsoCode: 'AED',
      supplier: { taxId: '' },
    },
    invoiceqError: {
      httpStatus: 400,
      valid: false,
      errors: [{ reason: 'supplier.taxId', errorDescription: 'Missing tax identification number.' }],
    },
  };

  userQuery = '';
  isOpen = false;
  isStreaming = false;
  messages: ChatMessage[] = [];
  private streamSubscription?: Subscription;

  constructor(
    private invoiceAiService: InvoiceAiService,
    private cdr: ChangeDetectorRef,
  ) {}

  toggleChat(): void {
    this.isOpen = !this.isOpen;
  }

  submitCheck(): void {
    const question = this.userQuery.trim();
    if (!question || this.isStreaming) return;

    this.messages.push({ sender: 'user', text: question });
    const botMessage: ChatMessage = {
      sender: 'bot',
      text: '',
      statusText: 'Connecting to InvoiceQ AI…',
      aiText: '',
    };
    this.messages.push(botMessage);

    const request: InvoiceExplainRequest = {
      invoice: this.activeInvoice.invoice,
      invoiceqError: this.activeInvoice.invoiceqError,
      question,
    };

    this.userQuery = '';
    this.isStreaming = true;
    this.refreshMessage(botMessage);

    this.streamSubscription = this.invoiceAiService.streamExplanation(request).subscribe({
      next: (event) => this.handleEvent(event, botMessage),
      error: (error: unknown) => {
        botMessage.statusText = '';
        botMessage.aiText = error instanceof Error ? error.message : 'The AI service is unavailable.';
        this.isStreaming = false;
        this.refreshMessage(botMessage);
      },
      complete: () => {
        this.isStreaming = false;
        this.cdr.detectChanges();
      },
    });
  }

  private handleEvent(event: InvoiceAiEvent, message: ChatMessage): void {
    if (event.type === 'status') {
      message.statusText = String(event.data['message'] ?? 'Searching documentation…');
    } else if (event.type === 'token') {
      message.statusText = '';
      message.aiText = (message.aiText ?? '') + String(event.data['text'] ?? '');
    } else if (event.type === 'error') {
      message.statusText = '';
      message.aiText = String(event.data['message'] ?? 'Unable to generate an explanation.');
      this.isStreaming = false;
    } else if (event.type === 'done') {
      message.statusText = '';
      this.isStreaming = false;
    }

    this.refreshMessage(message);
  }

  private refreshMessage(message: ChatMessage): void {
    const status = message.statusText ? `${message.statusText}\n\n` : '';
    message.text = status + (message.aiText ?? '');
    this.cdr.detectChanges();
  }

  ngOnDestroy(): void {
    this.streamSubscription?.unsubscribe();
  }
}
