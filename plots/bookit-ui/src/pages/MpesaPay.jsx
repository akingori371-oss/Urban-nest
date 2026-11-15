import { useEffect, useRef, useState } from "react";
import { api, errorText } from "../Api.js";

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 120000;

function normalizeKenyanPhone(value) {
  let phone = value.replace(/\D/g, "");
  if (phone.startsWith("0")) phone = "254" + phone.slice(1);
  return /^254\d{9}$/.test(phone) ? phone : null;
}

async function responseData(response) {
  try { return await response.json(); } catch { return null; }
}

export default function MpesaPay({ periodId, bookingId, amount, onPaid }) {
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [paymentId, setPaymentId] = useState(null);
  const [pending, setPending] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [receipt, setReceipt] = useState("");
  const [error, setError] = useState("");
  const onPaidRef = useRef(onPaid);

  useEffect(() => { onPaidRef.current = onPaid; }, [onPaid]);

  useEffect(() => {
    if (!pending || !paymentId) return undefined;
    let active = true;
    let timer;
    let controller;
    const startedAt = Date.now();

    async function checkPayment() {
      if (!active) return;
      if (Date.now() - startedAt >= POLL_TIMEOUT_MS) {
        setPending(false);
        setStatusMessage("Confirmation is taking longer than expected. Check this booking again later.");
        return;
      }
      controller = new AbortController();
      try {
        const response = await api("/payments/" + paymentId + "/", { signal: controller.signal });
        const data = await responseData(response);
        if (!active) return;
        if (!response.ok) {
          setError(errorText(data) || "Could not check payment status.");
        } else if (data.status === "success") {
          setPending(false);
          setError("");
          setReceipt(data.receipt || "");
          setStatusMessage("Payment confirmed.");
          onPaidRef.current?.(data);
          return;
        } else if (data.status === "failed" || data.status === "review") {
          setPending(false);
          setError(data.result_description || (data.status === "review" ? "Payment needs manual review." : "Payment failed. You can retry."));
          return;
        } else {
          setError("");
          setStatusMessage("Waiting for M-Pesa confirmation.");
        }
      } catch (requestError) {
        if (!active || requestError.name === "AbortError") return;
        setError("Unable to check payment status right now. Retrying...");
      }
      if (active) timer = setTimeout(checkPayment, POLL_INTERVAL_MS);
    }

    timer = setTimeout(checkPayment, POLL_INTERVAL_MS);
    return () => {
      active = false;
      clearTimeout(timer);
      controller?.abort();
    };
  }, [pending, paymentId]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting || pending) return;
    setError("");
    setStatusMessage("");
    setReceipt("");
    const normalizedPhone = normalizeKenyanPhone(phone.trim());
    if (!normalizedPhone) {
      setError("Enter a valid Kenyan phone number, for example 0712345678.");
      return;
    }
    setSubmitting(true);
    try {
      const kind = periodId ? "period" : "booking";
      const targetId = periodId || bookingId;
      const response = await api("/pay/" + kind + "/" + targetId + "/", {
        method: "POST",
        body: JSON.stringify({ phone: normalizedPhone }),
      });
      const data = await responseData(response);
      if (!response.ok) {
        setError(errorText(data));
        return;
      }
      setPaymentId(data.id);
      if (data.status === "success") {
        setReceipt(data.receipt || "");
        setStatusMessage("Payment confirmed.");
        onPaidRef.current?.(data);
      } else if (data.status === "pending") {
        setPending(true);
        setStatusMessage("STK Push sent. Waiting for payment confirmation.");
      } else if (data.status === "failed" || data.status === "review") {
        setError(data.result_description || "Payment did not complete.");
      }
    } catch {
      setError("Could not start the M-Pesa request. Check your connection and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="mt-4 grid gap-3" onSubmit={handleSubmit}>
      <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-muted">
        M-Pesa phone number
        <input className="min-h-11 rounded-xl border border-line bg-white px-3 text-sm font-normal normal-case tracking-normal text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100 disabled:bg-nest-50" type="tel" inputMode="numeric" autoComplete="tel" placeholder="0712345678"
          value={phone} onChange={(event) => setPhone(event.target.value)}
          disabled={submitting || pending} required />
      </label>
      <button className="rounded-xl bg-nest-800 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-nest-900 disabled:cursor-wait disabled:opacity-60" type="submit" disabled={submitting || pending}>
        {submitting ? "Sending request..." : pending ? "Awaiting confirmation..." : "Pay KES " + amount}
      </button>
      {statusMessage && <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800" role="status" aria-live="polite">{statusMessage}</p>}
      {receipt && <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">M-Pesa receipt: <strong>{receipt}</strong></p>}
      {error && <p className="rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}
    </form>
  );
}

