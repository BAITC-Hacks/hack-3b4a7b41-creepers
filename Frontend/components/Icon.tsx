export type IconName =
  | "spark"
  | "chat"
  | "grid"
  | "cart"
  | "file"
  | "arrow"
  | "plus"
  | "check"
  | "close"
  | "search"
  | "box"
  | "shield"
  | "truck"
  | "card"
  | "download"
  | "link"
  | "bolt";
const paths: Record<IconName, string> = {
  spark: "m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4L12 3Z",
  chat: "M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5A8.5 8.5 0 0 1 10.5 3h2A8.5 8.5 0 0 1 21 11.5ZM7 9h9M7 13h6",
  grid: "M3 3h7v7H3V3Zm11 0h7v7h-7V3ZM3 14h7v7H3v-7Zm11 0h7v7h-7v-7Z",
  cart: "M2 3h3l3 12h11l3-9H6M9 20h.01M18 20h.01",
  file: "M14 2H5v20h14V7l-5-5Zm0 0v6h5M8 12h8M8 16h6",
  arrow: "M5 12h14m-6-6 6 6-6 6",
  plus: "M12 5v14M5 12h14",
  check: "m5 12 4 4L19 6",
  close: "m6 6 12 12M6 18 18 6",
  search: "M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z",
  box: "m12 2 9 5v10l-9 5-9-5V7l9-5ZM3 7l9 5 9-5M12 12v10M7 4.5l9 5",
  shield: "m12 2 8 3v6c0 6-8 11-8 11S4 17 4 11V5l8-3Zm-4 9 3 3 5-6",
  truck:
    "M1 4h13v13H1V4Zm13 5h4l4 5v3h-8M5 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm13 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
  card: "M2 5h20v14H2V5Zm0 5h20M5 15h4",
  download: "M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5",
  link: "M14 3h7v7m0-7L10 14M10 3H3v18h18v-7",
  bolt: "m13 2-9 12h7l-1 8 10-13h-8l1-7Z",
};
export default function Icon({
  name,
  size = 20,
}: {
  name: IconName;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}
