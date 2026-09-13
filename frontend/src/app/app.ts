import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatWidgetComponent } from './components/chat-widget/chat-widget';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ChatWidgetComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  title = 'InvoiceQ AI';

  selectedInvoiceFromTable = {
    invoice: {
      invoiceNumber: 'INV-2026-991',
      currencyIsoCode: 'AED',
      supplier: { taxId: '' },
      totalInvoiceAmount: 4500,
    },
    invoiceqError: {
      httpStatus: 400,
      traceId: 'demo-trace-id',
      valid: false,
      errors: [{ reason: 'supplier.taxId', errorDescription: 'Missing tax identification number.' }],
      body: null,
    },
  };

  onInvoiceRowClick(clickedInvoice: typeof this.selectedInvoiceFromTable): void {
    this.selectedInvoiceFromTable = clickedInvoice;
  }
}
