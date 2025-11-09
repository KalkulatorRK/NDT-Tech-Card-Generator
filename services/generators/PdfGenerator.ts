
import { Generator } from './BaseGenerator';

// Assume html2pdf is available globally from the vendor script
declare const html2pdf: any;

export class PdfGenerator implements Generator {
    public async generate(element: HTMLElement, fileName: string): Promise<void> {
        if (typeof html2pdf === 'undefined') {
            console.error('html2pdf.js is not loaded.');
            throw new Error('PDF generation library is not available.');
        }

        const options = {
            margin:       [2, 1.5, 2, 1.5], // top, left, bottom, right in cm
            filename:     `${fileName}.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2, useCORS: true, logging: false },
            jsPDF:        { unit: 'cm', format: 'a4', orientation: 'portrait' }
        };
        
        // The library handles the promise-based flow.
        await html2pdf().from(element).set(options).save();
    }
}
