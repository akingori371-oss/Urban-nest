import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { api, errorText } from "../Api.js";
import { demoApartmentMarker, formatKsh, visibleApartmentDescription } from "../apartmentDisplay.js";
import { useAuth } from "../auth.js";


function useResource(path) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  async function reload() {
    setBusy(true);
    try {
      const response = await api(path);
      const body = await response.json();
      if (!response.ok) throw new Error(errorText(body));
      setData(body);
      setError("");
    } catch (err) { setError(err.message || "Could not load this page."); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    let active = true;
    api(path).then(async (response) => {
      const body = await response.json();
      if (!response.ok) throw new Error(errorText(body));
      if (active) { setData(body); setError(""); }
    }).catch((err) => { if (active) setError(err.message || "Could not load this page."); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [path]);
  return { data, error, busy, reload, setData };
}
function ResultMessage({ error, message }) {
  return <>{error && <p className="my-3 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>}{message && <p className="my-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800" role="status">{message}</p>}</>;
}

function ManagerDashboard() {
  const { data, error, busy } = useResource("/manager/dashboard/");
  if (busy) return <p role="status">Loading manager dashboard...</p>;
  if (error) return <p className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">{error}</p>;
  const stats = [
    ["Properties", data.apartments_total], ["Available now", data.apartments_available],
    ["Occupied now", data.apartments_occupied], ["Tenants", data.tenants_total],
    ["Bookings", data.bookings_total], ["Pending approval", data.bookings_pending],
    ["Confirmed", data.bookings_confirmed], ["Rejected", data.bookings_rejected],
    ["Cancelled", data.bookings_cancelled], ["Unread requests", data.unread_booking_requests],
  ];
  return <>
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold tracking-[.16em] text-nest-600">OVERVIEW</p><h1 className="text-3xl font-semibold tracking-tight text-ink">Manager dashboard</h1><p>Live activity and totals from Urban Nest records.</p></div><Link className="rounded-xl bg-nest-800 px-4 py-3 font-semibold text-white" to="/manager/requests">Review booking requests</Link></div>
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">{stats.map(([label, value]) => <article className="grid gap-3 rounded-2xl border border-line bg-white p-5 shadow-sm" key={label}><span>{label}</span><strong>{value}</strong></article>)}</div>
    <div className="mt-6 grid items-start gap-4 lg:grid-cols-2"><section className="rounded-2xl border border-line bg-white p-5 shadow-sm"><h2 className="mb-4 text-lg font-semibold text-ink">Recent bookings</h2>{data.recent_bookings.length ? data.recent_bookings.map((b) => <p key={b.id}><Link to={`/manager/bookings/${b.id}`}>#{b.id} ? {b.house__name}</Link><span>{b.user__username} ? {b.status}</span></p>) : <p>No bookings yet.</p>}</section>
      <section className="rounded-2xl border border-line bg-white p-5 shadow-sm"><h2 className="mb-4 text-lg font-semibold text-ink">New tenants</h2>{data.recent_tenants.length ? data.recent_tenants.map((t) => <p key={t.id}>{t.username}<span>{t.email}</span></p>) : <p>No tenants yet.</p>}</section>
      <section className="rounded-2xl border border-line bg-white p-5 shadow-sm"><h2 className="mb-4 text-lg font-semibold text-ink">Announcements</h2>{data.recent_announcements.length ? data.recent_announcements.map((a) => <p key={a.id}>{a.title}<span>{a.is_published ? "Published" : "Draft"}</span></p>) : <p>No announcements yet.</p>}</section></div>
  </>;
}

function ApartmentList() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { data, error, busy, reload } = useResource(`/manager/apartments/?search=${encodeURIComponent(search)}&page=${page}`);
  const [notice, setNotice] = useState("");
  async function deactivate(id) {
    const response = await api(`/manager/apartments/${id}/`, { method: "DELETE" });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) setNotice(errorText(body)); else { setNotice("Property deactivated; booking history was preserved."); reload(); }
  }
  return <>
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold tracking-[.16em] text-nest-600">PROPERTY MANAGEMENT</p><h1 className="text-3xl font-semibold tracking-tight text-ink">Properties</h1></div><Link className="inline-flex min-h-11 items-center justify-center rounded-xl bg-nest-800 px-4 py-2.5 font-semibold text-white transition hover:bg-nest-900 disabled:cursor-not-allowed disabled:opacity-50" to="/manager/apartments/new">Add property</Link></div>
    <ResultMessage error={error || notice.startsWith("Property") ? "" : notice} message={notice.startsWith("Property") ? notice : ""} />
    <div className="my-4 flex flex-wrap gap-3"><input className="min-h-11 rounded-xl border border-line bg-white px-4 py-2 text-sm focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" placeholder="Search name or location" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} /></div>
    {busy ? <p role="status">Loading properties...</p> : data?.results?.length ? <div className="overflow-x-auto rounded-2xl border border-line bg-white"><table className="w-full min-w-max border-collapse text-left text-sm"><thead><tr><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Property</th><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Location</th><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Bedrooms</th><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Nightly price</th><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Availability</th><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Actions</th></tr></thead><tbody>{data.results.map((h) => <tr key={h.id}><td className="border-b border-line px-4 py-3 align-top">{h.name}</td><td className="border-b border-line px-4 py-3 align-top">{h.location}</td><td className="border-b border-line px-4 py-3 align-top">{h.bedrooms}</td><td className="border-b border-line px-4 py-3 align-top">KSh {formatKsh(h.price_per_night)}</td><td className="border-b border-line px-4 py-3 align-top">{h.is_active ? "Active" : "Inactive"}</td><td className="border-b border-line px-4 py-3 align-top"><Link to={`/manager/apartments/${h.id}/edit`}>Edit</Link>{h.is_active && <button className="rounded-lg px-2 py-1 text-sm font-semibold text-red-700 hover:bg-red-50" onClick={() => deactivate(h.id)}>Deactivate</button>}</td></tr>)}</tbody></table></div> : <p className="rounded-xl border border-dashed border-nest-300 p-6 text-center text-muted">No properties found.</p>}
    {data && <div className="my-5 flex items-center justify-center gap-4"><button disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>Previous</button><span>{page} · {data.count} properties</span><button disabled={!data.next} onClick={() => setPage((p) => p + 1)}>Next</button></div>}
  </>;
}

function ApartmentForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", location: "", description: "", bedrooms: 1, price_per_night: "", is_active: true });
  const [bookings, setBookings] = useState([]);
  const fields = [["name", "Name"], ["location", "Location"], ["bedrooms", "Bedrooms"], ["price_per_night", "Nightly price (KSh)"]];
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [photos, setPhotos] = useState([]);
  const [photoCaption, setPhotoCaption] = useState("Interior");
  const [demoMarker, setDemoMarker] = useState("");
  useEffect(() => { if (id) api(`/manager/apartments/${id}/`).then(async (response) => { const d = await response.json(); if (!response.ok) throw new Error(errorText(d)); setDemoMarker(demoApartmentMarker(d)); setForm({ ...d, price_per_night: String(Number(d.price_per_night)), description: visibleApartmentDescription(d) }); setPhotos(d.photos || []); setBookings(d.bookings || []); }).catch((e) => setError(e.message)); }, [id]);
  function change(e) { setForm({ ...form, [e.target.name]: e.target.type === "checkbox" ? e.target.checked : e.target.value }); }
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const payload = { ...form, description: demoMarker ? `${demoMarker} ${form.description}` : form.description };
      const response = await api(id ? `/manager/apartments/${id}/` : "/manager/apartments/", { method: id ? "PATCH" : "POST", body: JSON.stringify(payload) });
      const data = await response.json(); if (!response.ok) throw new Error(errorText(data));
      navigate(`/manager/apartments/${data.id}/edit`);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function upload(e) {
    const image = e.target.files?.[0]; if (!image) return;
    const body = new FormData(); body.append("image", image); body.append("caption", photoCaption);
    const response = await api(`/manager/apartments/${id}/photos/`, { method: "POST", body });
    const data = await response.json(); if (!response.ok) setError(errorText(data)); else setPhotos([...photos, data]);
    e.target.value = "";
  }
  async function removePhoto(photoId) {
    const response = await api(`/manager/apartments/${id}/photos/${photoId}/`, { method: "DELETE" });
    if (response.ok) setPhotos(photos.filter((photo) => photo.id !== photoId));
    else setError(errorText(await response.json()));
  }
  return <><div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold tracking-[.16em] text-nest-600">PROPERTY</p><h1 className="text-3xl font-semibold tracking-tight text-ink">{id ? "Edit property" : "Add property"}</h1></div></div><ResultMessage error={error} />
    <form className="grid max-w-3xl gap-4 rounded-2xl border border-line bg-white p-6 shadow-sm" onSubmit={submit}>{fields.map(([name, label]) => <label key={name}>{label}<input name={name} type={name === "bedrooms" || name === "price_per_night" ? "number" : "text"} min={name === "bedrooms" ? (demoMarker ? 0 : 1) : name === "price_per_night" ? 1 : undefined} max={name === "price_per_night" ? 4999 : undefined} step={name === "price_per_night" ? "1" : undefined} value={form[name]} onChange={change} required /></label>)}<label>Description<textarea name="description" value={form.description} onChange={change} rows="5" /></label>{id && <label className="flex items-center gap-3"><input type="checkbox" name="is_active" checked={form.is_active} onChange={change} /> Active and available to tenants</label>}<button className="inline-flex min-h-11 items-center justify-center rounded-xl bg-nest-800 px-4 py-2.5 font-semibold text-white transition hover:bg-nest-900 disabled:cursor-not-allowed disabled:opacity-50" disabled={busy}>{busy ? "Saving..." : "Save property"}</button></form>
    {id && <><section className="rounded-2xl border border-line bg-white p-5 shadow-sm manager-photo-panel"><h2 className="mb-4 text-lg font-semibold text-ink">Property photos</h2><p>JPEG, PNG, or WebP · maximum 8 MB each.</p><label>Photo type <select value={photoCaption} onChange={(event) => setPhotoCaption(event.target.value)}><option>Interior</option><option>Exterior</option></select></label><input type="file" accept="image/jpeg,image/png,image/webp" onChange={upload} />{photos.map((photo) => <div className="mr-3 mt-3 inline-flex flex-col gap-2" key={photo.id}><img src={photo.image} alt={photo.caption || "Property"} /><input aria-label="Replace photo" type="file" accept="image/jpeg,image/png,image/webp" onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; const body = new FormData(); body.append("image", file); const response = await api(`/manager/apartments/${id}/photos/${photo.id}/`, { method: "PUT", body }); const data = await response.json(); if (response.ok) setPhotos(photos.map((item) => item.id === photo.id ? data : item)); else setError(errorText(data)); e.target.value = ""; }} /><button className="rounded-lg px-2 py-1 text-sm font-semibold text-red-700 hover:bg-red-50" onClick={() => removePhoto(photo.id)}>Remove photo</button></div>)}</section><section className="rounded-2xl border border-line bg-white p-5 shadow-sm"><h2 className="mb-4 text-lg font-semibold text-ink">Recent booking activity</h2>{bookings.length ? bookings.map((booking) => <p key={booking.id}>Booking #{booking.id} · {booking.check_in} – {booking.check_out} · {booking.status}</p>) : <p>No bookings for this property.</p>}</section></>}
  </>;
}

function BookingList() {
  const [search, setSearch] = useState(""); const [status, setStatus] = useState(""); const [page, setPage] = useState(1);
  const { data, error, busy } = useResource(`/manager/bookings/?search=${encodeURIComponent(search)}&status=${status}&page=${page}`);
  return <><div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold tracking-[.16em] text-nest-600">OPERATIONS</p><h1 className="text-3xl font-semibold tracking-tight text-ink">Bookings</h1></div></div><ResultMessage error={error} /><div className="my-4 flex flex-wrap gap-3"><input className="min-h-11 rounded-xl border border-line bg-white px-4 py-2 text-sm" placeholder="Search tenant, property, or booking ID" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} /><select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}><option value="">All statuses</option>{["pending", "confirmed", "rejected", "cancelled"].map((value) => <option key={value} value={value}>{value}</option>)}</select></div>{busy ? <p>Loading bookings...</p> : <div className="overflow-x-auto rounded-2xl border border-line bg-white"><table className="w-full min-w-max border-collapse text-left text-sm"><thead><tr><th className="border-b border-line bg-nest-50 px-4 py-3">Booking</th><th className="border-b border-line bg-nest-50 px-4 py-3">Tenant</th><th className="border-b border-line bg-nest-50 px-4 py-3">Apartment</th><th className="border-b border-line bg-nest-50 px-4 py-3">Dates</th><th className="border-b border-line bg-nest-50 px-4 py-3">Estimated cost</th><th className="border-b border-line bg-nest-50 px-4 py-3">Status</th></tr></thead><tbody>{(data?.results || []).map((b) => <tr key={b.id}><td className="border-b border-line px-4 py-3"><Link to={`/manager/bookings/${b.id}`}>#{b.id}</Link></td><td className="border-b border-line px-4 py-3">{b.tenant?.username}<small>{b.tenant?.email}</small></td><td className="border-b border-line px-4 py-3">{b.apartment?.name}</td><td className="border-b border-line px-4 py-3">{b.check_in} ? {b.check_out}</td><td className="border-b border-line px-4 py-3">KSh {formatKsh(b.total_price)}</td><td className="border-b border-line px-4 py-3 capitalize">{b.status}</td></tr>)}</tbody></table>{!data?.results?.length && <p className="p-6 text-center text-muted">No bookings found.</p>}</div>}<Pager data={data} page={page} setPage={setPage} /></>;
}

function BookingDetail() {
  const { id } = useParams(); const { data, error, busy, reload } = useResource(`/manager/bookings/${id}/`);
  const [message, setMessage] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => { if (data) window.dispatchEvent(new Event("urban-nest-booking-count-refresh")); }, [data]);
  async function requestClarification(event) {
    event.preventDefault();
    const response = await api(`/manager/bookings/${id}/clarify/`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    const body = await response.json();
    if (!response.ok) setNotice(errorText(body));
    else {
      setMessage("");
      setNotice("Clarification request sent.");
      reload();
    }
  }
  if (busy) return <p>Loading booking...</p>;
  return <><div className="mb-6"><p className="text-xs font-bold tracking-[.16em] text-nest-600">BOOKING #{id}</p><h1 className="text-3xl font-semibold tracking-tight text-ink">{data?.apartment?.name}</h1></div><ResultMessage error={error || (notice && notice !== "Clarification request sent." ? notice : "")} message={notice === "Clarification request sent." ? notice : ""} />{data && <><section className="grid gap-3 rounded-2xl border border-line bg-white p-5 shadow-sm"><p><strong>Customer</strong> {data.tenant.username} ? {data.tenant.email}</p><p><strong>Contact</strong> {data.contact_number || "Not provided"}</p><p><strong>Dates</strong> {data.check_in} ? {data.check_out} ? {data.nights} nights</p><p><strong>Guests</strong> {data.guest_count}</p><p><strong>Estimated cost</strong> KSh {formatKsh(data.total_price)}</p><p><strong>Status</strong> <span className="capitalize">{data.status}</span></p><p><strong>Submitted</strong> {new Date(data.created_at).toLocaleString()}</p></section>{data.status === "pending" && <section className="mt-4 rounded-2xl border border-line bg-white p-5 shadow-sm">{data.clarification_requested ? <p role="status">A clarification request has already been sent to this customer.</p> : <form className="grid gap-3" onSubmit={requestClarification}><h2 className="font-semibold text-ink">Request clarification</h2><p className="text-sm text-muted">The booking remains pending while the customer responds.</p><label htmlFor="booking-clarification" className="text-sm font-medium text-ink">Message to customer</label><textarea id="booking-clarification" className="min-h-28 rounded-xl border border-line p-3" required maxLength={1000} value={message} onChange={(event) => setMessage(event.target.value)} /><button className="justify-self-start rounded-xl bg-nest-800 px-4 py-2.5 font-semibold text-white">Send clarification request</button></form>}</section>}</>}</>;
}

function AnnouncementList() {
  const { data, error, busy, reload } = useResource("/manager/announcements/?page_size=100");
  const tenants = useResource("/manager/tenants/?page_size=100");
  const [form, setForm] = useState({ title: "", message: "", is_published: false, recipient_ids: [], audience: "all" }); const [notice, setNotice] = useState("");
  async function create(e) { e.preventDefault(); const payload = { title: form.title, message: form.message, is_published: form.is_published, recipient_ids: form.audience === "all" ? [] : form.recipient_ids }; const response = await api("/manager/announcements/", { method: "POST", body: JSON.stringify(payload) }); const body = await response.json(); if (!response.ok) setNotice(errorText(body)); else { setForm({ title: "", message: "", is_published: false, recipient_ids: [], audience: "all" }); setNotice("Announcement saved."); reload(); } }
  async function update(a, changes) { const response = await api(`/manager/announcements/${a.id}/`, { method: "PATCH", body: JSON.stringify(changes) }); if (response.ok) reload(); else setNotice(errorText(await response.json())); }
  async function remove(a) { const response = await api(`/manager/announcements/${a.id}/`, { method: "DELETE" }); if (response.ok) reload(); else setNotice(errorText(await response.json())); }
  return <><div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold tracking-[.16em] text-nest-600">COMMUNICATION</p><h1 className="text-3xl font-semibold tracking-tight text-ink">Announcements</h1></div></div><ResultMessage error={error || (notice && !notice.includes("saved") ? notice : "")} message={notice.includes("saved") ? notice : ""} /><div className="mt-6 grid items-start gap-4 lg:grid-cols-2"><form className="grid max-w-3xl gap-4 rounded-2xl border border-line bg-white p-6 shadow-sm manager-panel" onSubmit={create}><h2 className="mb-4 text-lg font-semibold text-ink">New announcement</h2><label>Title<input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label><label>Message<textarea required rows="5" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} /></label><label>Audience<select value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value, recipient_ids: [] })}><option value="all">All tenants</option><option value="selected">Selected tenants</option></select></label>{form.audience === "selected" && <label>Choose tenants<select multiple value={form.recipient_ids.map(String)} onChange={(e) => setForm({ ...form, recipient_ids: Array.from(e.target.selectedOptions, (option) => Number(option.value)) })}>{(tenants.data?.results || []).map((t) => <option key={t.id} value={t.id}>{t.username} · {t.email}</option>)}</select></label>}<label className="flex items-center gap-3"><input type="checkbox" checked={form.is_published} onChange={(e) => setForm({ ...form, is_published: e.target.checked })} /> Publish now</label><button className="inline-flex min-h-11 items-center justify-center rounded-xl bg-nest-800 px-4 py-2.5 font-semibold text-white transition hover:bg-nest-900 disabled:cursor-not-allowed disabled:opacity-50">Save announcement</button></form><section className="rounded-2xl border border-line bg-white p-5 shadow-sm"><h2 className="mb-4 text-lg font-semibold text-ink">All announcements</h2>{busy ? <p>Loading...</p> : (data?.results || []).map((a) => <article className="border-b border-line py-4" key={a.id}><h3 className="font-semibold text-ink">{a.title}</h3><p>{a.message}</p><small>{a.recipient_ids?.length ? `${a.recipient_ids.length} selected tenants` : "All tenants"} · {a.is_published ? "Published" : "Draft"}</small><div><button onClick={() => update(a, { is_published: !a.is_published })}>{a.is_published ? "Unpublish" : "Publish"}</button><button className="rounded-lg px-2 py-1 text-sm font-semibold text-red-700 hover:bg-red-50" onClick={() => remove(a)}>Delete</button></div></article>)}</section></div></>;
}

function TenantList() {
  const [search, setSearch] = useState(""); const [page, setPage] = useState(1); const { data, error, busy, reload } = useResource(`/manager/tenants/?search=${encodeURIComponent(search)}&page=${page}`); const [notice, setNotice] = useState("");
  async function toggle(t) { const response = await api(`/manager/tenants/${t.id}/`, { method: "PATCH", body: JSON.stringify({ is_active: !t.is_active }) }); if (response.ok) reload(); else setNotice(errorText(await response.json())); }
  return <><div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold tracking-[.16em] text-nest-600">PEOPLE</p><h1 className="text-3xl font-semibold tracking-tight text-ink">Tenants</h1></div></div><ResultMessage error={error || notice} /><div className="my-4 flex flex-wrap gap-3"><input className="min-h-11 rounded-xl border border-line bg-white px-4 py-2 text-sm focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" placeholder="Search username or email" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} /></div>{busy ? <p>Loading tenants...</p> : <div className="overflow-x-auto rounded-2xl border border-line bg-white"><table className="w-full min-w-max border-collapse text-left text-sm"><thead><tr><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Tenant</th><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Joined</th><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Bookings</th><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Status</th><th className="border-b border-line bg-nest-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">Action</th></tr></thead><tbody>{(data?.results || []).map((t) => <tr key={t.id}><td className="border-b border-line px-4 py-3 align-top">{t.username}<small>{t.email}</small></td><td className="border-b border-line px-4 py-3 align-top">{new Date(t.date_joined).toLocaleDateString()}</td><td className="border-b border-line px-4 py-3 align-top">{t.bookings_count}</td><td className="border-b border-line px-4 py-3 align-top">{t.is_active ? "Active" : "Inactive"}</td><td className="border-b border-line px-4 py-3 align-top"><Link to={`/manager/tenants/${t.id}`}>History</Link> <button onClick={() => toggle(t)}>{t.is_active ? "Deactivate" : "Activate"}</button></td></tr>)}</tbody></table></div>}<Pager data={data} page={page} setPage={setPage} /></>;
}

function TenantDetail() {
  const { id } = useParams(); const { data, error, busy } = useResource(`/manager/tenants/${id}/`);
  if (busy) return <p>Loading tenant...</p>;
  return <><div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold tracking-[.16em] text-nest-600">TENANT HISTORY</p><h1 className="text-3xl font-semibold tracking-tight text-ink">{data?.username}</h1><p>{data?.email} ? {data?.is_active ? "Active" : "Inactive"}</p></div></div><ResultMessage error={error} /><section className="rounded-2xl border border-line bg-white p-5 shadow-sm"><h2 className="mb-4 text-lg font-semibold text-ink">Bookings</h2>{(data?.bookings || []).map((b) => <p key={b.id}>#{b.id} ? {b.house__name} ? {b.check_in} ? {b.check_out} ? KSh {formatKsh(b.total_price)} ? {b.status}</p>)}</section></>;
}

function ManagerInvitations() {
  const { data, error, busy, reload } = useResource("/manager/invitations/?page_size=100"); const [email, setEmail] = useState(""); const [notice, setNotice] = useState("");
  async function invite(e) { e.preventDefault(); const response = await api("/manager/invitations/", { method: "POST", body: JSON.stringify({ email }) }); const body = await response.json(); if (!response.ok) setNotice(errorText(body)); else { setEmail(""); setNotice("Invitation email sent."); reload(); } }
  async function cancel(item) { const response = await api(`/manager/invitations/${item.id}/`, { method: "DELETE" }); if (response.ok) reload(); else setNotice(errorText(await response.json())); }
  const { isMainManager } = useAuth(); if (!isMainManager) return <p className="error">Only the main manager can manage invitations.</p>;
  return <><div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold tracking-[.16em] text-nest-600">ACCESS CONTROL</p><h1 className="text-3xl font-semibold tracking-tight text-ink">Managers & invitations</h1></div></div><ResultMessage error={error || (notice && !notice.includes("sent") ? notice : "")} message={notice.includes("sent") ? notice : ""} /><form className="my-4 flex flex-wrap gap-3" onSubmit={invite}><input className="min-h-11 rounded-xl border border-line bg-white px-4 py-2 text-sm focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" type="email" required placeholder="Manager email address" value={email} onChange={(e) => setEmail(e.target.value)} /><button className="inline-flex min-h-11 items-center justify-center rounded-xl bg-nest-800 px-4 py-2.5 font-semibold text-white transition hover:bg-nest-900 disabled:cursor-not-allowed disabled:opacity-50">Send invitation</button></form><section className="rounded-2xl border border-line bg-white p-5 shadow-sm"><h2 className="mb-4 text-lg font-semibold text-ink">Invitations</h2>{busy ? <p>Loading invitations...</p> : (data?.results || []).map((item) => <p key={item.id}>{item.email}<span>{item.status} · expires {new Date(item.expires_at).toLocaleDateString()}</span>{item.status === "pending" && <button className="rounded-lg px-2 py-1 text-sm font-semibold text-red-700 hover:bg-red-50" onClick={() => cancel(item)}>Cancel</button>}</p>)}</section></>;
}

function ManagersList() {
  const { data, error, busy, reload } = useResource("/manager/managers/"); const { isMainManager } = useAuth(); const [notice, setNotice] = useState("");
  async function remove(m) { const response = await api(`/manager/managers/${m.id}/`, { method: "DELETE" }); if (response.ok) reload(); else setNotice(errorText(await response.json())); }
  if (!isMainManager) return <p className="error">Only the main manager can remove managers.</p>;
  return <><div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold tracking-[.16em] text-nest-600">ACCESS CONTROL</p><h1 className="text-3xl font-semibold tracking-tight text-ink">Managers</h1></div></div><ResultMessage error={error || notice} />{busy ? <p>Loading managers...</p> : <section className="rounded-2xl border border-line bg-white p-5 shadow-sm">{(data || []).map((m) => <p key={m.id}>{m.username} · {m.email}<span>{m.is_main ? "Main manager" : "Invited manager"}</span>{!m.is_main && <button className="rounded-lg px-2 py-1 text-sm font-semibold text-red-700 hover:bg-red-50" onClick={() => remove(m)}>Remove access</button>}</p>)}</section>}</>;
}

function Pager({ data, page, setPage }) { return data?.count > 20 && <div className="my-5 flex items-center justify-center gap-4"><button className="rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink hover:bg-nest-50 disabled:opacity-40" disabled={!data.previous} onClick={() => setPage(page - 1)}>Previous</button><span className="text-sm text-muted">Page {page}</span><button className="rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink hover:bg-nest-50 disabled:opacity-40" disabled={!data.next} onClick={() => setPage(page + 1)}>Next</button></div>; }

function BookingRequestsNavLink({ className }) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const response = await api("/manager/booking-requests/unread-count/");
        const data = await response.json();
        if (active && response.ok) setCount(data.unread_count || 0);
      } catch { /* The next interval refreshes the server-derived count. */ }
    };
    void refresh();
    window.addEventListener("urban-nest-booking-count-refresh", refresh);
    const timer = setInterval(refresh, 10000);
    return () => { active = false; window.removeEventListener("urban-nest-booking-count-refresh", refresh); clearInterval(timer); };
  }, []);
  return <Link className={className} to="/manager/requests">Booking Requests{count > 0 && <span className="ml-2 inline-grid min-w-5 place-items-center rounded-full bg-red-600 px-1.5 py-0.5 text-xs font-bold text-white">{count}</span>}</Link>;
}

