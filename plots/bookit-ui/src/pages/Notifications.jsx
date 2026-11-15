import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorText } from "../Api.js";

export default function Notifications() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const load = useCallback(async () => {
    try {
      const response = await api("/notifications/");
      const body = await response.json();
      if (!response.ok) throw new Error(errorText(body));
      setData(body);
      setError("");
    } catch (requestError) { setError(requestError.message || "Could not load notifications."); }
    finally { setBusy(false); }
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(timer);
  }, [load]);
  async function markRead(notification) {
    const response = await api(`/notifications/${notification.id}/read/`, { method: "POST", body: JSON.stringify({}) });
    if (response.ok) setData((current) => ({ ...current, unread_count: Math.max(0, current.unread_count - (notification.read ? 0 : 1)), results: current.results.map((item) => item.id === notification.id ? { ...item, read: true } : item) }));
    else setError(errorText(await response.json()));
  }
  return <section className="mx-auto max-w-3xl space-y-5"><header><p className="text-xs font-bold uppercase tracking-wider text-nest-600">YOUR ACCOUNT</p><h1 className="mt-2 text-3xl font-semibold text-ink">Notifications</h1><p className="mt-2 text-muted">Booking updates from Urban Nest.</p>{data && <p className="mt-1 text-sm text-muted" aria-live="polite">{data.unread_count} unread notification{data.unread_count === 1 ? "" : "s"}</p>}</header>{error && <p className="rounded-xl bg-red-50 p-4 text-red-700" role="alert">{error}</p>}{busy && <p role="status">Loading notifications…</p>}<div className="grid gap-3">{(data?.results || []).map((notification) => <article key={notification.id} className={`rounded-2xl border bg-white p-5 ${notification.read ? "border-line" : "border-nest-300 shadow-sm"}`}><div className="flex items-start justify-between gap-3"><div><h2 className="font-semibold text-ink">{notification.title}</h2><p className="mt-2 text-sm leading-6 text-muted">{notification.message}</p><small className="mt-3 block text-xs text-muted">{new Date(notification.created_at).toLocaleString()}</small></div>{!notification.read && <span className="rounded-full bg-red-600 px-2 py-1 text-xs font-bold text-white">New</span>}</div><div className="mt-3 flex gap-4">{notification.booking_id && <Link className="text-sm font-semibold text-nest-700" to={`/bookings/${notification.booking_id}`}>View booking</Link>}{!notification.read && <button className="text-sm font-semibold text-nest-700" onClick={() => markRead(notification)}>Mark as read</button>}</div></article>)}{!busy && !data?.results?.length && <p className="rounded-2xl border border-dashed border-nest-300 p-6 text-muted">You have no notifications.</p>}</div></section>;
}
