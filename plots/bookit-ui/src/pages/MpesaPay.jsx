import { useEffect, useRef, useState } from "react";
import { api, errorText } from "../api.js";

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 120000;

function normalizeKenyanPhone(value) {
  let phone = value.replace(/\D/g, "");
  if (phone.startsWith("0")) phone = `254${phone.slice(1)}`;
  return /^254\d{9}$/.test(phone) ? phone : null;
}

async function responseData(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export default function MpesaPay({ periodId, bookingId, amount, onPaid }) {
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [pending, setPending] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState("");
  const onPaidRef = useRef(onPaid);

  useEffect(() => {
    onPaidRef.current = onPaid;
  }, [onPaid]);

  useEffect(() => {
    if (!pending) return undefined;

    let active = true;
    let timer;
    let controller;
    const startedAt = Date.now();

    async function checkPayment() {
      if (!active) return;

      if (Date.now() - startedAt >= POLL_TIMEOUT_MS) {
        setStatusMessage(
          "Payment confirmation is still pending. You can check this booking again later."
        );
        return;
      }

      controller = new AbortController();

      try {
        const response = await api(`/bookings/${bookingId}/periods/`, {
          signal: controller.signal,
        });
        const data = await responseData(response);

        if (!active) return;

        if (!response.ok || !Array.isArray(data)) {
          setError(errorText(data) || "Could not check payment status. Retrying...");
        } else {
          const period = data.find((item) => item.id === Number(periodId));
          setError("");

          if (period?.paid) {
            setPending(false);
            setStatusMessage(`Payment confirmed for period ${period.number}.`);
            onPaidRef.current?.(period);
            return;
          }
        }
      } catch (requestError) {
        if (!active || requestError.name === "AbortError") return;
        setError("Unable to check payment status right now. Retrying...");
      }

      if (active) {
        timer = setTimeout(checkPayment, POLL_INTERVAL_MS);
      }
    }

    timer = setTimeout(checkPayment, POLL_INTERVAL_MS);

    return () => {
      active = false;
      clearTimeout(timer);
      controller?.abort();
    };
  }, [pending, bookingId, periodId]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting || pending) return;

    setError("");
    setStatusMessage("");

    const normalizedPhone = normalizeKenyanPhone(phone.trim());
    if (!normalizedPhone) {
      setError("Enter a valid Kenyan phone number, for example 0712345678.");
      return;
    }

    setSubmitting(true);

    try {
      const response = await api(`/pay/period/${periodId}/`, {
        method: "POST",
        body: JSON.stringify({ phone: normalizedPhone }),
      });
      const data = await responseData(response);

      if (!response.ok) {
        setError(errorText(data));
        return;
      }

      if (data?.status !== "pending") {
        setError("The payment request did not return a pending status.");
        return;
      }

      setStatusMessage(data.message || "STK Push sent. Waiting for payment confirmation.");
      setPending(true);
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
        <input
          type="tel"
          inputMode="numeric"
          autoComplete="tel"
          placeholder="0712345678"
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
          disabled={submitting || pending}
          required
        />
      </label>
      <button type="submit" disabled={submitting || pending}>
        {submitting ? "Sending request..." : pending ? "Awaiting confirmation..." : `Pay KES ${amount}`}
      </button>
      {statusMessage && (
        <p className="success" role="status" aria-live="polite">
          {pending ? `Pending: ${statusMessage}` : statusMessage}
        </p>
      )}
      {error && <p className="error" role="alert">{error}</p>}
    </form>
  );
}
