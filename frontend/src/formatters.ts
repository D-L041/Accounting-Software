export const money = (value: unknown, currency = "KES") => new Intl.NumberFormat("en-KE", { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(value || 0));

/**
 * Return today's date in the school's operating timezone.
 * Using UTC ISO dates can select yesterday for users in East Africa
 * during the first three hours after local midnight.
 */
export const schoolToday = (now: Date = new Date(), timeZone = "Africa/Nairobi") => {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const value = (type: string) => parts.find(part => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
};
