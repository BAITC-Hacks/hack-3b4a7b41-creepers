export type SpecificationValue = string | number | boolean | null;

export interface Product {
  id: string;
  name: string;
  article?: string | null;
  category?: string | null;
  description?: string | null;
  price?: number | null;
  currency?: string | null;
  stock?: number | null;
  available?: boolean | null;
  availability?: string | null;
  specifications?: Record<string, SpecificationValue> | null;
  certificateUrl?: string | null;
  certificate_url?: string | null;
  imageUrl?: string | null;
  image_url?: string | null;
}

export interface AlternativeProduct extends Product {
  reason?: string | null;
}