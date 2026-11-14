import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { api, errorText } from "../api.js";
import { useAuth } from "../auth.js";
import "./Manager.css";

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
  useEffect(() => { reload(); }, [path]);
  return { data, error, busy, reload, setData };
}

function ResultMessage({ error, message }) {
  return <>{error && <p className="error" role="alert">{error}</p>}{message && <p className="success" role="status">{message}</p>}</>;
}

function ManagerDashboard() {
  const { data, error, busy } = useResource("/manager/dashboard/");
  if (busy) return <p role="status">Loading manager dashboard...</p>;
  if (error) return <p className="error">{error}</p>;
  const stats = [
    ["Apartments", data.apartments_total], ["Available now", data.apartments_available],
    ["Occupied now", data.apartments_occupied], ["Tenants", data.tenants_total],
    ["Bookings", data.bookings_total], ["Pending bookings", data.bookings_pending],
    ["Confirmed bookings", data.bookings_confirmed], ["Cancelled bookings", data.bookings_cancelled],
    ["Successful payments", data.payments_success], ["Pending / review", data.payments_pending_review],
    ["Failed payments", data.payments_failed], ["Outstanding balance", `KES ${data.outstanding_balance}`],
  ];
  return <>
    <div className="manager-page-title"><div><p className="manager-eyebrow">OVERVIEW</p><h1>Manager dashboard</h1><p>Live activity and totals from Urban Nest records.</p></div></div>
    <div className="manager-stat-grid">{stats.map(([label, value]) => <article className="manager-stat" key={label}><span>{label}</span><strong>{value}</strong></article>)}</div>
    <div className="manager-columns"><section className="manager-panel"><h2>Recent bookings</h2>{data.recent_bookings.length ? data.recent_bookings.map((b) => <p key={b.id}><Link to={`/manager/bookings/${b.id}`}>#{b.id} · {b.house__name}</Link><span>{b.user__username} · {b.status}</span></p>) : <p>No bookings yet.</p>}</section>
      <section className="manager-panel"><h2>Recent payments</h2>{data.recent_payments.length ? data.recent_payments.map((p) => <p key={p.id}>KES {p.amount} · {p.status}<span>{p.booking__house__name || p.period__booking__house__name || "Payment"}</span></p>) : <p>No payments yet.</p>}</section>
      <section className="manager-panel"><h2>New tenants</h2>{data.recent_tenants.length ? data.recent_tenants.map((t) => <p key={t.id}>{t.username}<span>{t.email}</span></p>) : <p>No tenants yet.</p>}</section>
      <section className="manager-panel"><h2>Announcements</h2>{data.recent_announcements.length ? data.recent_announcements.map((a) => <p key={a.id}>{a.title}<span>{a.is_published ? "Published" : "Draft"}</span></p>) : <p>No announcements yet.</p>}</section></div>
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
    if (!response.ok) setNotice(errorText(body)); else { setNotice("Apartment deactivated; booking history was preserved."); reload(); }
  }
  return <>
    <div className="manager-page-title"><div><p className="manager-eyebrow">PROPERTY</p><h1>Apartments</h1></div><Link className="manager-primary" to="/manager/apartments/new">Add apartment</Link></div>
    <ResultMessage error={error || notice.startsWith("Apartment") ? "" : notice} message={notice.startsWith("Apartment") ? notice : ""} />
    <div className="manager-toolbar"><input placeholder="Search name or location" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} /></div>
    {busy ? <p role="status">Loading apartments...</p> : data?.results.length ? <div className="manager-table-wrap"><table className="manager-table"><thead><tr><th>Apartment</th><th>Location</th><th>Bedrooms</th><th>Nightly price</th><th>Availability</th><th>Actions</th></tr></thead><tbody>{data.results.map((h) => <tr key={h.id}><td>{h.name}</td><td>{h.location}</td><td>{h.bedrooms}</td><td>KES {h.price_per_night}</td><td>{h.is_active ? "Active" : "Inactive"}</td><td><Link to={`/manager/apartments/${h.id}/edit`}>Edit</Link>{h.is_active && <button className="manager-danger-link" onClick={() => deactivate(h.id)}>Deactivate</button>}</td></tr>)}</tbody></table></div> : <p className="manager-empty">No apartments found.</p>}
    {data && <div className="manager-pager"><button disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>Previous</button><span>{page} · {data.count} apartments</span><button disabled={!data.next} onClick={() => setPage((p) => p + 1)}>Next</button></div>}
  </>;
}

function ApartmentForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", location: "", description: "", bedrooms: 1, price_per_night: "", is_active: true });
  const fields = [["name", "Name"], ["location", "Location"], ["bedrooms", "Bedrooms"], ["price_per_night", "Nightly price (KES)"]];
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [photos, setPhotos] = useState([]);
  useEffect(() => { if (id) api(`/manager/apartments/${id}/`).then((r) => r.json()).then((d) => { setForm(d); setPhotos(d.photos || []); }).catch((e) => setError(e.message)); }, [id]);
  function change(e) { setForm({ ...form, [e.target.name]: e.target.type === "checkbox" ? e.target.checked : e.target.value }); }
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const response = await api(id ? `/manager/apartments/${id}/` : "/manager/apartments/", { method: id ? "PATCH" : "POST", body: JSON.stringify(form) });
      const data = await response.json(); if (!response.ok) throw new Error(errorText(data));
      navigate(`/manager/apartments/${data.id}/edit`);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function upload(e) {
    const image = e.target.files?.[0]; if (!image) return;
    const body = new FormData(); body.append("image", image);
    const response = await api(`/manager/apartments/${id}/photos/`, { method: "POST", body });
    const data = await response.json(); if (!response.ok) setError(errorText(data)); else setPhotos([...photos, data]);
    e.target.value = "";
  }
  async function removePhoto(photoId) {
    const response = await api(`/manager/apartments/${id}/photos/${photoId}/`, { method: "DELETE" });
    if (response.ok) setPhotos(photos.filter((photo) => photo.id !== photoId));
  }
  return <><div className="manager-page-title"><div><p className="manager-eyebrow">PROPERTY</p><h1>{id ? "Edit apartment" : "Add apartment"}</h1></div></div><ResultMessage error={error} />
    <form className="manager-form" onSubmit={submit}>{fields.map(([name, label]) => <label key={name}>{label}<input name={name} type={name === "bedrooms" || name === "price_per_night" ? "number" : "text"} min={name === "bedrooms" ? 1 : undefined} step={name === "price_per_night" ? "0.01" : undefined} value={form[name]} onChange={change} required /></label>)}<label>Description<textarea name="description" value={form.description} onChange={change} rows="5" /></label>{id && <label className="manager-check"><input type="checkbox" name="is_active" checked={form.is_active} onChange={change} /> Active and available to tenants</label>}<button className="manager-primary" disabled={busy}>{busy ? "Saving..." : "Save apartment"}</button></form>
    {id && <section className="manager-panel manager-photo-panel"><h2>Photographs</h2><p>JPEG, PNG, or WebP · maximum 8 MB each.</p><input type="file" accept="image/jpeg,image/png,image/webp" onChange={upload} />{photos.map((photo) => <div className="manager-photo" key={photo.id}><img src={photo.image} alt={photo.caption || "Apartment"} /><button className="manager-danger-link" onClick={() => removePhoto(photo.id)}>Remove photo</button></div>)}</section>}
  </>;
}

