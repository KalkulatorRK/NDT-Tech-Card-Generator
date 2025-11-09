import { GoogleGenAI, Type } from "@google/genai";
import { TechCardFormData } from "../types";

// Per guidelines, initialize with API key from environment variables.
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

// A schema for the tech card generation
const techCardSchema = {
    type: Type.OBJECT,
    properties: {
        controlProcedure: {
            type: Type.STRING,
            description: "Detailed step-by-step procedure for the non-destructive testing method. Should be written in Russian.",
        },
        acceptanceCriteria: {
            type: Type.STRING,
            description: "The criteria for accepting or rejecting the weld based on the normative document. Should be written in Russian.",
        },
        personnelRequirements: {
            type: Type.STRING,
            description: "Requirements for the qualifications of the personnel performing the test. Should be written in Russian.",
        },
        safetyPrecautions: {
            type: Type.STRING,
            description: "Safety precautions to be taken during the testing process. Should be written in Russian.",
        },
    },
    required: ["controlProcedure", "acceptanceCriteria", "personnelRequirements", "safetyPrecautions"],
};


export const generateTechCardContent = async (formData: TechCardFormData): Promise<any> => {
  const prompt = `
    Создай содержимое для технологической карты неразрушающего контроля на основе следующих данных.
    Ответ должен быть в формате JSON и соответствовать предоставленной схеме.

    Заказчик: ${formData.customer}
    Объект: ${formData.facility}
    Номер сварного соединения: ${formData.weldConnectionNumber}
    Объект контроля: ${formData.controlObject}
    Нормативный документ: ${formData.normativeDocument}
    Тип сварного соединения: ${formData.weldType}
    Толщина, мм: ${formData.thickness}
    Диаметр, мм: ${formData.diameter}
    Метод контроля: ${formData.controlMethod}
    Уровень качества: ${formData.qualityLevel}
    Чувствительность: ${formData.sensitivity}
    Используемое оборудование: ${formData.equipment.join(', ')}

    Сгенерируй следующие разделы:
    - Порядок проведения контроля (controlProcedure)
    - Нормы оценки качества (acceptanceCriteria)
    - Требования к персоналу (personnelRequirements)
    - Требования по технике безопасности (safetyPrecautions)
  `;

  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-pro", // Complex text task
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: techCardSchema,
        temperature: 0.2, // Lower temperature for more deterministic results
      },
    });
    
    // Per guidelines, access text property and parse it.
    const jsonString = response.text.trim();
    return JSON.parse(jsonString);
  } catch (error) {
    console.error("Error generating tech card content:", error);
    throw new Error("Не удалось сгенерировать содержимое техкарты. Пожалуйста, попробуйте снова.");
  }
};

export const assessQuality = async (
    method: string, 
    document: string, 
    thickness: string, 
    defects: {type: string, size: string}[]
): Promise<string> => {
    const defectsString = defects.map(d => `- Тип: ${d.type}, Размер: ${d.size} мм`).join('\n');
    
    const prompt = `
        Проведи оценку качества сварного шва на основе предоставленных данных.
        Дай четкое заключение: "Годен" или "Брак".
        Обоснуй свое решение, ссылаясь на конкретные пункты нормативного документа.
        Ответ должен быть на русском языке.

        Исходные данные:
        - Метод контроля: ${method}
        - Нормативный документ: ${document}
        - Толщина стенки: ${thickness} мм
        - Обнаруженные дефекты:
        ${defectsString}
    `;

    try {
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-pro', // Advanced reasoning
            contents: prompt,
        });

        // Per guidelines, access text property directly.
        return response.text;
    } catch (error) {
        console.error("Error assessing quality:", error);
        throw new Error("Не удалось провести оценку качества. Пожалуйста, попробуйте снова.");
    }
};
