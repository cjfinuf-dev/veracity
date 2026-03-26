"""
Vera Module Freshener — New-knowledge integrator

Runs daily after the knowledge gatherer. Checks for knowledge entries added today,
maps them to relevant modules, and integrates new information into enhanced-modules.json.

Only touches modules that already have enhanced data. Does NOT overwrite existing
content -- appends new sources and detail bullets where relevant.

Scheduled: Daily at 10:00 AM (after vera_module_enhancer.py)
"""

import json
import os
import re
import sys
import logging
from datetime import datetime, date

# -- Paths --
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
KNOWLEDGE_FILE = os.path.join(DATA_DIR, 'vera-knowledge.json')
ASU_FILE = os.path.join(DATA_DIR, 'asu-knowledge.json')
ENHANCED_FILE = os.path.join(DATA_DIR, 'enhanced-modules.json')
LOG_DIR = os.path.join(ROOT, 'scripts', 'logs')

os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f'freshener_{date.today().isoformat()}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('vera_freshener')

# Import module definitions from the enhancer
from vera_module_enhancer import MODULES, score_entry_for_module, build_sources, simplify_text


def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return [] if path.endswith('knowledge.json') else {}


def get_todays_entries():
    """Get all knowledge entries added today."""
    today = date.today().isoformat()
    entries = []
    for path in [KNOWLEDGE_FILE, ASU_FILE]:
        data = load_json(path)
        if isinstance(data, list):
            for entry in data:
                if entry.get('_date') == today:
                    entries.append(entry)
    log.info(f"Found {len(entries)} knowledge entries added today ({today})")
    return entries


def map_entries_to_modules(new_entries):
    """Map each new entry to the modules it's most relevant to."""
    module_updates = {}  # module_id -> list of entries

    for entry in new_entries:
        best_module = None
        best_score = 0

        for module in MODULES:
            score = score_entry_for_module(entry, module)
            if score > best_score:
                best_score = score
                best_module = module

        if best_module and best_score >= 3:  # Minimum relevance threshold
            mid = best_module['id']
            if mid not in module_updates:
                module_updates[mid] = []
            module_updates[mid].append(entry)

    return module_updates


def integrate_new_knowledge(enhanced, module_updates):
    """Integrate new knowledge entries into existing enhanced modules."""
    updated_count = 0

    for module_id, new_entries in module_updates.items():
        if module_id not in enhanced:
            log.info(f"  Skipping {module_id} -- not yet enhanced")
            continue

        mod_data = enhanced[module_id]
        module_def = next((m for m in MODULES if m['id'] == module_id), None)
        if not module_def:
            continue

        log.info(f"  Updating {module_id} with {len(new_entries)} new entries")

        # Add new sources
        existing_urls = {s['url'] for s in mod_data.get('sources', [])}
        new_sources = build_sources(new_entries)
        for source in new_sources:
            if source['url'] not in existing_urls:
                mod_data.setdefault('sources', []).append(source)
                existing_urls.add(source['url'])

        # Try to add new detail bullets to concepts
        for concept in mod_data.get('concepts', []):
            concept_name = concept.get('term', '').lower()
            existing_details = set(concept.get('details', []))

            for entry in new_entries:
                entry_text = ' '.join(entry.get('patterns', [])).lower()
                response = entry.get('response', '')

                # Check if this entry is relevant to this concept
                if concept_name in entry_text or any(concept_name in p.lower() for p in entry.get('patterns', [])):
                    # Extract a useful sentence
                    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', response) if len(s.strip()) > 30]
                    for sent in sentences[:1]:
                        clean = simplify_text(sent, 200)
                        if clean and clean not in existing_details:
                            concept.setdefault('details', []).append(clean)
                            existing_details.add(clean)
                            break

            # Cap details at 6 per concept
            if len(concept.get('details', [])) > 6:
                concept['details'] = concept['details'][:6]

            # Add new concept-level sources
            concept_sources_urls = {s['url'] for s in concept.get('sources', [])}
            for entry in new_entries:
                url = entry.get('_url', '')
                if url and url not in concept_sources_urls:
                    entry_text = ' '.join(entry.get('patterns', [])).lower()
                    if concept_name in entry_text:
                        new_src = build_sources([entry])
                        for s in new_src:
                            if s['url'] not in concept_sources_urls:
                                concept.setdefault('sources', []).append(s)
                                concept_sources_urls.add(s['url'])

        # Cap module-level sources at 15
        if len(mod_data.get('sources', [])) > 15:
            mod_data['sources'] = mod_data['sources'][:15]

        mod_data['lastFreshened'] = date.today().isoformat()
        enhanced[module_id] = mod_data
        updated_count += 1

    return updated_count


def main():
    log.info("=" * 60)
    log.info(f"Vera Module Freshener -- {datetime.now().isoformat()}")
    log.info("=" * 60)

    new_entries = get_todays_entries()
    if not new_entries:
        log.info("No new entries today. Nothing to freshen.")
        return 0

    module_updates = map_entries_to_modules(new_entries)
    log.info(f"Mapped entries to {len(module_updates)} modules: {list(module_updates.keys())}")

    if not module_updates:
        log.info("No entries met the relevance threshold. Done.")
        return 0

    enhanced = load_json(ENHANCED_FILE) if os.path.exists(ENHANCED_FILE) else {}
    if not enhanced:
        log.info("No enhanced modules yet. Run vera_module_enhancer.py first.")
        return 0

    updated = integrate_new_knowledge(enhanced, module_updates)

    if updated > 0:
        with open(ENHANCED_FILE, 'w', encoding='utf-8') as f:
            json.dump(enhanced, f, indent=2, ensure_ascii=False)
        log.info(f"Freshened {updated} modules with new knowledge.")
    else:
        log.info("No modules needed updating.")

    log.info("Freshener complete.")
    return updated


if __name__ == '__main__':
    try:
        result = main()
        sys.exit(0)
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
