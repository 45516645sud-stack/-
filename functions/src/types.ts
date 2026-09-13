export type ItemCategory = "pill" | "battery" | "unknown";

// Flutter 클라이언트의 ItemModel.fromJson과 1:1로 대응하는 응답 형태.
export interface IdentifyResult {
  matched: boolean;
  category: ItemCategory;
  name: string;
  description: string;
  disposalSteps: string[];
  precautions: string[];
  imageUrl?: string;
  confidence?: number;
}
