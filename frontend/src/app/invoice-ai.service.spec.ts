import { TestBed } from '@angular/core/testing';
import { InvoiceAiService } from './invoice-ai.service';

describe('InvoiceAiService', () => {
  it('should be created', () => {
    TestBed.configureTestingModule({});
    expect(TestBed.inject(InvoiceAiService)).toBeTruthy();
  });
});
