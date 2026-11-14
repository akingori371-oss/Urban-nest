import { useEffect, useRef, useState } from "react";
import { api, errorText } from "../api.js";

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
    <form onSubmit={handleSubmit}>
      <label>
        M-Pesa phone number
        <input type="tel" inputMode="numeric" autoComplete="tel" placeholder="0712345678"
          value={phone} onChange={(event) => setPhone(event.target.value)}
          disabled={submitting || pending} required />
      </label>
      <button type="submit" disabled={submitting || pending}>
        {submitting ? "Sending request..." : pending ? "Awaiting confirmation..." : "Pay KES " + amount}
      </button>
      {statusMessage && <p className="success" role="status" aria-live="polite">{statusMessage}</p>}
      {receipt && <p className="success">M-Pesa receipt: <strong>{receipt}</strong></p>}
      {error && <p className="error" role="alert">{error}</p>}
    </form>
  );
}

