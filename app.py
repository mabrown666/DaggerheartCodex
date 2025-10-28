import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, abort

app = Flask(__name__)

# Data file
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "statblocks.json")

# Categories and types
CATEGORIES = {
    "Environments": ["Exploration", "Traversal", "Social", "Event"],
    "Adversaries": ["Solo", "Bruiser", "Leader", "Horde", "Ranged", "Skulk", "Standard", "Support", "Minion", "Social"],
}

TIERS = [1, 2, 3, 4]


def ensure_data():
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.isfile(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2)


def load_data():
    ensure_data()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    ensure_data()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_stat(data, name):
    name_lower = name.strip().lower()
    for s in data:
        if s.get('name', '').strip().lower() == name_lower:
            return s
    return None


@app.route('/')
def index():
    return render_template('lookup.html', categories=CATEGORIES, tiers=TIERS)


@app.route('/update')
def update():
    # If ?name= provided, client-side will fetch the stat via API
    return render_template('update.html', categories=CATEGORIES, tiers=TIERS)


@app.route('/api/types')
def api_types():
    category = request.args.get('category', '')
    types = CATEGORIES.get(category, [])
    return jsonify({'types': types})


@app.route('/api/search', methods=['POST'])
def api_search():
    data = load_data()
    payload = request.get_json() or {}
    category = (payload.get('category') or '').strip()
    tier = payload.get('tier')
    type_ = (payload.get('type') or '').strip()
    text = (payload.get('text') or '').strip().lower()

    results = []
    for s in data:
        if category and s.get('category') != category:
            continue
        if tier:
            try:
                if int(s.get('tier')) != int(tier):
                    continue
            except Exception:
                continue
        if type_ and s.get('type') != type_:
            continue
        if text:
            # Build a searchable string from all relevant fields
            haystack_fields = ['name', 'description', 'type']
            hay = ' '.join([str(s.get(field, '')) for field in haystack_fields]).lower()

            if s.get('category') == 'Adversaries':
                adversary_fields = ['motives_tactics']
                hay += ' ' + ' '.join([str(s.get(field, '')) for field in adversary_fields]).lower()
                weapon_fields = ['weapon', 'damage_type']
                hay += ' ' + ' '.join([str(s.get(field, '')) for field in weapon_fields]).lower()
            elif s.get('category') == 'Environments':
                environment_fields = ['impulses', 'potential_adversaries']
                hay += ' ' + ' '.join([str(s.get(field, '')) for field in environment_fields]).lower()

            # Include features in search
            for f in s.get('features', []):
                hay += f" {str(f.get('name','')).lower()} {str(f.get('description','')).lower()}"

            if text not in hay:
                continue

        results.append({
            'name': s.get('name', ''),
            'tier': s.get('tier', ''),
            'type': s.get('type', ''),
            'category': s.get('category', ''),
            'description': s.get('description','')
        })

    return jsonify({'results': results})


@app.route('/api/stat/<path:name>')
def api_stat(name):
    data = load_data()
    found = find_stat(data, name)
    if not found:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(found)


@app.route('/api/save', methods=['POST'])
def api_save():
    payload = request.get_json() or {}
    name = (payload.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400

    data = load_data()
    existing = find_stat(data, name)
    if existing:
        # overwrite
        data = [s for s in data if s.get('name','').strip().lower() != name.lower()]
    
    category = payload.get('category')
    stat = {}

    if category == 'Adversaries':
        stat = {
            'name': name,
            'category': category,
            'tier': payload.get('tier'),
            'type': payload.get('type'),
            'description': payload.get('description'),
            'motives_tactics': payload.get('motives_tactics'),
            'difficulty': payload.get('difficulty'),
            'thresholds': payload.get('thresholds'),
            'hp': payload.get('hp'),
            'stress': payload.get('stress'),
            'atk': payload.get('atk'),
            'weapon': payload.get('weapon'),
            'range': payload.get('range'),
            'damage_dice': payload.get('damage_dice'),
            'damage_type': payload.get('damage_type'),
            'experience': payload.get('experience'),
            'features': payload.get('features', [])
        }
    elif category == 'Environments':
        stat = {
            'name': name,
            'category': category,
            'tier': payload.get('tier'),
            'type': payload.get('type'),
            'description': payload.get('description'),
            'impulses': payload.get('impulses'),
            'difficulty': payload.get('difficulty'),
            'potential_adversaries': payload.get('potential_adversaries'),
            'features': payload.get('features', [])
        }

    data.append(stat)
    save_data(data)
    return jsonify({'saved': True})


if __name__ == '__main__':
    app.run(debug=True)
