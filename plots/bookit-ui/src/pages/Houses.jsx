import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorText } from "../Api.js";
import { apartmentPrice, apartmentRatingLabel, apartmentTypeLabel, demoApartmentInfo } from "../apartmentDisplay.js";
import PhotoCarousel from "../components/PhotoCarousel.jsx";

export default function Houses() {
  const [params, setParams] = useSearchParams();
  const [houses, setHouses] = useState([]);
  const [count, setCount] = useState(0);
  const [checkIn, setCheckIn] = useState(params.get("check_in") || "");
  const [checkOut, setCheckOut] = useState(params.get("check_out") || "");
  const [search, setSearch] = useState(params.get("search") || "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const page = Math.max(1, Number(params.get("page") || 1));
  const pageCount = Math.max(1, Math.ceil(count / 20));

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const query = new URLSearchParams(params);
    query.set("page", String(page));
    try {
      const response = await api("/houses/?" + query.toString());
      const data = await response.json();
      if (!response.ok) throw new Error(errorText(data));
      if (!data || !Array.isArray(data.results) || !Number.isFinite(data.count)) {
        throw new Error("The server returned an unexpected home list response.");
      }
      setHouses(data.results);
      setCount(data.count || 0);
    } catch (requestError) {
      setHouses([]);
      setError(requestError.message || "Could not load homes.");
    } finally {
      setLoading(false);
    }
  }, [params, page]);

  useEffect(() => {
    const timer = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(timer);
  }, [load]);

  function searchHouses(event) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (checkIn && checkOut) {
      next.set("check_in", checkIn);
      next.set("check_out", checkOut);
    }
    if (search.trim()) next.set("search", search.trim());
    next.set("page", "1");
    setParams(next);
  }

  function goToPage(value) {
    const next = new URLSearchParams(params);
    next.set("page", String(value));
    setParams(next);
  }

  return (
    <section>
      <div className="mb-8"><p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">EXPLORE URBAN NEST</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Find your next stay</h1><p className="mt-2 text-muted">A good place to land, for as long as you need.</p></div>
      <form className="mb-9 grid gap-4 rounded-2xl border border-line bg-white p-5 shadow-sm sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1.5fr_auto] lg:items-end" onSubmit={searchHouses}>
        <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-muted">Check-in <input className="min-h-11 rounded-xl border border-line bg-nest-50/50 px-3 text-sm font-normal text-ink focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" type="date" value={checkIn} onChange={(event) => setCheckIn(event.target.value)} /></label>
        <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-muted">Check-out <input className="min-h-11 rounded-xl border border-line bg-nest-50/50 px-3 text-sm font-normal text-ink focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" type="date" value={checkOut} onChange={(event) => setCheckOut(event.target.value)} /></label>
        <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-muted">Search by name or area <input className="min-h-11 rounded-xl border border-line bg-nest-50/50 px-3 text-sm font-normal text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Neighbourhood, home name…" /></label>
        <button className="min-h-11 rounded-xl bg-nest-800 px-6 py-2.5 font-semibold text-white transition hover:bg-nest-900" type="submit">Search homes</button>
      </form>

      {loading && <p className="rounded-xl bg-white p-6 text-muted" role="status">Finding available homes…</p>}
      {error && <p className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>}
      {!loading && !error && houses.length === 0 && <p className="rounded-xl border border-dashed border-nest-300 p-8 text-center text-muted">No homes match those filters. Try different dates or another area.</p>}

      <div className="grid">
        {houses.map((house) => {
          const price = apartmentPrice(house);
          const demo = demoApartmentInfo(house);
          return (
          <article className="group flex flex-col overflow-hidden rounded-2xl border border-line bg-white p-5 shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-soft" key={house.id}>
            <PhotoCarousel className="mb-5" photos={house.photos} name={house.name} />
            <p className="text-xs font-bold uppercase tracking-wider text-nest-600">{apartmentTypeLabel(house)}</p>
            <h2 className="mt-1 text-xl font-semibold text-ink"><Link className="text-ink transition hover:text-nest-700" to={"/houses/" + house.id + "?" + params.toString()}>{house.name}</Link></h2>
            <p className="mt-1 text-sm text-muted">{house.location}</p>
            {demo && <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-nest-700">Fictional demonstration listing</p>}
            <p className="mt-3 text-sm text-amber-700">{apartmentRatingLabel(house)}</p>
            <div className="mt-auto flex items-end justify-between gap-3 border-t border-line pt-5"><p className="text-sm text-muted"><strong className="text-lg text-ink">KSh {price.amount}</strong> / {price.unit}</p><Link className="rounded-full bg-nest-100 px-4 py-2 text-sm font-semibold text-nest-800 transition hover:bg-nest-800 hover:text-white" to={"/houses/" + house.id + "?" + params.toString()}>View home <span aria-hidden="true">→</span></Link></div>
          </article>
          );
        })}
      </div>

      {!loading && !error && pageCount > 1 && (
        <nav className="mt-8 flex items-center justify-center gap-4" aria-label="Apartment pages">
          <button className="rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink transition hover:bg-nest-100 disabled:opacity-40" type="button" onClick={() => goToPage(page - 1)} disabled={page <= 1}>Previous</button>
          <span className="text-sm text-muted">Page {page} of {pageCount} · {count} homes</span>
          <button className="rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-ink transition hover:bg-nest-100 disabled:opacity-40" type="button" onClick={() => goToPage(page + 1)} disabled={page >= pageCount}>Next</button>
        </nav>
      )}
    </section>
  );
}

