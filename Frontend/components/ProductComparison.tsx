import { money, type Product } from "@/lib/workspace-api";
import Icon from "./Icon";

export default function ProductComparison({
  products,
}: {
  products: Product[];
}) {
  if (products.length < 2) return null;
  const selected = products.slice(0, 2);
  const keys = Array.from(
    new Set(selected.flatMap((p) => Object.keys(p.specifications))),
  );
  const rows: { label: string; values: string[] }[] = [
    {
      label: "Производитель",
      values: selected.map(
        (p) => p.specifications["Торговая марка"] || "Нет данных",
      ),
    },
    {
      label: "Артикул",
      values: selected.map((p) => p.article || "Нет данных"),
    },
    {
      label: "Цена",
      values: selected.map((p) => (p.price === null ? "Нет данных" : money(p))),
    },
    {
      label: "Наличие",
      values: selected.map((p) =>
        p.stock === null ? "Нет данных" : `${p.stock} ед.`,
      ),
    },
    ...keys
      .filter((key) => key !== "Торговая марка")
      .map((key) => ({
        label: key,
        values: selected.map((p) => p.specifications[key] || "Нет данных"),
      })),
    {
      label: "Сертификаты",
      values: selected.map((p) =>
        p.certificates.length
          ? `${p.certificates.length} документов`
          : "Нет данных",
      ),
    },
  ];
  return (
    <section className="comparison-panel">
      <h3>
        <Icon name="grid" size={18} /> Сравнение по данным каталога
      </h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Параметр</th>
              {selected.map((p) => (
                <th key={p.id}>
                  {p.name}
                  <small>
                    {p.source === "demo_catalog"
                      ? "Учебный каталог"
                      : "Каталог EKT"}
                  </small>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.label}
                className={row.values[0] !== row.values[1] ? "different" : ""}
              >
                <th>{row.label}</th>
                {row.values.map((value, i) => (
                  <td key={i}>{value}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>
        Подсвечены различия. Отсутствующие сведения нельзя считать совпадением
        или преимуществом.
      </p>
    </section>
  );
}
