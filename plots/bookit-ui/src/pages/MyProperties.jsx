
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api, errorText } from "../Api.js";
import PhotoCarousel from "../components/PhotoCarousel.jsx";
import { apartmentPrice, apartmentTypeLabel } from "../apartmentDisplay.js";

function StatusBadge({ status }) {
  const styles = {
    pending: "bg-amber-50 text-amber-800",
    approved: "bg-emerald-50 text-emerald-800",
    rejected: "bg-red-50 text-red-700",
  };

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-bold capitalize ${styles[status] || "bg-gray-100 text-gray-700"}`}>
      {status || "Unknown"}
    </span>
  );
}

export default function MyProperties() {
  const [houses, setHouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionId, setActionId] = useState(null);
  const [message, setMessage] = useState("");

  const location = useLocation();

  const loadProperties = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api("/my-houses/");
      const data = await response.json();

      if (!response.ok) throw new Error(errorText(data));
      if (!Array.isArray(data)) {
        throw new Error("The server returned an unexpected property list.");
      }

      setHouses(data);
    } catch (requestError) {
      setError(requestError.message || "Could not load your properties.");
      setHouses([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProperties();
  }, [loadProperties, location.key]);

  async function toggleProperty(house) {
    const action = house.is_active ? "deactivate" : "activate";

    const confirmed = window.confirm(
      `Are you sure you want to ${action} "${house.name}"?`
    );

    if (!confirmed) return;

    setActionId(house.id);
    setError("");
    setMessage("");

    try {
      const response = await api(`/my-houses/${house.id}/toggle/`, {
        method: "POST",
        body: JSON.stringify({
          is_active: !house.is_active,
        }),
      });

      const data = await response.json();

      if (!response.ok) throw new Error(errorText(data));

      setHouses((previous) =>
        previous.map((item) =>
          item.id === house.id
            ? { ...item, is_active: !house.is_active }
            : item
        )
      );

      setMessage(`${house.name} has been ${action}d successfully.`);
    } catch (requestError) {
      setError(requestError.message || `Could not ${action} property.`);
    } finally {
      setActionId(null);
    }
  }

  return (
    <section>
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">
            PROPERTY MANAGEMENT
          </p>

          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            My properties
          </h1>

          <p className="mt-2 text-muted">
            View and manage the properties you've submitted to Urban Nest.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={loadProperties}
            disabled={loading}
            className="rounded-xl border border-line bg-white px-5 py-3 text-sm font-semibold text-nest-800 transition hover:bg-nest-50 disabled:opacity-50"
          >
            {loading ? "Refreshing..." : "Refresh status"}
          </button>

          <Link
            to="/list-property"
            className="rounded-xl bg-nest-800 px-5 py-3 text-center text-sm font-semibold text-white transition hover:bg-nest-900"
          >
            + List a property
          </Link>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Total properties", value: houses.length },
          { label: "Approved", value: houses.filter((h) => h.approval_status === "approved").length },
          { label: "Pending", value: houses.filter((h) => h.approval_status === "pending").length },
          { label: "Rejected", value: houses.filter((h) => h.approval_status === "rejected").length },
        ].map((item) => (
          <div key={item.label} className="rounded-2xl border border-line bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              {item.label}
            </p>
            <p className="mt-2 text-2xl font-bold text-ink">
              {item.value}
            </p>
          </div>
        ))}
      </div>

      {error && (
        <p className="mb-5 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      {message && (
        <p className="mb-5 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800" role="status">
          {message}
        </p>
      )}

      {loading && (
        <p className="rounded-xl bg-white p-6 text-muted" role="status">
          Loading your properties...
        </p>
      )}

      {!loading && !error && houses.length === 0 && (
        <div className="rounded-2xl border border-dashed border-nest-300 bg-white p-10 text-center">
          <h2 className="text-xl font-semibold text-ink">
            No properties yet
          </h2>

          <p className="mt-2 text-sm text-muted">
            You haven't submitted any properties. Start by listing your first property.
          </p>

          <Link
            to="/list-property"
            className="mt-5 inline-block rounded-xl bg-nest-800 px-6 py-3 text-sm font-semibold text-white transition hover:bg-nest-900"
          >
            List your property
          </Link>
        </div>
      )}

      {!loading && houses.length > 0 && (
        <div className="grid gap-6 md:grid-cols-2">
          {houses.map((house) => {
            const price = apartmentPrice(house);

            return (
              <article
                key={house.id}
                className="overflow-hidden rounded-2xl border border-line bg-white p-5 shadow-sm transition hover:shadow-soft"
              >
                <PhotoCarousel
                  className="mb-5"
                  photos={house.photos}
                  name={house.name}
                />

                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-nest-600">
                    {apartmentTypeLabel(house)}
                  </span>

                  <StatusBadge status={house.approval_status} />
                </div>

                <h2 className="mt-2 text-xl font-semibold text-ink">
                  {house.name}
                </h2>

                <p className="mt-1 text-sm text-muted">
                  {house.location}, {house.county}
                </p>

                <p className="mt-3 text-lg font-semibold text-ink">
                  KSh {price.amount}
                  <span className="text-sm font-normal text-muted">
                    {" "}/ {price.unit}
                  </span>
                </p>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-4">
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    house.is_active
                      ? "bg-emerald-50 text-emerald-800"
                      : "bg-gray-100 text-gray-600"
                  }`}>
                    {house.is_active ? "Active" : "Inactive"}
                  </span>

                  <div className="flex flex-wrap gap-2">
                    <Link
                      to={`/edit-property/${house.id}`}
                      className="rounded-full border border-line px-4 py-2 text-sm font-semibold text-nest-800 transition hover:bg-nest-50"
                    >
                      Edit
                    </Link>

                    <button
                      type="button"
                      onClick={() => toggleProperty(house)}
                      disabled={actionId === house.id}
                      className="rounded-full bg-nest-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-nest-900 disabled:opacity-50"
                    >
                      {actionId === house.id
                        ? "Please wait..."
                        : house.is_active
                          ? "Deactivate"
                          : "Activate"}
                    </button>
                  </div>
                </div>

                {house.approval_status === "pending" && (
                  <p className="mt-3 text-xs leading-5 text-amber-700">
                    Your property is awaiting admin approval.
                  </p>
                )}

                {house.approval_status === "approved" && (
                  <p className="mt-3 text-xs leading-5 text-emerald-700">
                    Your property has been approved.
                  </p>
                )}

                {house.approval_status === "rejected" && (
                  <p className="mt-3 text-xs leading-5 text-red-700">
                    This property was rejected. You can edit it and submit it for review again.
                  </p>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
