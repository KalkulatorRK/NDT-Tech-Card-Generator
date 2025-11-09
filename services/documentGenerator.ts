
import { PdfGenerator } from './generators/PdfGenerator';
import { DocxGenerator } from './generators/DocxGenerator';

const pdfGenerator = new PdfGenerator();
const docxGenerator = new DocxGenerator();

/**
 * Generates and triggers a download for a document from an HTML element.
 * @param {HTMLElement} element The HTML element to convert.
 * @param {string} fileName The base name for the downloaded file (without extension).
 * @param {'pdf' | 'docx'} format The desired output format.
 */
export const generateDocument = async (
    element: HTMLElement, 
    fileName: string, 
    format: 'pdf' | 'docx'
): Promise<void> => {
    // The component provides a ref to the styled element.
    if (!element) {
        throw new Error("Target element for document generation not found.");
    }
    
    switch (format) {
        case 'pdf':
            await pdfGenerator.generate(element, fileName);
            break;
        case 'docx':
            await docxGenerator.generate(element, fileName);
            break;
        default:
            throw new Error(`Unsupported document format: ${format}`);
    }
};
