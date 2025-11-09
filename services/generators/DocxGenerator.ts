
import { Generator } from './BaseGenerator';
import { inlineStyles } from '../styleInliner';

// Assume htmlToDocx is available globally from the vendor script
declare const htmlToDocx: any;

export class DocxGenerator implements Generator {
    public async generate(element: HTMLElement, fileName: string): Promise<void> {
         if (typeof htmlToDocx === 'undefined') {
            console.error('html-to-docx.js is not loaded.');
            throw new Error('DOCX generation library is not available.');
        }

        // html-to-docx requires styles to be inlined.
        const htmlStringWithStyles = await inlineStyles(element);

        // The header is important for correct encoding and display in Word.
        const fullHtml = `
            <!DOCTYPE html>
            <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
            <head>
                <meta charset='utf-8'>
                <title>Generated Document</title>
                <!--[if gte mso 9]>
                <xml>
                    <w:WordDocument>
                    <w:View>Print</w:View>
                    <w:Zoom>90</w:Zoom>
                    </w:WordDocument>
                </xml>
                <![endif]-->
            </head>
            <body>
                ${htmlStringWithStyles}
            </body>
            </html>
        `;

        const fileBuffer = await htmlToDocx(fullHtml, null, {
            // Options can be passed here if needed
        });
        
        const blob = new Blob([fileBuffer], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${fileName}.docx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    }
}