function BookingRequests() {
  const [status, setStatus] = useState("pending");
  const [page, setPage] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, error, busy, reload } = useResource(`/manager/bookings/?status=${status}&page=${page}&refresh=${refreshKey}`);
  const [notice, setNotice] = useState("");
  async function decide(booking, action) {
    const verb = action === "approve" ? "approve" : "reject";
    if (!window.confirm(`Are you sure you want to ${verb} booking request #${booking.id}?`)) return;
    const response = await api(`/manager/bookings/${booking.id}/${action}/`, { method: "POST", body: JSON.stringify({}) });
    const body = await response.json();
    if (!response.ok) setNotice(errorText(body));
    else { setNotice(`Booking request #${booking.id} ${action === "approve" ? "approved" : "rejected"}.`); window.dispatchEvent(new Event("urban-nest-booking-count-refresh")); reload(); }
  }
  useEffect(() => { const timer = setInterval(() => setRefreshKey((value) => value + 1), 10000); return () => clearInterval(timer); }, []);
  return <><div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-xs font-bold tracking-[.16em] text-nest-600">RESERVATION REVIEW</p><h1 className="text-3xl font-semibold tracking-tight text-ink">Booking Requests</h1><p>Pending requests do not reserve apartment dates until approved.</p></div></div><ResultMessage error={error || (notice && !notice.startsWith("Booking request") ? notice : "")} message={notice.startsWith("Booking request") ? notice : ""} /><div className="mb-4 flex flex-wrap gap-2">{["pending", "confirmed", "rejected", "cancelled"].map((value) => <button key={value} className={`rounded-full px-4 py-2 text-sm font-semibold capitalize ${status === value ? "bg-nest-800 text-white" : "border border-line bg-white text-ink"}`} onClick={() => { setStatus(value); setPage(1); }}>{value}</button>)}</div>{busy ? <p role="status">Loading booking requests...</p> : <div className="grid gap-4">{(data?.results || []).map((booking) => <article key={booking.id} className={`rounded-2xl border bg-white p-5 shadow-sm ${booking.unread ? "border-red-200" : "border-line"}`}><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-lg font-semibold text-ink">{booking.apartment.name} <span className="text-sm font-normal text-muted">#{booking.id}</span></h2><p className="mt-1 text-sm text-muted">{booking.tenant.username} ? {booking.tenant.email}{booking.contact_number ? ` ? ${booking.contact_number}` : ""}</p><p className="mt-1 text-sm text-muted">{booking.check_in} ? {booking.check_out} ? {booking.nights} nights ? {booking.guest_count} guest{booking.guest_count === 1 ? "" : "s"}</p><p className="mt-1 text-sm font-semibold text-ink">Estimated cost: KSh {formatKsh(booking.total_price)}</p><p className="mt-1 text-xs text-muted">Submitted {new Date(booking.created_at).toLocaleString()} ? <span className="capitalize">{booking.status}</span></p></div>{booking.unread && <span className="rounded-full bg-red-600 px-2.5 py-1 text-xs font-bold text-white">Unread</span>}</div><div className="mt-4 flex flex-wrap gap-2"><Link className="rounded-lg border border-line px-3 py-2 text-sm font-semibold" to={`/manager/bookings/${booking.id}`}>View request</Link>{booking.status === "pending" && <><button className="rounded-lg bg-nest-800 px-3 py-2 text-sm font-semibold text-white" onClick={() => decide(booking, "approve")}>Approve booking</button><button className="rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-700" onClick={() => decide(booking, "reject")}>Reject booking</button></>}</div></article>)}{!data?.results?.length && <p className="rounded-xl border border-dashed border-nest-300 p-6 text-center text-muted">No {status} bookings.</p>}</div>}<Pager data={data} page={page} setPage={setPage} /></>;
}


