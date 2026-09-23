import PurchaseCart from "@/components/PurchaseCart";

export default async function CartPage({
  params,
  searchParams,
}: {
  params: Promise<{ session_id: string }>;
  searchParams: Promise<{ mode?: string }>;
}) {
  const { session_id } = await params;
  const { mode } = await searchParams;
  return (
    <PurchaseCart
      session={session_id}
      mode={mode === "demo" ? "demo" : "live"}
    />
  );
}
