import EktWorkspace from "@/components/EktWorkspace";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ mode?: string }>;
}) {
  const { mode } = await searchParams;
  return <EktWorkspace mode={mode === "demo" ? "demo" : "live"} />;
}
