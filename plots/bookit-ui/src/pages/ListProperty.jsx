
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorText } from "../Api.js";

const counties = [
  "Kiambu",
  "Nairobi",
  "Nakuru",
  "Mombasa",
  "Machakos",
];

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

export default function ListProperty() {
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

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

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

  async function submitProperty(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (form.amenities.length === 0) {
      setError("Select at least one property amenity.");
      return;
    }

    setLoading(true);

    try {
      const response = await api("/my-houses/", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          bedrooms: Number(form.bedrooms),
          price_per_night: Number(form.price_per_night),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(errorText(data));
      }

      setSuccess(
        "Your property has been submitted successfully. It is now awaiting admin approval."
      );

      setForm({
        name: "",
        county: "",
        location: "",
        property_type: "",
        description: "",
        bedrooms: "1",
        price_per_night: "",
        amenities: [],
      });

    } catch (requestError) {
      setError(
        requestError.message || "Could not submit your property."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-4xl">

      <Link
        to="/houses"
        className="text-sm font-semibold text-nest-700 transition hover:text-nest-900"
      >
        ← Back to homes
      </Link>

      <div className="mb-8 mt-6">
        <p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">
          PROPERTY OWNERS
        </p>

        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          List your property
        </h1>

        <p className="mt-3 leading-7 text-muted">
          Share your property with people looking for a place to stay.
          Complete the details below to submit your listing for review.
        </p>
      </div>

      <form
        onSubmit={submitProperty}
        className="grid gap-7 rounded-2xl border border-line bg-white p-5 shadow-sm sm:p-8"
      >

        <div>
          <h2 className="text-lg font-semibold text-ink">
            Property information
          </h2>

          <p className="mt-1 text-sm text-muted">
            Tell us about the property you want to list.
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
              placeholder="e.g. Greenview Apartments"
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
              placeholder="e.g. Ruiru, near the bypass"
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
              placeholder="e.g. 2500"
              required
            />
          </label>

        </div>

        <div>
          <label className={labelClass}>
            Property description

            <textarea
              className="min-h-36 w-full resize-y rounded-xl border border-line bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal text-ink placeholder:text-muted/70 focus:border-nest-500 focus:outline-none focus:ring-4 focus:ring-nest-100"
              name="description"
              value={form.description}
              onChange={updateField}
              placeholder="Describe the property, its surroundings and what makes it a great place to stay..."
              required
              rows="5"
            />
          </label>
        </div>

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
          <p
            className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700"
            role="alert"
          >
            {error}
          </p>
        )}

        {success && (
          <div
            className="rounded-xl border border-emerald-100 bg-emerald-50 p-4"
            role="status"
          >
            <p className="text-sm leading-6 text-emerald-800">
              {success}
            </p>

            <button
              type="button"
              onClick={() => navigate("/my-properties")}
              className="mt-3 text-sm font-bold text-emerald-900 underline"
            >
              View my properties
            </button>
          </div>
        )}

        <div className="flex flex-col-reverse gap-3 border-t border-line pt-6 sm:flex-row sm:justify-end">

          <Link
            to="/houses"
            className="rounded-xl border border-line px-6 py-3 text-center text-sm font-semibold text-ink transition hover:bg-nest-50"
          >
            Cancel
          </Link>

          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-nest-800 px-7 py-3 text-sm font-semibold text-white transition hover:bg-nest-900 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Submitting..." : "Submit property"}
          </button>

        </div>

      </form>

      <p className="mt-5 text-center text-xs leading-6 text-muted">
        Your listing will remain private until it has been reviewed and approved
        by the Urban Nest administration team.
      </p>

    </section>
  );
}
