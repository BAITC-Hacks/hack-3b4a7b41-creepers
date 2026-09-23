import type { Product } from "@/types/product";

export interface PendingConfirmation {
  product?: Product | null;
  product_id?: string | null;
  quantity: number;
  available_stock?: number | null;
  available?: number | null;
  article?: string | null;
}

export interface CartItem {
  product?: Product | null;
  product_id?: string | null;
  name?: string | null;
  quantity: number;
  unit_price?: number | null;
  total_price?: number | null;
}

export interface Cart {
  session_id?: string | null;
  items?: CartItem[];
  total?: number | null;
  currency?: string | null;
  checkout_url?: string | null;
  message?: string | null;
  stock_validated?: boolean | null;
}