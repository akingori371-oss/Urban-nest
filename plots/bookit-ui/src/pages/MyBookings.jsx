import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorText } from "../api.js";
import MpesaPay from "./MpesaPay.jsx";

export default function MyBookings() {
  const [bookings, setBookings] = useState([]);
  const [message, setMessage] = useState("");
  const [receipts, setReceipts] = useState({});
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const res = await api("/bookings/");
      const data = await res.json();
      if (res.ok) {
        setBookings(data);
        setError("");
      } else {
        setError(errorText(data));
      }
    } catch {
      setError("Could not load bookings. Check your connection and try again.");
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(timer);
  }, [load]);

  async function act(path) {
    setMessage("");
    setError("");
    try {
      const res = await api(path, { method: "POST", body: JSON.stringify({}) });
      const data = await res.json();
      if (!res.ok) {
        setError(errorText(data));
        return;
      }
      setMessage(data.message || "Done.");
      await load();
    } catch {
      setError("The request failed. Check your connection and try again.");
    }
  }

  return (
    <div>
      <h2>My bookings</h2>
      {message && <p className="success">{message}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <div className="grid">
        {bookings.map((booking) => (
          <div className="card" key={booking.id}>
            <h3>{booking.house_name}</h3>
            <p>{booking.check_in} to {booking.check_out} · {booking.nights} night{booking.nights === 1 ? "" : "s"}</p>
            <p><strong>KES {booking.total_price}</strong> · {booking.is_long ? "Long stay" : "Short stay"}</p>
            <p>
              Status: <strong>{booking.status}</strong>
              {booking.status === "confirmed" && !booking.is_long && (booking.paid ? " · Paid" : " · Unpaid")}
            </p>
            {receipts[booking.id] && <p className="success">M-Pesa receipt: <strong>{receipts[booking.id]}</strong></p>}
            {booking.status === "confirmed" && (
              <div className="row">
                {booking.is_long ? (
                  <Link to={"/bookings/" + booking.id}>View payment card</Link>
                ) : (
                  !booking.paid && <MpesaPay bookingId={booking.id} amount={booking.total_price} onPaid={(payment) => { setReceipts((current) => ({ ...current, [booking.id]: payment.receipt })); void load(); }} />
                )}
                <button onClick={() => act("/bookings/" + booking.id + "/cancel/")}>Cancel</button>
              </div>
            )}
          </div>
        ))}
        {bookings.length === 0 && !error && <p>No bookings yet.</p>}
      </div>
    </div>
  );
}

