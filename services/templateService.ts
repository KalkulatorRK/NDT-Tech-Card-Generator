// This service can be used to manage different templates for tech cards.
// For example, templates for different control methods or normative documents.

export interface Template {
    id: string;
    name: string;
    defaultValues: Record<string, any>;
}

const templates: Template[] = [
    {
        id: 'gost_7512_radiographic',
        name: 'ГОСТ 7512 - Радиографический контроль',
        defaultValues: {
            normativeDocument: 'ГОСТ 7512-82',
            controlMethod: 'Радиографический',
            sensitivity: 'Класс 2 по ГОСТ 7512',
        }
    },
    {
        id: 'gost_14782_ultrasonic',
        name: 'ГОСТ 14782 - Ультразвуковой контроль',
        defaultValues: {
            normativeDocument: 'ГОСТ 14782-86',
            controlMethod: 'Ультразвуковой',
            sensitivity: 'Уровень А',
        }
    }
];

export const getTemplates = (): Template[] => {
    return templates;
};

export const getTemplateById = (id: string): Template | undefined => {
    return templates.find(t => t.id === id);
};
