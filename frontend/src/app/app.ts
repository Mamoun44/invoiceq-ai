import { Component } from '@angular/core';
import { StoredInvoices } from './stored-invoices/stored-invoices';
import { CommonModule } from '@angular/common';
import { ChatWidgetComponent } from './components/chat-widget/chat-widget';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ChatWidgetComponent, StoredInvoices],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  title = 'InvoiceQ AI';

}
