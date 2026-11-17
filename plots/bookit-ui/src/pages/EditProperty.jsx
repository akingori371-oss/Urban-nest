
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, errorText } from "../Api.js";

const counties = ["Kiambu", "Nairobi", "Nakuru", "Mombasa", "Machakos"];

const propertyTypes = [
  "Apartment",
  "Bedsitter",
  "Studio",
  "House",
  "Villa",
  "Townhouse",
];

const availableAmenities = [
  "Wi-Fi",
  "Parking",
  "Swimming pool",
  "Kitchen",
  "Hot water",
  "Security",
  "Laundry",
  "Balcony",
  "Furnished",
  "Garden",
];

const inputClass =
  "min-h-11 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100";

const labelClass =
  "grid gap-2 text-xs font-bold uppercase tracking-wider text-muted";

export default function EditProperty() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "",
    county: "",
    location: "",
    property_type: "",
    description: "",
    bedrooms: "1",
    price_per_night: "",
    amenities: [],
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [house, setHouse] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadProperty() {
      setLoading(true);
      setError("");

      try {
        const response = await api(`/my-houses/${id}/`);
        const data = await response.json();

        if (!response.ok) throw new Error(errorText(data));

        if (cancelled) return;

        setHouse(data);

        setForm({
          name: data.name || "",
          county: data.county || "",
          location: data.location || "",
          property_type: data.property_type || "",
          description: data.description || "",
          bedrooms: String(data.bedrooms ?? 1),
          price_per_night: String(data.price_per_night ?? ""),
          amenities: Array.isArray(data.amenities) ? data.amenities : [],
        });
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError.message || "Could not load this property.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadProperty();

    return () => {
      cancelled = true;
    };
  }, [id]);

  function updateField(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  function toggleAmenity(amenity) {
    setForm((previous) => ({
      ...previous,
      amenities: previous.amenities.includes(amenity)
        ? previous.amenities.filter((item) => item !== amenity)
        : [...previous.amenities, amenity],
    }));
  }

  async function saveChanges(event) {
    event.preventDefault();
    setError("");

    if (form.amenities.length === 0) {
      setError("Select at least one property amenity.");
      return;
    }

    setSaving(true);

    try {
      const response = await api(`/my-houses/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({
          ...form,
          bedrooms: Number(form.bedrooms),
          price_per_night: Number(form.price_per_night),
        }),
      });

      const data = await response.json();

      if (!response.ok) throw new Error(errorText(data));

      navigate("/my-properties", {
        state: {
          message: "Property updated successfully. It is now awaiting admin approval.",
        },
      });
    } catch (requestError) {
      setError(requestError.message || "Could not update this property.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <p className="py-12 text-muted" role="status">
        Loading property details...
      </p>
    );
  }

  if (error && !house) {
    return (
      <section>
        <p className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700" role="alert">
          {error}
        </p>

        <Link
          to="/my-properties"
          className="mt-5 inline-block text-sm font-semibold text-nest-700"
        >
          ← Back to my properties
        </Link>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-4xl">

      <Link
        to="/my-properties"
        className="text-sm font-semibold text-nest-700 transition hover:text-nest-900"
      >
        ← Back to my properties
      </Link>

      <div className="mb-8 mt-6">
        <p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">
          PROPERTY MANAGEMENT
        </p>

        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          Edit property
        </h1>

        <p className="mt-3 text-muted">
          Update the details of {house?.name}.
        </p>
      </div>

      <form
        onSubmit={saveChanges}
        className="grid gap-7 rounded-2xl border border-line bg-white p-5 shadow-sm sm:p-8"
      >

        <div>
          <h2 className="text-lg font-semibold text-ink">
            Property information
          </h2>

          <p className="mt-1 text-sm text-muted">
            Make the necessary changes to your property listing.
          </p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">

          <label className={labelClass}>
            Property name

            <input
              className={inputClass}
              name="name"
              value={form.name}
              onChange={updateField}
              required
              maxLength={200}
            />
          </label>

          <label className={labelClass}>
            County

            <select
              className={inputClass}
              name="county"
              value={form.county}
              onChange={updateField}
              required
            >
              <option value="">Select county</option>

              {counties.map((county) => (
                <option key={county} value={county}>
                  {county}
                </option>
              ))}
            </select>
          </label>

          <label className={labelClass}>
            Specific location

            <input
              className={inputClass}
              name="location"
              value={form.location}
              onChange={updateField}
              required
            />
          </label>

          <label className={labelClass}>
            Property type

            <select
              className={inputClass}
              name="property_type"
              value={form.property_type}
              onChange={updateField}
              required
            >
              <option value="">Select property type</option>

              {propertyTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>

          <label className={labelClass}>
            Number of bedrooms

            <input
              className={inputClass}
              type="number"
              name="bedrooms"
              min="0"
              max="100"
              value={form.bedrooms}
              onChange={updateField}
              required
            />
          </label>

          <label className={labelClass}>
            Price per night (KSh)

            <input
              className={inputClass}
              type="number"
              name="price_per_night"
              min="1"
              step="0.01"
              value={form.price_per_night}
              onChange={updateField}
              required
            />
          </label>

        </div>

        <label className={labelClass}>
          Property description

          <textarea
            className="min-h-36 w-full resize-y rounded-xl border border-line bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal text-ink focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100"
            name="description"
            value={form.description}
            onChange={updateField}
            rows="5"
            required
          />
        </label>

        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted">
            Property amenities
          </h2>

          <p className="mb-4 mt-1 text-sm text-muted">
            Select all amenities available at your property.
          </p>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {availableAmenities.map((amenity) => (
              <label
                key={amenity}
                className={`flex cursor-pointer items-center gap-2 rounded-xl border p-3 text-sm transition ${
                  form.amenities.includes(amenity)
                    ? "border-nest-500 bg-nest-50 text-nest-900"
                    : "border-line bg-white text-muted hover:bg-nest-50"
                }`}
              >
                <input
                  type="checkbox"
                  checked={form.amenities.includes(amenity)}
                  onChange={() => toggleAmenity(amenity)}
                  className="size-4 accent-nest-800"
                />

                {amenity}
              </label>
            ))}
          </div>
        </div>

        {error && (
          <p className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        <div className="rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-800">
          Saving changes will send this property back for admin approval.
          It will not appear in public listings until approved again.
        </div>

        <div className="flex flex-col-reverse gap-3 border-t border-line pt-6 sm:flex-row sm:justify-end">

          <Link
            to="/my-properties"
            className="rounded-xl border border-line px-6 py-3 text-center text-sm font-semibold text-ink transition hover:bg-nest-50"
          >
            Cancel
          </Link>

          <button
            type="submit"
            disabled={saving}
            className="rounded-xl bg-nest-800 px-7 py-3 text-sm font-semibold text-white transition hover:bg-nest-900 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Saving changes..." : "Save changes"}
          </button>

        </div>

      </form>
    </section>
  );
}
