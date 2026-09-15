import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface Session { accessToken: string; user: { email: string; role: string; corporationId: string }; }
interface Answer {
  status: string; answer: string; explanationSource: string;
  tool?: { amountType?: string; statusScope?: string; statuses?: string[]; currency?: string; dateFrom?: string; dateTo?: string };
  result?: { totals: { currency: string; amount: string; invoiceCount: number }[] };
}

@Component({
  selector: 'app-stored-invoices', standalone: true, imports: [CommonModule, FormsModule],
  templateUrl: './stored-invoices.html', styleUrl: './stored-invoices.css',
})
export class StoredInvoices {
  email = ''; password = ''; question = '';
  readonly session = signal<Session | null>(null);
  readonly busy = signal(false);
  readonly error = signal('');
  readonly answer = signal<Answer | null>(null);
  private async request(path: string, body?: unknown): Promise<Response> {
    const token = this.session()?.accessToken;
    const response = await fetch('/api/' + path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'omit', cache: 'no-store',
    });
    if (!response.ok) {
      if (response.status === 401) { this.session.set(null); this.answer.set(null); }
      throw new Error(response.status === 401 ? 'Sign in again or check your email and password.' :
        response.status === 403 ? 'You do not have permission for this action.' :
        response.status === 429 ? 'Too many requests. Please wait and retry.' :
        'The service is unavailable or the request could not be completed. Please retry.');
    }
    return response;
  }
  async login(): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true); this.error.set(''); this.answer.set(null);
    try {
      const response = await this.request('auth/login', { email: this.email, password: this.password });
      this.session.set(await response.json());
    } catch (error) { this.error.set(error instanceof Error ? error.message : 'Login failed.'); }
    finally { this.password = ''; this.busy.set(false); }
  }
  async logout(): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true); this.error.set('');
    try { await this.request('auth/logout', {}); }
    catch { this.error.set('Signed out locally. Server logout could not be confirmed; the session expires within one hour.'); }
    finally { this.session.set(null); this.answer.set(null); this.question = ''; this.busy.set(false); }
  }
  async ask(): Promise<void> {
    if (this.busy() || !this.question.trim() || !this.session()) return;
    this.busy.set(true); this.error.set(''); this.answer.set(null);
    try {
      const response = await this.request('api/invoices/ask', { question: this.question.trim() });
      this.answer.set(await response.json());
    } catch (error) { this.error.set(error instanceof Error ? error.message : 'Query failed.'); }
    finally { this.busy.set(false); }
  }
}
