import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, errorText } from "../api.js";

export default function HouseDetail() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const [house, setHouse] = useState(null);
  const [checkIn, setCheckIn] = useState(params.get("check_in") || "");
  const [checkOut, setCheckOut] = useState(params.get("check_out") || "");
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const query = params.toString();
      const response = await api("/houses/" + id + "/" + (query ? "?" + query : ""));
      const data = await response.json();
      if (!response.ok) throw new Error(errorText(data));
      setHouse(data);
    } catch (requestError) {
      setHouse(null);
      setError(requestError.message || "Could not load this apartment.");
    } finally {
      setLoading(false);
    }
  }, [id, params]);

  useEffect(() => {
    const timer = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(timer);
  }, [load]);

  function updateDates(event) {
    event.preventDefault();
    const next = new URLSearchParams(params);
    if (checkIn && checkOut) {
      next.set("check_in", checkIn);
      next.set("check_out", checkOut);
    } else {
      next.delete("check_in");
      next.delete("check_out");
    }
    setParams(next);
  }

  async function createBooking() {
    setError("");
    setMessage("");
    if (!checkIn || !checkOut) {
      setError("Choose check-in and check-out dates first.");
      return;
    }
    if (house?.availability === false) {
      setError("This apartment is unavailable for those dates. Choose another date range.");
      return;
    }
    setBooking(true);
    try {
      const response = await api("/bookings/", {
        method: "POST",
        body: JSON.stringify({ house: Number(id), check_in: checkIn, check_out: checkOut }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(errorText(data));
      setMessage("Booking created. Booking ID " + data.id + ".");
    } catch (requestError) {
      setError(requestError.message || "Could not create the booking.");
    } finally {
      setBooking(false);
    }
  }

  const back = "/houses" + (params.toString() ? "?" + params.toString() : "");

  return (
    <section>
      <p><Link to={back}>Back to apartments</Link></p>
      {loading && <p role="status">Loading apartment...</p>}
      {error && !house && <p className="error" role="alert">{error}</p>}
      {house && (
        <article className="card">
          <h2>{house.name}</h2>
          <p>{house.location}</p>
          <p>{house.bedrooms} bedroom{house.bedrooms === 1 ? "" : "s"}</p>
          <p><strong>KES {house.price_per_night}</strong> / night</p>
          <p>{house.description || "No description is available."}</p>
          <p>{house.avg_rating ? "★ " + house.avg_rating.toFixed(1) + " from " + house.review_count + " reviews" : "No reviews yet"}</p>

          <form className="row" onSubmit={updateDates}>
            <label>Check-in <input type="date" value={checkIn} onChange={(event) => setCheckIn(event.target.value)} /></label>
            <label>Check-out <input type="date" value={checkOut} onChange={(event) => setCheckOut(event.target.value)} /></label>
            <button type="submit">Check availability</button>
          </form>
          {house.availability === true && <p className="success">Available for these dates.</p>}
          {house.availability === false && <p className="error">Unavailable for these dates.</p>}
          {message && <p className="success" role="status">{message}</p>}
          {error && house && <p className="error" role="alert">{error}</p>}
          <button type="button" onClick={createBooking} disabled={booking || loading || house.availability === false}>
            {booking ? "Booking..." : "Book this apartment"}
          </button>

          {house.reviews?.length > 0 && (
            <section>
              <h3>Guest reviews</h3>
              {house.reviews.map((review, index) => (
                <blockquote key={index}>
                  <strong>{review.rating}/5</strong>
                  <p>{review.comment || "No written comment."}</p>
                </blockquote>
              ))}
            </section>
          )}
        </article>
      )}
    </section>
  );
}

