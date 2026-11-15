import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorText } from "../Api.js";
import { formatKsh } from "../apartmentDisplay.js";

export default function MyBookings() {
  const [bookings, setBookings] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api("/bookings/");
      const data = await res.json();
      if (res.ok && Array.isArray(data)) {
        setBookings(data);
        setError("");
      } else {
        setError(res.ok ? "The server returned an unexpected bookings response." : errorText(data));
      }
    } catch {
      setError("Could not load bookings. Check your connection and try again.");
    } finally {
      setLoading(false);
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
    <div className="space-y-6">
      <header><p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">YOUR TRIPS</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">My stays</h1><p className="mt-2 text-muted">Track your booking requests and reservations.</p></header>
      {message && <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{message}</p>}
      {error && <p className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>}
      {loading && <p className="rounded-xl bg-white p-6 text-muted" role="status">Loading your stays…</p>}
      {error && !loading && <button className="rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink" onClick={() => void load()}>Try again</button>}
      <div className="grid gap-4 md:grid-cols-2">
        {!loading && bookings.map((booking) => (
          <article className="flex flex-col rounded-2xl border border-line bg-white p-5 shadow-sm sm:p-6" key={booking.id}>
            <p className="text-xs font-bold uppercase tracking-wider text-nest-600">{booking.status === "pending" ? "BOOKING REQUEST" : "RESERVATION"}</p>
            <h2 className="mt-2 text-xl font-semibold text-ink">{booking.house_name}</h2>
            <p className="mt-2 text-sm text-muted">{booking.check_in} to {booking.check_out} · {booking.nights} night{booking.nights === 1 ? "" : "s"} · {booking.guest_count} guest{booking.guest_count === 1 ? "" : "s"}</p>
            <p className="mt-4 text-sm text-muted"><strong className="text-lg text-ink">Estimated cost: KSh {formatKsh(booking.total_price)}</strong></p>
            <p className="mt-3 text-sm text-muted">Status: <strong className="capitalize text-nest-800">{booking.status === "pending" ? "Pending Approval" : booking.status}</strong></p>
            <div className="mt-auto flex flex-wrap gap-3 pt-5">
              <Link className="rounded-full border border-line px-4 py-2 text-sm font-semibold text-ink transition hover:bg-nest-50" to={"/bookings/" + booking.id}>View details</Link>
              {(booking.status === "pending" || booking.status === "confirmed") && <button className="rounded-full border border-line px-4 py-2 text-sm font-semibold text-ink transition hover:bg-nest-50" onClick={() => act("/bookings/" + booking.id + "/cancel/")}>Cancel request</button>}
            </div>
          </article>
        ))}
        {!loading && bookings.length === 0 && !error && <div className="rounded-2xl border border-dashed border-nest-300 p-8 text-center text-muted"><p>You don’t have any stays yet.</p><Link className="mt-3 inline-flex rounded-full bg-nest-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-nest-900" to="/houses">Explore homes</Link></div>}
      </div>
    </div>
  );
}

