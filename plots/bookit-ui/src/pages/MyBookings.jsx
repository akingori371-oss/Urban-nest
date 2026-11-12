import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorText } from "../api.js";

export default function MyBookings() {
  const [bookings, setBookings] = useState([]);
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const res = await api("/bookings/");
    const data = await res.json();
    if (res.ok) setBookings(data);
    else setError(errorText(data));
  }

  useEffect(() => {
    load();
  }, []);

  // One helper for the Cancel and Pay buttons.
  async function act(path, body) {
    setMessage("");
    setError("");
    const res = await api(path, { method: "POST", body: JSON.stringify(body || {}) });
    const data = await res.json();
    if (!res.ok) {
      setError(errorText(data));
      return;
    }
    setMessage(data.message || "Done.");
    load();
  }

  function pay(id) {
    if (!phone) {
      setError("Enter your M-Pesa phone number first, for example 0712345678.");
      return;
    }
    act(`/pay/booking/${id}/`, { phone });
  }

  return (
    <div>
      <h2>My bookings</h2>

      <div className="row">
        <label>
          M-Pesa phone number
          <input placeholder="0712345678" value={phone} onChange={(e) => setPhone(e.target.value)} />
        </label>
      </div>

      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="grid">
        {bookings.map((b) => (
          <div className="card" key={b.id}>
            <h3>{b.house_name}</h3>
            <p>{b.check_in} to {b.check_out} · {b.nights} night{b.nights === 1 ? "" : "s"}</p>
            <p><strong>${b.total_price}</strong> · {b.is_long ? "Long stay" : "Short stay"}</p>
            <p>
              Status: <strong>{b.status}</strong>
              {b.status === "confirmed" && !b.is_long && (b.paid ? " · Paid" : " · Unpaid")}
            </p>

            {b.status === "confirmed" && (
              <div className="row">
                {b.is_long ? (
                  <Link to={`/bookings/${b.id}`}>View payment card</Link>
                ) : (
                  !b.paid && <button onClick={() => pay(b.id)}>Pay</button>
                )}
                <button onClick={() => act(`/bookings/${b.id}/cancel/`)}>Cancel</button>
              </div>
            )}
          </div>
        ))}
        {bookings.length === 0 && !error && <p>No bookings yet.</p>}
      </div>
    </div>
  );
}