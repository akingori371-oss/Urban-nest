export function normalizeKenyanPhone(value) {
  if (typeof value !== "string" || !/^\+?[\d\s().-]+$/.test(value.trim())) return null;
  let phone = value.replace(/\D/g, "");
  if (phone.startsWith("0")) phone = "254" + phone.slice(1);
  return /^254[71]\d{8}$/.test(phone) ? phone : null;
}

export function maskKenyanPhone(value) {
  return value ? `*******${value.slice(-4)}` : "";
}
