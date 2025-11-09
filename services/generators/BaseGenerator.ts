
export interface Generator {
    generate(element: HTMLElement, fileName: string): Promise<void>;
}
