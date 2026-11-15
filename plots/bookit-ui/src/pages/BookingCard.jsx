import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorText } from "../Api.js";
import { formatKsh } from "../apartmentDisplay.js";
import MpesaPay from "./MpesaPay.jsx";


export default function BookingCard() {
  const { id } = useParams();
  const [periods, setPeriods] = useState([]);
  const [message, setMessage] = useState("");
  const [receipts, setReceipts] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api(`/bookings/${id}/periods/`);
      const data = await res.json();
      if (!res.ok) setError(errorText(data));
      else if (!Array.isArray(data)) setError("The server returned an unexpected payment periods response.");
      else { setPeriods(data); setError(""); }
    } catch {
      setError("Could not refresh payment periods. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    const timer = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(timer);
  }, [load]);

  function paid(payment) {
    setError("");
    setMessage("Payment confirmed.");
    if (payment.receipt) setReceipts((current) => ({ ...current, [payment.period]: payment.receipt }));
    void load();
  }

  const total = periods.reduce((sum, p) => sum + Number(p.amount), 0);
  const paidTotal = periods.filter((p) => p.paid).reduce((sum, p) => sum + Number(p.amount), 0);

  return (
    <div>
      <p className="mb-5"><Link className="text-sm font-semibold text-nest-700 hover:text-nest-900" to="/bookings">← Back to my stays</Link></p>
      <header className="mb-6 rounded-2xl bg-nest-900 p-6 text-white sm:p-8"><p className="text-xs font-bold uppercase tracking-[.18em] text-nest-300">LONG STAY PAYMENTS</p><h1 className="mt-2 text-3xl font-semibold text-white">Payment card</h1>
      <p className="mt-3 text-sm text-white/70">
        Total KSh {formatKsh(total)} · Paid KSh {formatKsh(paidTotal)} · Outstanding KSh {formatKsh(total - paidTotal)}
      </p></header>

      {message && <p className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800">{message}</p>}
      {error && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      {loading && <p className="py-6 text-muted" role="status">Loading payment periods…</p>}
      {error && !loading && <button className="mb-4 rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink" onClick={() => void load()}>Try again</button>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {!loading && periods.map((p) => (
          <div className="rounded-2xl border border-line bg-white p-5 shadow-sm" key={p.id}>
            <h2 className="font-semibold text-ink">Period {p.number}</h2>
            <p className="mt-2 text-sm text-muted">{p.start} to {p.end}</p>
            <p className="mt-3 text-lg font-semibold text-ink">KSh {formatKsh(p.amount)}</p>
            {p.paid ? (
              <div><p className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">Paid</p>{receipts[p.id] && <p className="text-sm text-muted">M-Pesa receipt: <strong>{receipts[p.id]}</strong></p>}</div>
            ) : (
              <div className="mt-3">
                <MpesaPay periodId={p.id} bookingId={id} amount={p.amount} onPaid={paid} />
              </div>
            )}
          </div>
        ))}
        {!loading && periods.length === 0 && !error && <p>No payment periods. This is a short stay.</p>}
      </div>
    </div>
  );
}

