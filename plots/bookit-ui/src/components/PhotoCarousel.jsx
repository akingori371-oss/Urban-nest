import { useState } from "react";

function orderedPhotos(photos) {
  if (!Array.isArray(photos)) return [];
  return [...photos]
    .filter((photo) => photo?.image)
    .sort((a, b) => {
      const rank = (photo) => {
        const caption = String(photo.caption || "").toLowerCase();
        if (caption.includes("interior")) return 0;
        if (caption.includes("exterior")) return 1;
        return 2;
      };
      return rank(a) - rank(b) || (a.id || 0) - (b.id || 0);
    })
    .slice(0, 2);
}

export default function PhotoCarousel({ photos, name, className = "" }) {
  const images = orderedPhotos(photos);
  const [index, setIndex] = useState(0);
  const current = images.length ? images[index % images.length] : null;

  if (!current) {
    return <div className={`grid aspect-[16/9] place-items-center rounded-xl bg-gradient-to-br from-nest-100 via-[#edf0e6] to-[#d8e3d7] text-sm font-medium text-nest-700 ${className}`} role="img" aria-label={`No photos available for ${name}`}>
      Photos coming soon
    </div>;
  }

  const change = (direction) => setIndex((value) => (value + direction + images.length) % images.length);
  return <div className={`relative aspect-[16/9] overflow-hidden rounded-xl bg-nest-100 ${className}`} aria-label={`${name} photos`}>
    <img className="size-full object-cover" src={current.image} alt={current.caption ? `${name} ${current.caption}` : `${name} property photo`} loading="lazy" />
    {images.length > 1 && <>
      <button className="absolute left-3 top-1/2 grid size-10 -translate-y-1/2 place-items-center rounded-full bg-black/55 text-xl text-white shadow hover:bg-black/75 focus-visible:outline-white" type="button" onClick={() => change(-1)} aria-label={`Previous photo of ${name}`}>‹</button>
      <button className="absolute right-3 top-1/2 grid size-10 -translate-y-1/2 place-items-center rounded-full bg-black/55 text-xl text-white shadow hover:bg-black/75 focus-visible:outline-white" type="button" onClick={() => change(1)} aria-label={`Next photo of ${name}`}>›</button>
      <span className="absolute bottom-3 right-3 rounded-full bg-black/65 px-2.5 py-1 text-xs font-semibold text-white" aria-live="polite">{(index % images.length) + 1} / {images.length}</span>
    </>}
  </div>;
}
