import { useEffect, useRef, useState } from "react";
import { api, errorText } from "../Api.js";
import { formatKsh } from "../apartmentDisplay.js";
import { maskKenyanPhone, normalizeKenyanPhone } from "../mpesaPhone.js";

const POLL_INTERVAL_MS = 5000;
const POLL_TIMEOUT_MS = 120000;
const PAYMENT_INITIATION_TIMEOUT_MS = 70000; // 30s OAuth + 30s STK request, with response overhead.

async function responseData(response) {
  try { return await response.json(); } catch { return null; }
}

export default function MpesaPay({ periodId, bookingId, amount, onPaid }) {
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [paymentId, setPaymentId] = useState(null);
  const [pending, setPending] = useState(false);
  const [initiationUncertain, setInitiationUncertain] = useState(false);
  const [maskedPaymentPhone, setMaskedPaymentPhone] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [receipt, setReceipt] = useState("");
  const [error, setError] = useState("");
  const onPaidRef = useRef(onPaid);
  const submittingRef = useRef(false);

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
        setInitiationUncertain(true);
        setStatusMessage("Confirmation is taking longer than expected. Do not start another payment yet; check this booking or contact support.");
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
          setInitiationUncertain(false);
          setError("");
          setReceipt(data.receipt || "");
          setMaskedPaymentPhone(data.phone || "");
          setStatusMessage("Payment confirmed.");
          onPaidRef.current?.(data);
          return;
        } else if (data.status === "failed" || data.status === "cancelled" || data.status === "review") {
          setPending(false);
          setInitiationUncertain(false);
          setError(data.result_description || (data.status === "cancelled"
            ? "The M-Pesa request was cancelled."
            : data.status === "review" ? "Payment needs manual review." : "Payment failed. You can retry."));
          return;
        } else if (data.status === "uncertain" && data.initiation_uncertain) {
          setPending(false);
          setInitiationUncertain(true);
          setStatusMessage("This attempt has no CheckoutRequestID, so Safaricom cannot query it. Do not pay again until it has been reconciled.");
          return;
        } else {
          setError("");
          if (data.callback_reconciliation_pending) {
            setInitiationUncertain(true);
            setStatusMessage(data.callback_result_code === 9999
              ? "M-Pesa reported an error sending the payment request to your phone. We are verifying the result; do not start another payment yet."
              : "M-Pesa sent a status update that is still being verified. Do not start another payment yet.");
          } else if (data.status === "uncertain") {
            setStatusMessage("The STK response was incomplete. Checking its status with Safaricom; do not start another payment.");
          } else {
            setInitiationUncertain(false);
            setStatusMessage("Check your phone. An M-Pesa payment request has been sent. Enter your M-Pesa PIN on your phone to continue.");
          }
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
    if (submittingRef.current || pending || initiationUncertain) return;
    setError("");
    setStatusMessage("");
    setReceipt("");
    setMaskedPaymentPhone("");
    const normalizedPhone = normalizeKenyanPhone(phone);
    if (!normalizedPhone) {
      setError("Enter a valid Kenyan phone number, for example 0712345678.");
      return;
    }
    submittingRef.current = true;
    setSubmitting(true);
    try {
      const kind = periodId ? "period" : "booking";
      const targetId = periodId || bookingId;
      const response = await api("/pay/" + kind + "/" + targetId + "/", {
        method: "POST",
        body: JSON.stringify({ phone: normalizedPhone }),
        timeoutMs: PAYMENT_INITIATION_TIMEOUT_MS,
      });
      const data = await responseData(response);
      if (!response.ok) {
        if (response.status === 0 || data?.outcome_uncertain === true || (response.status >= 500 && data?.outcome_uncertain !== false)) {
          setInitiationUncertain(true);
          setError("");
          setStatusMessage("We could not confirm whether M-Pesa received this request. Do not try paying again; check this booking or contact support before another attempt.");
        } else {
          setError(errorText(data));
        }
        return;
      }
      setPaymentId(data.id);
      setMaskedPaymentPhone(data.phone || maskKenyanPhone(normalizedPhone));
      if (data.status === "success") {
        setReceipt(data.receipt || "");
        setStatusMessage("Payment confirmed.");
        onPaidRef.current?.(data);
      } else if (data.status === "pending" || data.status === "uncertain") {
        const uncertainWithoutId = Boolean(data.initiation_uncertain);
        setInitiationUncertain(uncertainWithoutId);
        setPending(!uncertainWithoutId);
        setStatusMessage(uncertainWithoutId
          ? "This attempt has no CheckoutRequestID, so Safaricom cannot query it. Do not pay again until it has been reconciled."
          : data.stk_accepted
            ? "Check your phone. An M-Pesa payment request has been sent. Enter your M-Pesa PIN on your phone to continue."
            : "The STK response was incomplete. Checking its status with Safaricom; do not start another payment.");
      } else if (data.status === "failed" || data.status === "cancelled" || data.status === "review") {
        setError(data.result_description || "Payment did not complete.");
      }
    } catch {
      setInitiationUncertain(true);
      setError("");
      setStatusMessage("We could not confirm whether M-Pesa received this request. Do not try paying again; check this booking or contact support before another attempt.");
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  const statusLabel = initiationUncertain ? "Uncertain — reconciliation required"
    : pending ? "Awaiting M-Pesa confirmation"
      : receipt ? "Successful"
        : error ? "Not completed" : "Ready";

  return (
    <form className="mt-4 grid gap-3" onSubmit={handleSubmit}>
      <div className="rounded-xl border border-line bg-nest-50 p-3 text-sm text-ink">
        <p><strong>Amount:</strong> KSh {formatKsh(amount)}</p>
        {maskedPaymentPhone && <p className="mt-1"><strong>Request sent to:</strong> {maskedPaymentPhone}</p>}
        <p className="mt-1"><strong>Payment status:</strong> {statusLabel}</p>
      </div>
      <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-muted">
        M-Pesa phone number
        <input className="min-h-11 rounded-xl border border-line bg-white px-3 text-sm font-normal normal-case tracking-normal text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100 disabled:bg-nest-50" type="tel" inputMode="numeric" autoComplete="tel" placeholder="0712345678"
          value={phone} onChange={(event) => setPhone(event.target.value)}
          disabled={submitting || pending || initiationUncertain} required />
      </label>
      <button className="rounded-xl bg-nest-800 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-nest-900 disabled:cursor-wait disabled:opacity-60" type="submit" disabled={submitting || pending || initiationUncertain}>
        {submitting ? "Sending request..." : initiationUncertain ? "Payment outcome uncertain" : pending ? "Awaiting confirmation..." : "Pay KSh " + formatKsh(amount)}
      </button>
      {submitting && <p className="flex items-center gap-2 text-sm text-muted" role="status"><span className="h-4 w-4 animate-spin rounded-full border-2 border-nest-700 border-r-transparent" />Contacting M-Pesa securely…</p>}
      {pending && !initiationUncertain && <p className="flex items-center gap-2 text-sm text-muted" role="status"><span className="h-4 w-4 animate-spin rounded-full border-2 border-nest-700 border-r-transparent" />Waiting for M-Pesa confirmation…</p>}
      {statusMessage && <p className={`rounded-xl border p-3 text-sm ${initiationUncertain ? "border-amber-200 bg-amber-50 text-amber-900" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`} role="status" aria-live="polite">{statusMessage}</p>}
      {receipt && <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">M-Pesa receipt: <strong>{receipt}</strong></p>}
      {error && <p className="rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}
    </form>
  );
}

