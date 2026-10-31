export const money = (value: unknown, currency = "KES") => new Intl.NumberFormat("en-KE", { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(value || 0));
