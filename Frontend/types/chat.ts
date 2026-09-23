export type MessageRole = "assistant" | "user";

import type { AlternativeProduct, Product } from "@/types/product";
import type { Cart, PendingConfirmation } from "@/types/cart";

export interface ChatMessageData {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: Date;
  products?: Product[];
  alternatives?: AlternativeProduct[];
  pendingConfirmation?: PendingConfirmation | null;
  cart?: Cart | null;
  checkoutUrl?: string | null;
  isError?: boolean;
}

export interface ChatResponse {
  message: string;
  intent?: string;
  products?: Product[];
  alternatives?: AlternativeProduct[];
  pending_confirmation?: PendingConfirmation | null;
  cart?: Cart | null;
  checkout_url?: string | null;
  error?: string | null;
}