
/**
 * Clones a DOM node and applies all computed styles as inline styles.
 * This is necessary for libraries like html-to-docx that don't process external or embedded CSS.
 * @param {HTMLElement} node The DOM node to process.
 * @returns {Promise<string>} A promise that resolves with the HTML string of the cloned node with inlined styles.
 */
export const inlineStyles = async (node: HTMLElement): Promise<string> => {
    const clonedNode = node.cloneNode(true) as HTMLElement;
    
    // It's crucial to append the cloned node to the DOM to get computed styles,
    // but we can make it invisible.
    clonedNode.style.position = 'absolute';
    clonedNode.style.left = '-9999px';
    clonedNode.style.top = '-9999px';
    document.body.appendChild(clonedNode);

    const elements = [clonedNode, ...Array.from(clonedNode.querySelectorAll<HTMLElement>('*'))];

    elements.forEach(element => {
        const computedStyle = window.getComputedStyle(element);
        let styleString = '';
        for (let i = 0; i < computedStyle.length; i++) {
            const propName = computedStyle[i];
            const propValue = computedStyle.getPropertyValue(propName);
            styleString += `${propName}:${propValue};`;
        }
        element.setAttribute('style', styleString);
    });

    const html = clonedNode.outerHTML;

    // Clean up by removing the cloned node from the DOM.
    document.body.removeChild(clonedNode);

    return html;
};
