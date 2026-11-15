import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorText } from "../Api.js";
import { useAuth } from "../auth.js";

export default function Dashboard() {
  const { username } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    async function load() {
      try {
        const res = await api("/dashboard/");
        const body = await res.json();
        if (!res.ok) setError(errorText(body));
        else if (!body || !Array.isArray(body.announcements)) setError("The server returned an unexpected dashboard response.");
        else { setData(body); setError(""); }
      } catch (requestError) { setError(errorText(requestError)); }
    }
    load();
  }, []);
  if (error) return <p className="rounded-xl border border-red-100 bg-red-50 p-4 text-red-700">{error}</p>;
  if (!data) return <p className="py-12 text-muted">Loading your dashboard…</p>;
  return <div className="space-y-8">
    <header className="rounded-[1.75rem] bg-nest-900 px-7 py-9 text-white sm:px-10"><p className="text-xs font-bold uppercase tracking-[.18em] text-nest-300">YOUR URBAN NEST</p><h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">Welcome home, {username}.</h1><p className="mt-2 text-sm text-white/65">Here’s what’s happening with your stays.</p><Link className="mt-6 inline-flex rounded-full bg-nest-200 px-5 py-2.5 text-sm font-bold text-nest-900 transition hover:bg-white" to="/houses">Explore available homes <span className="ml-2">→</span></Link></header>
    {data.payments_due > 0 && <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-950"><p className="m-0 text-sm">You have <strong>{data.payments_due}</strong> payment{data.payments_due === 1 ? "" : "s"} due on your payment cards.</p><Link className="font-semibold text-amber-900 underline decoration-amber-300 underline-offset-4" to="/bookings">Review payments</Link></div>}
    <section><div className="mb-4 flex items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">THE LATEST</p><h2 className="mt-2 text-2xl font-semibold text-ink">Updates for you</h2></div><Link className="text-sm font-semibold text-nest-700 hover:text-nest-900" to="/bookings">My stays →</Link></div><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{data.announcements.map((a, i) => <article className="rounded-2xl border border-line bg-white p-5 shadow-sm" key={i}><h3 className="font-semibold text-ink">{a.title}</h3><p className="mt-2 text-sm leading-6 text-muted">{a.message}</p><small className="mt-4 block text-xs text-muted">{new Date(a.created_at).toLocaleString()}</small></article>)}{data.announcements.length === 0 && <p className="rounded-2xl border border-dashed border-nest-300 p-6 text-sm text-muted">No announcements right now. We’ll share useful updates here.</p>}</div></section>
  </div>;
}
