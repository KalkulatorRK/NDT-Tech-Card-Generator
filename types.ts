export enum Page {
  Home = 'HOME',
  CreateTechCard = 'CREATE_TECH_CARD',
  QualityAssessment = 'QUALITY_ASSESSMENT',
  Dashboard = 'DASHBOARD',
}

export interface TechCardFormData {
  customer: string;
  facility: string;
  weldConnectionNumber: string;
  controlObject: string;
  normativeDocument: string;
  weldType: string;
  thickness: string;
  diameter: string;
  controlMethod: string;
  qualityLevel: string;
  sensitivity: string;
  equipment: string[];
}

export interface TechCardData extends TechCardFormData {
  controlProcedure: string;
  acceptanceCriteria: string;
  personnelRequirements: string;
  safetyPrecautions: string;
}

export interface Defect {
  id: string;
  type: string;
  size: string;
}
