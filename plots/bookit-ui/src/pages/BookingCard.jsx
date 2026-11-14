import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorText } from "../api.js";
import MpesaPay from "./MpesaPay.jsx";


export default function BookingCard() {
  const { id } = useParams();
  const [periods, setPeriods] = useState([]);
  const [message, setMessage] = useState("");
  const [receipts, setReceipts] = useState({});
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const res = await api(`/bookings/${id}/periods/`);
      const data = await res.json();
      if (res.ok) setPeriods(data);
      else setError(errorText(data));
    } catch {
      setError("Could not refresh payment periods. Check your connection and try again.");
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
      <p><Link to="/bookings">â† Back to my bookings</Link></p>
      <h2>Payment card</h2>
      <p>
        Total KES {total.toFixed(2)} Â· Paid KES {paidTotal.toFixed(2)} Â· Outstanding KES {(total - paidTotal).toFixed(2)}
      </p>

      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="grid">
        {periods.map((p) => (
          <div className="card" key={p.id}>
            <h3>Period {p.number}</h3>
            <p>{p.start} to {p.end}</p>
            <p><strong>KES {p.amount}</strong></p>
            {p.paid ? (
              <div><p className="success">Paid</p>{receipts[p.id] && <p>M-Pesa receipt: <strong>{receipts[p.id]}</strong></p>}</div>
            ) : (
              <div className="row">
                <MpesaPay periodId={p.id} bookingId={id} amount={p.amount} onPaid={paid} />
              </div>
            )}
          </div>
        ))}
        {periods.length === 0 && !error && <p>No payment periods. This is a short stay.</p>}
      </div>
    </div>
  );
}

