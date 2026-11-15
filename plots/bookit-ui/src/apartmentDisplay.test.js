import assert from "node:assert/strict";
import { test } from "node:test";
import {
  apartmentPrice,
  apartmentRatingLabel,
  apartmentTypeLabel,
  demoApartmentInfo,
  visibleApartmentDescription,
} from "./apartmentDisplay.js";

test("fictional demo metadata displays monthly rent and supplied type without changing nightly prices", () => {
  const demoHouse = {
    bedrooms: 0,
    price_per_night: "2166.67",
    description: "[[URBAN_NEST_DEMO|ID=NBI-01|MONTHLY=65000|TYPE=2-bedroom|RATING=4.8]] Fictional demo listing.",
    avg_rating: null,
    review_count: 0,
  };

  assert.deepEqual(demoApartmentInfo(demoHouse), {
    id: "NBI-01",
    monthlyRent: 65000,
    type: "2-bedroom",
    sampleRating: 4.8,
  });
  assert.deepEqual(apartmentPrice(demoHouse), { amount: "65,000", unit: "month", isDemo: true });
  assert.equal(apartmentTypeLabel(demoHouse), "2-bedroom");
  assert.equal(visibleApartmentDescription(demoHouse), "Fictional demo listing.");
  assert.match(apartmentRatingLabel(demoHouse), /Fictional sample rating/);
  assert.match(apartmentRatingLabel(demoHouse), /No guest reviews yet/);
});

test("ordinary apartments retain the current nightly price and real-review label", () => {
  const house = {
    bedrooms: 2,
    price_per_night: "2500.00",
    description: "A regular listing.",
    avg_rating: 4.5,
    review_count: 2,
  };

  assert.equal(demoApartmentInfo(house), null);
  assert.deepEqual(apartmentPrice(house), { amount: "2500.00", unit: "night", isDemo: false });
  assert.equal(apartmentTypeLabel(house), "2 bedrooms");
  assert.equal(apartmentRatingLabel(house), "Guest rating 4.5 · 2 reviews");
});
