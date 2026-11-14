import { useCallback, useEffect, useState } from "react";
import { api, errorText } from "../api.js";

export default function Houses() {
  const [houses, setHouses] = useState([]);
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    const query = checkIn && checkOut ? `?check_in=${checkIn}&check_out=${checkOut}` : "";
    const res = await api("/houses/" + query);
    const data = await res.json();
    if (!res.ok) {
      setHouses([]);
      setError(errorText(data));
      return;
    }
    setHouses(data);
  }, [checkIn, checkOut]);

  useEffect(() => {
    const timer = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(timer);
  }, [load]);

  async function book(houseId) {
    setMessage("");
    setError("");
    if (!checkIn || !checkOut) {
      setError("Pick check-in and check-out dates first.");
      return;
    }
    const res = await api("/bookings/", {
      method: "POST",
      body: JSON.stringify({ house: houseId, check_in: checkIn, check_out: checkOut }),
    });
    const data = await res.json();
    if (!res.ok) {
      setError(errorText(data));
      return;
    }
    setMessage(`Booked! Booking id ${data.id}, total ${data.total_price}.`);
    load();
  }

  return (
    <div>
      <h2>Find a free house</h2>
      <div className="row">
        <label>Check-in <input type="date" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} /></label>
        <label>Check-out <input type="date" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} /></label>
        <button onClick={load}>Search</button>
      </div>

      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="grid">
        {houses.map((h) => (
          <div className="card" key={h.id}>
            <h3>{h.name}</h3>
            <p>{h.location} Â· {h.bedrooms} bedroom{h.bedrooms === 1 ? "" : "s"}</p>
            <p>
              {h.avg_rating ? `â˜… ${h.avg_rating.toFixed(1)} (${h.review_count})` : "No reviews yet"}
            </p>
            <p><strong>${h.price_per_night}</strong> / night</p>
            <button onClick={() => book(h.id)}>Book</button>
          </div>
        ))}
        {houses.length === 0 && !error && <p>No houses to show.</p>}
      </div>
    </div>
  );
}
