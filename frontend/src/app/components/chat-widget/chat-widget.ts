import { Component, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import {
  InvoiceAiEvent,
  InvoiceAiService,
  InvoiceExplainRequest,
} from '../../invoice-ai.service';

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
  invoiceJson = '';
  errorJson = '';
  inputError = '';

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

    this.inputError = '';
    let request: InvoiceExplainRequest;
    try {
      request = {
        invoice: this.parseJson(this.invoiceJson, 'Invoice JSON'),
        invoiceqError: this.parseJson(this.errorJson, 'Error response JSON'),
        question,
      };
    } catch (error) {
      this.inputError = error instanceof Error ? error.message : 'Please check your JSON.';
      return;
    }

    this.messages.push({ sender: 'user', text: question });
    const botMessage: ChatMessage = {
      sender: 'bot',
      text: '',
      statusText: 'Connecting to InvoiceQ AI…',
      aiText: '',
    };
    this.messages.push(botMessage);

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
        botMessage.statusText = '';
        if (!botMessage.aiText) botMessage.aiText = 'No answer was received. Please try again.';
        this.refreshMessage(botMessage);
      },
    });
  }

  clearDetails(): void {
    this.invoiceJson = '';
    this.errorJson = '';
    this.inputError = '';
  }

  private parseJson(text: string, label: string): Record<string, unknown> | null {
    if (!text.trim()) return null;
    let value: unknown;
    try { value = JSON.parse(text); }
    catch { throw new Error(`${label} is not valid JSON. Check the quotes, commas, and brackets.`); }
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
      throw new Error(`${label} must be a JSON object enclosed in { }.`);
    }
    return value as Record<string, unknown>;
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
