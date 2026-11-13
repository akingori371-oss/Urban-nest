import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorText } from "../api.js";


export default function BookingCard() {
  const { id } = useParams();
  const [periods, setPeriods] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const res = await api(`/bookings/${id}/periods/`);
    const data = await res.json();
    if (res.ok) setPeriods(data);
    else setError(errorText(data));
  }

  useEffect(() => {
    load();
  }, [id]);

  function paid(data) {
    setError("");
    setMessage(`Payment received. M-Pesa receipt: ${data.receipt}`);
    load();
  }

  const total = periods.reduce((sum, p) => sum + Number(p.amount), 0);
  const paidTotal = periods.filter((p) => p.paid).reduce((sum, p) => sum + Number(p.amount), 0);

  return (
    <div>
      <p><Link to="/bookings">← Back to my bookings</Link></p>
      <h2>Payment card</h2>
      <p>
        Total KES {total.toFixed(2)} · Paid KES {paidTotal.toFixed(2)} · Outstanding KES {(total - paidTotal).toFixed(2)}
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
              <p className="success">Paid</p>
            ) : (
              <div className="row">
                <MpesaPay kind="period" id={p.id} amount={p.amount} onPaid={paid} />
              </div>
            )}
          </div>
        ))}
        {periods.length === 0 && !error && <p>No payment periods. This is a short stay.</p>}
      </div>
    </div>
  );
}