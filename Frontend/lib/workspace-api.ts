export type Mode = "live" | "demo";
export type Product = {
  id: string;
  article: string | null;
  name: string;
  category: string | null;
  description: string | null;
  image_url: string | null;
  product_url: string | null;
  specifications: Record<string, string>;
  certificates: string[];
  price: string | number | null;
  currency: string | null;
  stock: string | number | null;
  availability: "in_stock" | "out_of_stock" | "unknown";
  data_warnings: string[];
};
export type Cart = {
  items: { product: Product; quantity: number }[];
  total_items: number;
  checkout_url: string;
};
export type Pending = {
  product: Product;
  quantity: number;
  available_stock: string;
  message: string;
};
export type Reply = {
  intent: string;
  message: string;
  products: Product[];
  alternatives: { product: Product; reason: string }[];
  pending_confirmation: Pending | null;
  cart: Cart | null;
  error: { code: string; message: string } | null;
};
export type Status = {
  mode: Mode;
  catalog_configured: boolean;
  language_model_configured: boolean;
  policies: Record<string, string>;
  policy_source: string;
  policy_checked_at: string;
};
export async function api<T>(
  mode: Mode,
  path: string,
  body?: unknown,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const isFile = body instanceof FormData;
    const response = await fetch(
      `/backend${mode === "demo" ? "/demo" : ""}/api${path}`,
      {
        method: body === undefined ? "GET" : "POST",
        signal: controller.signal,
        cache: "no-store",
        headers:
          body !== undefined && !isFile
            ? { "Content-Type": "application/json" }
            : {},
        body:
          body === undefined ? undefined : isFile ? body : JSON.stringify(body),
      },
    );
    const data = await response.json().catch(() => null);
    if (!response.ok)
      throw new Error(
        data?.error?.message ||
          "Не удалось получить ответ. Проверьте подключение к backend.",
      );
    return data as T;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError")
      throw new Error("Ответ занимает больше 30 секунд. Повторите запрос.");
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
export function money(product: Product): string {
  if (product.price === null) return "Цена по запросу";
  return `${Number(product.price).toLocaleString("ru-RU")} ${product.currency === "KZT" ? "₸" : product.currency || "· валюта не указана"}`;
}
export function cartLink(session: string, mode: Mode): string {
  return `/cart/${encodeURIComponent(session)}?mode=${mode}`;
}
export function sessionFor(mode: Mode): string {
  const key = `ekt-workspace-${mode}`;
  const existing = localStorage.getItem(key);
  if (existing && /^[a-f0-9-]{36}$/.test(existing)) return existing;
  const session = crypto.randomUUID();
  localStorage.setItem(key, session);
  return session;
}
export function safeLink(url: string): string | undefined {
  try {
    const parsed = new URL(
      url,
      typeof window !== "undefined"
        ? window.location.origin
        : "http://localhost:3000",
    );
    return ["https:", "http:"].includes(parsed.protocol) &&
      !parsed.username &&
      !parsed.password
      ? parsed.href
      : undefined;
  } catch {
    return undefined;
  }
}
