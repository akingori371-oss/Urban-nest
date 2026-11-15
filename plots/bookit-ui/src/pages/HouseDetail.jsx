import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, errorText } from "../Api.js";
import { apartmentPrice, apartmentRatingLabel, apartmentTypeLabel, demoApartmentInfo, visibleApartmentDescription } from "../apartmentDisplay.js";
import PhotoCarousel from "../components/PhotoCarousel.jsx";

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
      if (!data || !Number.isInteger(data.id) || typeof data.name !== "string") {
        throw new Error("The server returned an unexpected home details response.");
      }
      setHouse(data);
    } catch (requestError) {
      setHouse(null);
      setError(requestError.message || "Could not load this home.");
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
      setError("This home is unavailable for those dates. Choose another date range.");
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
  const price = house ? apartmentPrice(house) : null;
  const demo = house ? demoApartmentInfo(house) : null;

  return (
    <section>
      <p className="mb-6"><Link className="text-sm font-semibold text-nest-700 hover:text-nest-900" to={back}>← Back to homes</Link></p>
      {loading && <p className="py-12 text-muted" role="status">Loading home…</p>}
      {error && !house && <p className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>}
      {house && (
        <article className="overflow-hidden rounded-[1.75rem] border border-line bg-white shadow-sm">
          <PhotoCarousel className="rounded-none sm:aspect-[2/1] sm:rounded-none" photos={house.photos} name={house.name} />
          <div className="grid gap-5 p-6 sm:p-9 lg:grid-cols-[1fr_320px] lg:gap-10">
          <div><p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">{apartmentTypeLabel(house)} · {house.location}</p><h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{house.name}</h1>
          <p className="mt-5 text-2xl font-semibold text-ink">KSh {price.amount}<span className="text-sm font-normal text-muted"> / {price.unit}</span></p>
          {demo && <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-nest-700">Fictional demonstration listing</p>}
          <p className="mt-5 leading-7 text-muted">{visibleApartmentDescription(house) || "No description is available."}</p>
          <p className="mt-4 text-sm text-amber-700">{apartmentRatingLabel(house)}</p>
          </div>

          <aside className="h-fit rounded-2xl border border-line bg-nest-50/70 p-5">
          <form className="grid gap-3" onSubmit={updateDates}>
            <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-muted">Check-in <input className="min-h-11 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" type="date" value={checkIn} onChange={(event) => setCheckIn(event.target.value)} /></label>
            <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-muted">Check-out <input className="min-h-11 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100" type="date" value={checkOut} onChange={(event) => setCheckOut(event.target.value)} /></label>
            <button className="rounded-xl border border-nest-300 bg-white px-4 py-2.5 text-sm font-semibold text-nest-800 transition hover:bg-nest-100" type="submit">Check availability</button>
          </form>
          {house.availability === true && <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">Available for these dates.</p>}
          {house.availability === false && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">Unavailable for these dates.</p>}
          {message && <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{message}</p>}
          {error && house && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}
          <button className="mt-3 w-full rounded-xl bg-nest-800 px-4 py-3 font-semibold text-white transition hover:bg-nest-900 disabled:cursor-not-allowed disabled:opacity-50" type="button" onClick={createBooking} disabled={booking || loading || house.availability === false}>
            {booking ? "Booking..." : "Book this home"}
          </button>
          </aside>

          {house.reviews?.length > 0 && (
            <section className="lg:col-span-2">
              <h2 className="text-xl font-semibold text-ink">Guest reviews</h2>
              {house.reviews.map((review, index) => (
                <blockquote className="mt-3 rounded-xl border border-line bg-nest-50 p-4 text-sm" key={index}>
                  <strong className="text-amber-700">★ {review.rating}/5</strong>
                  <p className="mt-2 text-muted">{review.comment || "No written comment."}</p>
                </blockquote>
              ))}
            </section>
          )}
          </div>
        </article>
      )}
    </section>
  );
}

