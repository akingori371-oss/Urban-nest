
from pathlib import Path
from django.core.files import File
from plots.models import House, HousePhoto

PHOTO_DIR = Path("../../Urban-nest-interior").resolve()

image_files = sorted(
    p for p in PHOTO_DIR.rglob("*")
    if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
)

house_ids = [
    1, 2, 3, 4, 5,
    11, 12, 13, 14, 15,
    21, 22, 23, 24, 25,
    31, 32, 33, 34, 35,
    41, 42, 43, 44, 45
]

if not image_files:
    raise ValueError("No images found.")

missing = [
    pk for pk in house_ids
    if not House.objects.filter(pk=pk).exists()
]

if missing:
    raise ValueError(f"Missing properties: {missing}")

uploaded = 0
skipped = 0

for index, house_id in enumerate(house_ids):
    path = image_files[index % len(image_files)]

    if HousePhoto.objects.filter(
        house_id=house_id,
        caption=path.name
    ).exists():
        skipped += 1
        continue

    house = House.objects.get(pk=house_id)

    with path.open("rb") as image_file:
        HousePhoto.objects.create(
            house=house,
            image=File(image_file, name=path.name),
            caption=path.name
        )

    uploaded += 1
    print(f"Uploaded {path.name} -> House {house_id}")

print(f"Finished! Uploaded: {uploaded}, Skipped: {skipped}")