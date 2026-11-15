const DEMO_MARKER = /^\[\[URBAN_NEST_DEMO\|ID=([A-Z0-9-]+)\|(?:NIGHTLY|MONTHLY)=\d+\|TYPE=([A-Za-z0-9-]+)\|RATING=([1-5]\.\d)\]\]\s*/;

export function formatKsh(value) {
  return new Intl.NumberFormat("en-KE", { maximumFractionDigits: 0 }).format(Number(value));
}

export function demoApartmentInfo(house) {
  const match = DEMO_MARKER.exec(house?.description || "");
  if (!match) return null;
  return {
    id: match[1],
    type: match[2],
    sampleRating: Number(match[3]),
  };
}

export function demoApartmentMarker(house) {
  const match = DEMO_MARKER.exec(house?.description || "");
  return match ? match[0].trim() : "";
}

export function visibleApartmentDescription(house) {
  return (house?.description || "").replace(DEMO_MARKER, "").trim();
}

export function apartmentTypeLabel(house) {
  const demo = demoApartmentInfo(house);
  if (demo) return demo.type;
  return `${house.bedrooms} bedroom${house.bedrooms === 1 ? "" : "s"}`;
}

export function apartmentPrice(house) {
  const demo = demoApartmentInfo(house);
  return {
    amount: formatKsh(house.price_per_night),
    unit: "night",
    isDemo: Boolean(demo),
  };
}

export function apartmentRatingLabel(house) {
  const demo = demoApartmentInfo(house);
  const realReview = Number.isFinite(house?.avg_rating) && house.avg_rating > 0
    ? `Guest rating ${house.avg_rating.toFixed(1)} · ${house.review_count} reviews`
    : (demo ? "No guest reviews yet" : "New to Urban Nest");
  if (demo) return `Fictional sample rating ★ ${demo.sampleRating.toFixed(1)} · ${realReview}`;
  return realReview;
}
