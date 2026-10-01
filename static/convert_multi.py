from deep_translator import GoogleTranslator
import json, copy
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_THREADS = 10  # Tune for performance

# --- Load data ---
with open("country_regions.json", "rb") as file_data:
    data = file_data.read().decode("utf-8", errors="ignore")

jsn = json.loads(data)
res = copy.deepcopy(jsn)

# --- Collect all translation tasks ---
tasks = []
for country_idx, country in enumerate(jsn):
    for region_idx, region in enumerate(country["regions"]):
        tasks.append((country_idx, region_idx, region["name"]))

total_tasks = len(tasks)
print(f"Total regions to translate: {total_tasks}")

# --- Worker ---
def translate_region(country_idx, region_idx, text):
    try:
        translator = GoogleTranslator(target="en")  # new instance per thread
        translated = translator.translate(text)
        return country_idx, region_idx, translated
    except Exception as e:
        print(f"❌ Error translating '{text}': {e}")
        return country_idx, region_idx, text

# --- Execute threads with live progress ---
completed = 0
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = [executor.submit(translate_region, *t) for t in tasks]

    for future in as_completed(futures):
        country_idx, region_idx, translated = future.result()
        res[country_idx]["regions"][region_idx]["name"] = translated

        completed += 1
        progress = (completed / total_tasks) * 100
        print(f"Progress: {progress:.2f}%", end="\r")

print("\n✅ Translation completed. Saving file...")

# --- Save output ---
with open("country_regions_translated.json", "w", encoding="utf-8") as file_data:
    json.dump(res, file_data, ensure_ascii=False, indent=2)

print("✅ Saved to 'country_regions_translated.json'")
