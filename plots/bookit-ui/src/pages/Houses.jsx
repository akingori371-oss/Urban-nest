import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorText } from "../api.js";

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
      setHouses(data.results || []);
      setCount(data.count || 0);
    } catch (requestError) {
      setHouses([]);
      setError(requestError.message || "Could not load apartments.");
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
      <h2>Find an apartment</h2>
      <form className="row" onSubmit={searchHouses}>
        <label>Check-in <input type="date" value={checkIn} onChange={(event) => setCheckIn(event.target.value)} /></label>
        <label>Check-out <input type="date" value={checkOut} onChange={(event) => setCheckOut(event.target.value)} /></label>
        <label>Search <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, location, details" /></label>
        <button type="submit">Search</button>
      </form>

      {loading && <p role="status">Loading apartments...</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {!loading && !error && houses.length === 0 && <p>No apartments match your search.</p>}

      <div className="grid">
        {houses.map((house) => (
          <article className="card" key={house.id}>
            <h3><Link to={"/houses/" + house.id + "?" + params.toString()}>{house.name}</Link></h3>
            <p>{house.location} · {house.bedrooms} bedroom{house.bedrooms === 1 ? "" : "s"}</p>
            <p>{house.avg_rating ? "★ " + house.avg_rating.toFixed(1) + " (" + house.review_count + " reviews)" : "No reviews yet"}</p>
            <p><strong>KES {house.price_per_night}</strong> / night</p>
            <Link className="button-link" to={"/houses/" + house.id + "?" + params.toString()}>View details</Link>
          </article>
        ))}
      </div>

      {!loading && !error && pageCount > 1 && (
        <nav className="row" aria-label="Apartment pages">
          <button type="button" onClick={() => goToPage(page - 1)} disabled={page <= 1}>Previous</button>
          <span>Page {page} of {pageCount} · {count} apartments</span>
          <button type="button" onClick={() => goToPage(page + 1)} disabled={page >= pageCount}>Next</button>
        </nav>
      )}
    </section>
  );
}