function BookingList() {
  const [search, setSearch] = useState(""); const [status, setStatus] = useState(""); const [page, setPage] = useState(1);
  const { data, error, busy } = useResource(`/manager/bookings/?search=${encodeURIComponent(search)}&status=${status}&page=${page}`);
  return <><div className="manager-page-title"><div><p className="manager-eyebrow">OPERATIONS</p><h1>Bookings</h1></div></div><ResultMessage error={error} /><div className="manager-toolbar"><input placeholder="Search tenant, apartment, or booking ID" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} /><select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}><option value="">All statuses</option><option value="confirmed">Confirmed</option><option value="cancelled">Cancelled</option></select></div>{busy ? <p>Loading bookings...</p> : <div className="manager-table-wrap"><table className="manager-table"><thead><tr><th>Booking</th><th>Tenant</th><th>Apartment</th><th>Dates</th><th>Total</th><th>Payment</th><th>Status</th></tr></thead><tbody>{(data?.results || []).map((b) => <tr key={b.id}><td><Link to={`/manager/bookings/${b.id}`}>#{b.id}</Link></td><td>{b.tenant?.username}<small>{b.tenant?.email}</small></td><td>{b.apartment?.name}</td><td>{b.check_in} – {b.check_out}</td><td>KES {b.total_price}</td><td>{b.payment_status}</td><td>{b.status}</td></tr>)}</tbody></table>{!data?.results?.length && <p className="manager-empty">No bookings found.</p>}</div>}<Pager data={data} page={page} setPage={setPage} /></>;
}

function BookingDetail() {
  const { id } = useParams(); const { data, error, busy, reload } = useResource(`/manager/bookings/${id}/`); const [notice, setNotice] = useState("");
  async function cancel() { const response = await api(`/manager/bookings/${id}/`, { method: "POST", body: JSON.stringify({ status: "cancelled" }) }); const body = await response.json(); if (!response.ok) setNotice(errorText(body)); else { setNotice("Booking cancelled."); reload(); } }
  if (busy) return <p>Loading booking...</p>;
  return <><div className="manager-page-title"><div><p className="manager-eyebrow">BOOKING #{id}</p><h1>{data?.apartment?.name}</h1></div></div><ResultMessage error={error || (notice && !notice.includes("cancelled") ? notice : "")} message={notice.includes("cancelled") ? notice : ""} />{data && <><section className="manager-panel manager-details"><p><strong>Tenant</strong>{data.tenant.username} · {data.tenant.email}</p><p><strong>Dates</strong>{data.check_in} – {data.check_out} · {data.nights} nights</p><p><strong>Total</strong>KES {data.total_price}</p><p><strong>Booking status</strong>{data.status}</p><p><strong>Payment periods</strong>{data.periods.length ? data.periods.map((p) => `#${p.number}: KES ${p.amount} (${p.paid ? "paid" : "outstanding"})`).join(" · ") : "Short stay"}</p>{data.status === "confirmed" && <button className="manager-danger" onClick={cancel}>Cancel booking</button>}</section><section className="manager-panel"><h2>Payment records</h2>{data.payments.map((p) => <p key={p.id}>KES {p.amount} · {p.status} · {p.phone} · {p.receipt || "No receipt"}</p>)}</section></>}</>;
}

function PaymentList() {
  const [search, setSearch] = useState(""); const [status, setStatus] = useState(""); const [page, setPage] = useState(1);
  const { data, error, busy } = useResource(`/manager/payments/?search=${encodeURIComponent(search)}&status=${status}&page=${page}`);
  return <><div className="manager-page-title"><div><p className="manager-eyebrow">RECONCILIATION</p><h1>Payments</h1></div></div><ResultMessage error={error} /><div className="manager-toolbar"><input placeholder="Search tenant, phone, receipt" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} /><select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}><option value="">All statuses</option>{["pending", "success", "failed", "review"].map((s) => <option key={s}>{s}</option>)}</select></div>{busy ? <p>Loading payments...</p> : <div className="manager-table-wrap"><table className="manager-table"><thead><tr><th>Date</th><th>Tenant</th><th>Apartment</th><th>Amount</th><th>Phone</th><th>Receipt</th><th>Status</th></tr></thead><tbody>{(data?.results || []).map((p) => <tr key={p.id}><td>{new Date(p.created_at).toLocaleString()}</td><td>{p.tenant?.username}<small>{p.tenant?.email}</small></td><td>{p.apartment?.name}{p.period_id && <small>Period #{p.period_id}</small>}</td><td>KES {p.amount}</td><td>{p.phone}</td><td>{p.receipt || "—"}</td><td>{p.status}</td></tr>)}</tbody></table>{!data?.results?.length && <p className="manager-empty">No payment records found.</p>}</div>}<Pager data={data} page={page} setPage={setPage} /></>;
}

function AnnouncementList() {
  const { data, error, busy, reload } = useResource("/manager/announcements/?page_size=100");
  const [form, setForm] = useState({ title: "", message: "", is_published: false, recipient_ids: [] }); const [notice, setNotice] = useState("");
  async function create(e) { e.preventDefault(); const response = await api("/manager/announcements/", { method: "POST", body: JSON.stringify(form) }); const body = await response.json(); if (!response.ok) setNotice(errorText(body)); else { setForm({ title: "", message: "", is_published: false, recipient_ids: [] }); setNotice("Announcement saved."); reload(); } }
  async function update(a, changes) { const response = await api(`/manager/announcements/${a.id}/`, { method: "PATCH", body: JSON.stringify(changes) }); if (response.ok) reload(); }
  async function remove(a) { const response = await api(`/manager/announcements/${a.id}/`, { method: "DELETE" }); if (response.ok) reload(); }
  return <><div className="manager-page-title"><div><p className="manager-eyebrow">COMMUNICATION</p><h1>Announcements</h1></div></div><ResultMessage error={error || (notice && !notice.includes("saved") ? notice : "")} message={notice.includes("saved") ? notice : ""} /><div className="manager-columns"><form className="manager-form manager-panel" onSubmit={create}><h2>New announcement</h2><label>Title<input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label><label>Message<textarea required rows="5" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} /></label><label>Audience<select value={form.recipient_ids.length ? "selected" : "all"} onChange={(e) => setForm({ ...form, recipient_ids: e.target.value === "all" ? [] : ["0"] })}><option value="all">All tenants</option><option value="selected">Selected tenants (choose IDs below)</option></select></label>{form.recipient_ids.length > 0 && <label>Tenant IDs, comma separated<input onChange={(e) => setForm({ ...form, recipient_ids: e.target.value.split(",").map(Number).filter(Boolean) })} /></label>}<label className="manager-check"><input type="checkbox" checked={form.is_published} onChange={(e) => setForm({ ...form, is_published: e.target.checked })} /> Publish now</label><button className="manager-primary">Save announcement</button></form><section className="manager-panel"><h2>All announcements</h2>{busy ? <p>Loading...</p> : (data?.results || []).map((a) => <article className="manager-announcement" key={a.id}><h3>{a.title}</h3><p>{a.message}</p><small>{a.recipient_ids?.length ? `${a.recipient_ids.length} selected tenants` : "All tenants"} · {a.is_published ? "Published" : "Draft"}</small><div><button onClick={() => update(a, { is_published: !a.is_published })}>{a.is_published ? "Unpublish" : "Publish"}</button><button className="manager-danger-link" onClick={() => remove(a)}>Delete</button></div></article>)}</section></div></>;
}

function TenantList() {
  const [search, setSearch] = useState(""); const [page, setPage] = useState(1); const { data, error, busy, reload } = useResource(`/manager/tenants/?search=${encodeURIComponent(search)}&page=${page}`);
  async function toggle(t) { await api(`/manager/tenants/${t.id}/`, { method: "PATCH", body: JSON.stringify({ is_active: !t.is_active }) }); reload(); }
  return <><div className="manager-page-title"><div><p className="manager-eyebrow">PEOPLE</p><h1>Tenants</h1></div></div><ResultMessage error={error} /><div className="manager-toolbar"><input placeholder="Search username or email" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} /></div>{busy ? <p>Loading tenants...</p> : <div className="manager-table-wrap"><table className="manager-table"><thead><tr><th>Tenant</th><th>Joined</th><th>Bookings</th><th>Outstanding</th><th>Status</th><th>Action</th></tr></thead><tbody>{(data?.results || []).map((t) => <tr key={t.id}><td>{t.username}<small>{t.email}</small></td><td>{new Date(t.date_joined).toLocaleDateString()}</td><td>{t.bookings_count}</td><td>KES {t.outstanding_balance}</td><td>{t.is_active ? "Active" : "Inactive"}</td><td><Link to={`/manager/tenants/${t.id}`}>History</Link> <button onClick={() => toggle(t)}>{t.is_active ? "Deactivate" : "Activate"}</button></td></tr>)}</tbody></table></div>}<Pager data={data} page={page} setPage={setPage} /></>;
}

function TenantDetail() {
  const { id } = useParams(); const { data, error, busy } = useResource(`/manager/tenants/${id}/`);
  if (busy) return <p>Loading tenant...</p>;
  return <><div className="manager-page-title"><div><p className="manager-eyebrow">TENANT HISTORY</p><h1>{data?.username}</h1><p>{data?.email} · {data?.is_active ? "Active" : "Inactive"}</p></div></div><ResultMessage error={error} /><section className="manager-panel"><h2>Bookings</h2>{(data?.bookings || []).map((b) => <p key={b.id}>#{b.id} · {b.house__name} · {b.check_in} – {b.check_out} · KES {b.total_price} · {b.status}</p>)}</section><section className="manager-panel"><h2>Payments</h2>{(data?.payments || []).map((p) => <p key={p.id}>KES {p.amount} · {p.status} · {p.phone} · {p.receipt || "No receipt"}</p>)}</section></>;
}

function ManagerInvitations() {
  const { data, error, busy, reload } = useResource("/manager/invitations/?page_size=100"); const [email, setEmail] = useState(""); const [notice, setNotice] = useState("");
  async function invite(e) { e.preventDefault(); const response = await api("/manager/invitations/", { method: "POST", body: JSON.stringify({ email }) }); const body = await response.json(); if (!response.ok) setNotice(errorText(body)); else { setEmail(""); setNotice("Invitation email sent."); reload(); } }
  async function cancel(item) { const response = await api(`/manager/invitations/${item.id}/`, { method: "DELETE" }); if (response.ok) reload(); }
  const { isMainManager } = useAuth(); if (!isMainManager) return <p className="error">Only the main manager can manage invitations.</p>;
  return <><div className="manager-page-title"><div><p className="manager-eyebrow">ACCESS CONTROL</p><h1>Managers & invitations</h1></div></div><ResultMessage error={error || (notice && !notice.includes("sent") ? notice : "")} message={notice.includes("sent") ? notice : ""} /><form className="manager-toolbar" onSubmit={invite}><input type="email" required placeholder="Manager email address" value={email} onChange={(e) => setEmail(e.target.value)} /><button className="manager-primary">Send invitation</button></form><section className="manager-panel"><h2>Invitations</h2>{busy ? <p>Loading invitations...</p> : (data?.results || []).map((item) => <p key={item.id}>{item.email}<span>{item.status} · expires {new Date(item.expires_at).toLocaleDateString()}</span>{item.status === "pending" && <button className="manager-danger-link" onClick={() => cancel(item)}>Cancel</button>}</p>)}</section></>;
}

function ManagersList() {
  const { data, error, busy, reload } = useResource("/manager/managers/"); const { isMainManager } = useAuth();
  async function remove(m) { const response = await api(`/manager/managers/${m.id}/`, { method: "DELETE" }); if (response.ok) reload(); }
  if (!isMainManager) return <p className="error">Only the main manager can remove managers.</p>;
  return <><div className="manager-page-title"><div><p className="manager-eyebrow">ACCESS CONTROL</p><h1>Managers</h1></div></div><ResultMessage error={error} />{busy ? <p>Loading managers...</p> : <section className="manager-panel">{(data || []).map((m) => <p key={m.id}>{m.username} · {m.email}<span>{m.is_main ? "Main manager" : "Invited manager"}</span>{!m.is_main && <button className="manager-danger-link" onClick={() => remove(m)}>Remove access</button>}</p>)}</section>}</>;
}

function Pager({ data, page, setPage }) { return data?.count > 20 && <div className="manager-pager"><button disabled={!data.previous} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page}</span><button disabled={!data.next} onClick={() => setPage(page + 1)}>Next</button></div>; }

function ManagerLayout() {
  const { isMainManager, logout } = useAuth(); const navigate = useNavigate();
  return <div className="manager-shell"><aside className="manager-sidebar"><Link className="manager-brand" to="/manager">Urban Nest <small>MANAGEMENT</small></Link><nav><Link to="/manager">Overview</Link><Link to="/manager/apartments">Apartments</Link><Link to="/manager/bookings">Bookings</Link><Link to="/manager/payments">Payments</Link><Link to="/manager/announcements">Announcements</Link><Link to="/manager/tenants">Tenants</Link>{isMainManager && <><span className="manager-nav-label">MAIN MANAGER</span><Link to="/manager/managers">Managers</Link><Link to="/manager/invitations">Invitations</Link></>}</nav><button onClick={() => { logout(); navigate("/login"); }}>Log out</button></aside><main className="manager-content"><Routes><Route index element={<ManagerDashboard />} /><Route path="apartments" element={<ApartmentList />} /><Route path="apartments/new" element={<ApartmentForm />} /><Route path="apartments/:id/edit" element={<ApartmentForm />} /><Route path="bookings" element={<BookingList />} /><Route path="bookings/:id" element={<BookingDetail />} /><Route path="payments" element={<PaymentList />} /><Route path="announcements" element={<AnnouncementList />} /><Route path="tenants" element={<TenantList />} /><Route path="tenants/:id" element={<TenantDetail />} /><Route path="managers" element={<ManagersList />} /><Route path="invitations" element={<ManagerInvitations />} /><Route path="*" element={<Navigate to="/manager" replace />} /></Routes></main></div>;
}

export default function ManagerArea() { return <ManagerLayout />; }

export function InvitationAccept() {
  const { token } = useParams(); const { username } = useAuth(); const [state, setState] = useState({ busy: true, error: "", message: "" });
  useEffect(() => {
    if (!username) { setState({ busy: false, error: "", message: "Sign in with the invited email address to accept the invitation." }); return; }
    api(`/manager/invitations/accept/${token}/`, { method: "POST", body: JSON.stringify({}) }).then(async (response) => {
      const body = await response.json(); if (!response.ok) throw new Error(errorText(body));
      setState({ busy: false, error: "", message: body.detail });
      setTimeout(() => window.location.assign("/manager"), 600);
    }).catch((err) => setState({ busy: false, error: err.message, message: "" }));
  }, [token, username]);
  if (!username && !state.busy) return <section className="card narrow"><h2>Accept manager invitation</h2><p>{state.message}</p><Link className="manager-primary" to={`/login?next=${encodeURIComponent(`/manager/invitations/accept/${token}`)}`}>Log in to continue</Link><p>New to Urban Nest? <Link to={`/register?next=${encodeURIComponent(`/manager/invitations/accept/${token}`)}`}>Create an account with the invited email</Link></p></section>;
  return <section className="card narrow"><h2>Accept manager invitation</h2>{state.busy ? <p>Verifying invitation...</p> : <ResultMessage error={state.error} message={state.message} />}</section>;
}
