import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorText } from "../Api.js";
import { formatKsh } from "../apartmentDisplay.js";

export default function BookingCard() {
  const { id } = useParams();
  const [booking, setBooking] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    api(`/bookings/${id}/`).then(async (response) => {
      const data = await response.json();
      if (!response.ok) throw new Error(errorText(data));
      if (active) setBooking(data);
    }).catch((requestError) => { if (active) setError(requestError.message || "Could not load this booking."); });
    return () => { active = false; };
  }, [id]);
  async function cancel() {
    if (!window.confirm("Cancel this booking request?")) return;
    const response = await api(`/bookings/${id}/cancel/`, { method: "POST", body: JSON.stringify({}) });
    const data = await response.json();
    if (!response.ok) setError(errorText(data));
    else { setBooking(data); setNotice("Booking cancelled."); }
  }
  return <div className="mx-auto max-w-3xl space-y-5">
    <p><Link className="text-sm font-semibold text-nest-700" to="/bookings">← Back to my stays</Link></p>
    {error && <p className="rounded-xl bg-red-50 p-4 text-red-700" role="alert">{error}</p>}
    {notice && <p className="rounded-xl bg-emerald-50 p-4 text-emerald-800" role="status">{notice}</p>}
    {!booking && !error && <p role="status">Loading booking details…</p>}
    {booking && <section className="rounded-2xl border border-line bg-white p-6 shadow-sm"><p className="text-xs font-bold uppercase tracking-wider text-nest-600">RESERVATION #{booking.id}</p><h1 className="mt-2 text-3xl font-semibold text-ink">{booking.house_name}</h1><dl className="mt-6 grid gap-4 sm:grid-cols-2"><div><dt className="text-sm text-muted">Dates</dt><dd>{booking.check_in} – {booking.check_out}</dd></div><div><dt className="text-sm text-muted">Guests</dt><dd>{booking.guest_count}</dd></div><div><dt className="text-sm text-muted">Nights</dt><dd>{booking.nights}</dd></div><div><dt className="text-sm text-muted">Contact</dt><dd>{booking.contact_number}</dd></div><div><dt className="text-sm text-muted">Estimated cost</dt><dd className="font-semibold">KSh {formatKsh(booking.total_price)}</dd></div><div><dt className="text-sm text-muted">Status</dt><dd className="capitalize">{booking.status === "pending" ? "Pending Approval" : booking.status}</dd></div><div><dt className="text-sm text-muted">Submitted</dt><dd>{new Date(booking.created_at).toLocaleString()}</dd></div></dl>{(booking.status === "pending" || booking.status === "confirmed") && <button className="mt-6 rounded-xl border border-red-200 px-4 py-2 font-semibold text-red-700" onClick={cancel}>Cancel request</button>}</section>}
  </div>;
}
