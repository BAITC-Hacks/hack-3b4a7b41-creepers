import type { Cart, PendingConfirmation } from "@/types/cart";
import type { ChatResponse } from "@/types/chat";
import type { Product } from "@/types/product";

const DEFAULT_API_URL = "http://localhost:8000";
const REQUEST_TIMEOUT = 15_000;

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const isMockMode = () => process.env.NEXT_PUBLIC_USE_MOCKS !== "false";

function apiUrl(path: string) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

  try {
    const response = await fetch(apiUrl(path), {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...init.headers },
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      throw new ApiError(body?.detail || body?.error || "Сервер временно недоступен.", response.status);
    }
    return body as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Сервер не ответил вовремя. Попробуйте ещё раз.");
    }
    throw new ApiError("Не удалось подключиться к AI-ассистенту. Проверьте, запущен ли backend.");
  } finally {
    window.clearTimeout(timeout);
  }
}

const demoProduct: Product = {
  id: "demo-515291",
  name: "Автоматический выключатель 25А",
  article: "515291",
  category: "Модульная автоматика",
  price: 4500,
  currency: "₸",
  stock: 12,
  available: true,
  specifications: { "Номинальный ток": "25 А", "Количество полюсов": 1, Тип: "C" },
};

const mockResponse = (message: string): ChatResponse => {
  const normalized = message.toLowerCase();
  if (normalized.includes("отсутств") || normalized.includes("аналог")) {
    return {
      message: "Товар отсутствует. Мы нашли возможную альтернативу по категории и основным характеристикам.",
      alternatives: [{ ...demoProduct, id: "demo-alternative", name: "Автоматический выключатель 25А IEK", stock: 7, reason: "Похожая категория и сопоставимые основные характеристики." }],
    };
  }
  if (normalized.includes("добав") || normalized.includes("корзин")) {
    return { message: "Подтвердите добавление товара в корзину.", products: [demoProduct], pending_confirmation: { product: demoProduct, product_id: demoProduct.id, quantity: 5, available_stock: 12 } };
  }
  if (normalized.includes("характер") || normalized.includes("сертифик") || normalized.includes("налич")) {
    return { message: "Нашёл подходящий товар. В наличии 12 шт. Ниже доступны характеристики и данные о товаре.", products: [demoProduct] };
  }
  return { message: "Нашёл подходящий товар по вашему запросу.", products: [demoProduct] };
};

export async function sendChatMessage(sessionId: string, message: string): Promise<ChatResponse> {
  if (isMockMode()) return new Promise((resolve) => window.setTimeout(() => resolve(mockResponse(message)), 500));
  return request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify({ session_id: sessionId, message }) });
}

export async function prepareCart(sessionId: string, productId: string, quantity: number): Promise<PendingConfirmation> {
  if (isMockMode()) return { product: demoProduct, product_id: productId, quantity, available_stock: demoProduct.stock };
  return request<PendingConfirmation>("/api/cart/prepare", { method: "POST", body: JSON.stringify({ session_id: sessionId, product_id: productId, quantity }) });
}

export async function confirmCart(sessionId: string, confirmation: PendingConfirmation): Promise<{ cart?: Cart | null; checkout_url?: string | null; message?: string }> {
  if (isMockMode()) return { message: "Товар добавлен в корзину.", cart: { session_id: sessionId, items: [{ product: demoProduct, product_id: demoProduct.id, quantity: confirmation.quantity, unit_price: demoProduct.price, total_price: (demoProduct.price || 0) * confirmation.quantity }], total: (demoProduct.price || 0) * confirmation.quantity, currency: "₸", checkout_url: "http://localhost:3000/cart/demo" }, checkout_url: "http://localhost:3000/cart/demo" };
  return request("/api/cart/confirm", { method: "POST", body: JSON.stringify({ session_id: sessionId, product_id: confirmation.product_id, quantity: confirmation.quantity, confirmed: true }) });
}

export async function getCart(sessionId: string): Promise<Cart> {
  if (isMockMode()) return { session_id: sessionId, items: [] };
  return request<Cart>(`/api/cart/${encodeURIComponent(sessionId)}`);
}

export async function searchProducts(query: string): Promise<Product[]> {
  return request<Product[]>(`/api/products/search?q=${encodeURIComponent(query)}`);
}

export async function getProduct(id: string): Promise<Product> {
  return request<Product>(`/api/products/${encodeURIComponent(id)}`);
}