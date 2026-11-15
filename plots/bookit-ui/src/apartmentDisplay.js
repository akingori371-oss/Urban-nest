const DEMO_MARKER = /^\[\[URBAN_NEST_DEMO\|ID=([A-Z0-9-]+)\|MONTHLY=(\d+)\|TYPE=([A-Za-z0-9-]+)\|RATING=([1-5]\.\d)\]\]\s*/;

export function demoApartmentInfo(house) {
  const match = DEMO_MARKER.exec(house?.description || "");
  if (!match) return null;
  return {
    id: match[1],
    monthlyRent: Number(match[2]),
    type: match[3],
    sampleRating: Number(match[4]),
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
  if (demo) {
    return {
      amount: demo.monthlyRent.toLocaleString("en-KE"),
      unit: "month",
      isDemo: true,
    };
  }
  return { amount: house.price_per_night, unit: "night", isDemo: false };
}

export function apartmentRatingLabel(house) {
  const demo = demoApartmentInfo(house);
  const realReview = Number.isFinite(house?.avg_rating) && house.avg_rating > 0
    ? `Guest rating ${house.avg_rating.toFixed(1)} · ${house.review_count} reviews`
    : (demo ? "No guest reviews yet" : "New to Urban Nest");
  if (demo) return `Fictional sample rating ★ ${demo.sampleRating.toFixed(1)} · ${realReview}`;
  return realReview;
}