function PropertyApprovals() {
  const { data, error, busy, reload, setData } = useResource(
    "/admin/pending-houses/"
  );

  const [processingId, setProcessingId] = useState(null);
  const [notice, setNotice] = useState("");

  async function decide(house, decision) {
    const action = decision === "approved" ? "approve" : "reject";

    if (!window.confirm(
      `Are you sure you want to ${action} "${house.name}"?`
    )) return;

    setProcessingId(house.id);
    setNotice("");

    try {
      const response = await api(
        `/admin/houses/${house.id}/review/`,
        {
          method: "POST",
          body: JSON.stringify({
            approval_status: decision,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(errorText(body));
      }

      setData((current) =>
        (current || []).filter((item) => item.id !== house.id)
      );

      setNotice(
        `${house.name} has been ${decision} successfully.`
      );
    } catch (err) {
      setNotice(err.message || "Could not review this property.");
    } finally {
      setProcessingId(null);
    }
  }

  return (
    <>
      <div className="mb-6">
        <p className="text-xs font-bold tracking-[.16em] text-nest-600">
          PROPERTY REVIEW
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-ink">
          Property Approvals
        </h1>
        <p className="mt-2 text-muted">
          Review customer-submitted properties before they appear in the
          public listings.
        </p>
      </div>

      <ResultMessage
        error={
          notice && !notice.includes("successfully") ? notice : ""
        }
        message={
          notice.includes("successfully") ? notice : ""
        }
      />

      {busy ? (
        <p role="status">Loading pending properties...</p>
      ) : error ? (
        <ResultMessage error={error} />
      ) : data?.length ? (
        <div className="grid gap-5">
          {data.map((house) => (
            <article
              key={house.id}
              className="overflow-hidden rounded-2xl border border-line bg-white shadow-sm"
            >
              <div className="p-5">
                <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-ink">
                      {house.name}
                    </h2>
                    <p className="mt-1 text-sm text-muted">
                      {house.location}, {house.county}
                    </p>
                  </div>

                  <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold capitalize text-amber-700">
                    {house.approval_status}
                  </span>
                </div>

                {house.photos?.length > 0 && (
                  <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                    {house.photos.map((photo) => (
                      <img
                        key={photo.id}
                        src={photo.image}
                        alt={photo.caption || house.name}
                        className="h-36 w-full rounded-xl object-cover"
                      />
                    ))}
                  </div>
                )}

                <div className="grid gap-3 text-sm sm:grid-cols-2">
                  <p>
                    <strong>Property type:</strong>{" "}
                    {house.property_type}
                  </p>
                  <p>
                    <strong>Bedrooms:</strong> {house.bedrooms}
                  </p>
                  <p>
                    <strong>Nightly price:</strong> KSh{" "}
                    {formatKsh(house.price_per_night)}
                  </p>
                  <p>
                    <strong>Submitted:</strong>{" "}
                    {new Date(house.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div className="mt-4">
                  <h3 className="mb-1 font-semibold text-ink">
                    Description
                  </h3>
                  <p className="whitespace-pre-line text-sm text-muted">
                    {house.description || "No description provided."}
                  </p>
                </div>

                {house.amenities?.length > 0 && (
                  <div className="mt-4">
                    <h3 className="mb-2 font-semibold text-ink">
                      Amenities
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {house.amenities.map((amenity) => (
                        <span
                          key={amenity}
                          className="rounded-full bg-nest-50 px-3 py-1 text-xs text-nest-800"
                        >
                          {amenity}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-4 border-t border-line pt-4">
                  <h3 className="font-semibold text-ink">
                    Submitted by
                  </h3>
                  <p className="mt-1 text-sm text-muted">
                    {house.owner?.username || "Unknown customer"}
                  </p>
                  <p className="text-sm text-muted">
                    {house.owner?.email || "No email provided"}
                  </p>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  <button
                    disabled={processingId !== null}
                    onClick={() => decide(house, "approved")}
                    className="rounded-xl bg-nest-800 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-nest-900 disabled:opacity-50"
                  >
                    {processingId === house.id
                      ? "Processing..."
                      : "Approve property"}
                  </button>

                  <button
                    disabled={processingId !== null}
                    onClick={() => decide(house, "rejected")}
                    className="rounded-xl border border-red-200 px-5 py-2.5 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:opacity-50"
                  >
                    Reject property
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-nest-300 p-10 text-center">
          <h2 className="text-lg font-semibold text-ink">
            All caught up!
          </h2>
          <p className="mt-2 text-sm text-muted">
            There are currently no properties awaiting approval.
          </p>
        </div>
      )}
    </>
  );
}



function ManagerLayout() {
  const { isMainManager, logout } = useAuth();
  const navigate = useNavigate();

  const item =
    "rounded-xl px-3 py-2 text-sm font-medium text-muted transition hover:bg-nest-50 hover:text-nest-800";

  return (
    <div className="grid min-h-full grid-cols-1 gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="flex flex-col gap-5 self-start rounded-card border border-line bg-white p-5 shadow-sm lg:sticky lg:top-24">
        <Link className="font-bold text-ink" to="/manager">
          Urban Nest
          <small className="block text-[.65rem] font-bold tracking-[.16em] text-muted">
            MANAGEMENT
          </small>
        </Link>

        <nav className="flex gap-1 overflow-x-auto lg:grid">
          <Link className={item} to="/manager">
            Overview
          </Link>

          <Link className={item} to="/manager/apartments">
            Properties
          </Link>

          <Link className={item} to="/manager/property-approvals">
            Property Approvals
          </Link>

          <BookingRequestsNavLink className={item} />

          <Link className={item} to="/manager/bookings">
            Bookings
          </Link>

          <Link className={item} to="/manager/announcements">
            Announcements
          </Link>

          <Link className={item} to="/manager/tenants">
            Tenants
          </Link>

          {isMainManager && (
            <>
              <span className="mt-3 px-2 text-xs font-bold uppercase tracking-wider text-muted">
                MAIN MANAGER
              </span>

              <Link className={item} to="/manager/managers">
                Managers
              </Link>

              <Link className={item} to="/manager/invitations">
                Invitations
              </Link>
            </>
          )}
        </nav>

        <button
          className="self-start rounded-full border border-line px-4 py-2 text-sm font-semibold text-ink transition hover:bg-nest-50"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Log out
        </button>
      </aside>

      <main className="min-w-0 py-2">
        <Routes>
          <Route index element={<ManagerDashboard />} />

          <Route path="apartments" element={<ApartmentList />} />
          <Route path="apartments/new" element={<ApartmentForm />} />
          <Route path="apartments/:id/edit" element={<ApartmentForm />} />

          <Route
            path="property-approvals"
            element={<PropertyApprovals />}
          />

          <Route path="requests" element={<BookingRequests />} />

          <Route path="bookings" element={<BookingList />} />
          <Route path="bookings/:id" element={<BookingDetail />} />

          <Route path="announcements" element={<AnnouncementList />} />

          <Route path="tenants" element={<TenantList />} />
          <Route path="tenants/:id" element={<TenantDetail />} />

          <Route path="managers" element={<ManagersList />} />
          <Route path="invitations" element={<ManagerInvitations />} />

          <Route
            path="*"
            element={<Navigate to="/manager" replace />}
          />
        </Routes>
      </main>
    </div>
  );
}

export default function ManagerArea() {
  return <ManagerLayout />;
}


export function InvitationAccept() {
  const { token } = useParams();
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function acceptInvitation() {
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await api.post(
        `/manager/invitations/accept/${token}/`
      );

      setMessage(response.data.detail || "Invitation accepted.");

      if (refreshUser) {
        await refreshUser();
      }

      setTimeout(() => navigate("/manager", { replace: true }), 1200);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-nest-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-nest-900">
          Manager Invitation
        </h1>

        <p className="mt-3 text-sm text-gray-600">
          {user?.email
            ? `You are signed in as ${user.email}.`
            : "Sign in to the account that received this invitation."}
        </p>

        {message && (
          <p className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">
            {message}
          </p>
        )}

        {error && (
          <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          onClick={acceptInvitation}
          disabled={loading || !user?.email || !!message}
          className="mt-6 w-full rounded-xl bg-nest-800 px-4 py-3 font-semibold text-white disabled:opacity-50"
        >
          {loading ? "Accepting..." : "Accept Invitation"}
        </button>
      </div>
    </div>
  );
}
