// This is a mock backend service.
// In a real application, this would make API calls to a server
// to save/load user data, documents, etc.

export const saveTechCard = async (techCardData: any): Promise<{ success: true, id: string }> => {
    console.log("Saving tech card to backend:", techCardData);
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 500));
    return { success: true, id: `doc_${Date.now()}` };
};

export const getUserTechCards = async (): Promise<any[]> => {
    console.log("Fetching user tech cards from backend.");
    await new Promise(resolve => setTimeout(resolve, 800));
    // Return mock data
    return [
        { id: 'doc_1', name: 'ТК № 02/11-РГК', createdAt: '2024-01-21' },
        { id: 'doc_2', name: 'ТК № 03/11-ВИК', createdAt: '2024-01-15' },
    ];
};

export const getUserProfile = async (): Promise<any> => {
    console.log("Fetching user profile.");
    await new Promise(resolve => setTimeout(resolve, 300));
    return {
        name: 'John Doe',
        availableGenerations: 3,
    };
}
