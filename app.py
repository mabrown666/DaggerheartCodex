import os
import json
import shutil
import re
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
        default_file = os.path.join(DATA_DIR, "statblocks_default.json")
        if os.path.isfile(default_file):
            shutil.copy(default_file, DATA_FILE)
        else:
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

def revalue_dice(dice_str, old_tier, new_tier):
    "Ppdates dice roll description based on a tier change."
    dice_regex = r'^(\d+)d(\d+)([+-]\d+)?$'
    match = re.match(dice_regex, dice_str.strip().lower())
    if match:
        num_dice = int(match.group(1))
        dice_size = int(match.group(2))
        modifier_str = match.group(3)
        modifier = int(modifier_str) if modifier_str else 0
        num_dice=int((num_dice / old_tier) * new_tier)
        num_dice=1 if num_dice<1 else num_dice
        modifier=0 if modifier==0 else int((modifier / old_tier) * new_tier)
        if modifier==0:
            dice_str = f"{int(num_dice)}d{dice_size}"
        else:
            dice_str = f"{int(num_dice)}d{dice_size}{'+' if modifier > 0 else ''}{modifier}"
    elif int(dice_str)>0:
        d=int((int(dice_str)/old_tier) * new_tier)
        dice_str=f"{d}"
    return dice_str

def retier(stat, new_tier):
    """Placeholder function to perform re-tier calculations."""
    thresholds_regex = r'^(\d+)/(\d+)$'
    if stat:
        if stat['category']!='Adversaries':
            return None
        old_tier = stat.get('tier')
        if not old_tier:
            return None
        stat['tier'] = new_tier
        new_tier=int(new_tier)
        old_tier=int(old_tier)
        tier_dif=int(new_tier) - int(old_tier)
        if tier_dif==0:
            return None
        tier_change_text=["Inferior", "Lesser", "Small", "" , "Large", "Greater", "Superior"][(int(new_tier) - int(old_tier))+3]
        stat['name'] = f"{tier_change_text} {stat['name']}"
        stat['damage_dice'] = revalue_dice(stat['damage_dice'], old_tier, new_tier)
        match = re.match(thresholds_regex, stat['thresholds'].strip().lower())
        if match:
            low_threshold = int(match.group(1))
            high_threshold = int(match.group(2))
            low_threshold=low_threshold + (6 * tier_dif)
            high_threshold=high_threshold + (11 * tier_dif)
            stat['thresholds'] = f"{low_threshold}/{high_threshold}"
        atk=int(stat['atk'])
        atk=atk + (tier_dif)
        stat['atk']=f"{'+' if atk>0 else ''}{atk}"
        hp=int(stat['hp'])
        hp=hp + (2 * tier_dif)
        stat['hp']=f"{hp}"
        stress=int(stat['stress'])
        stress=stress + (2 * tier_dif)
        stat['stress']=f"{stress}"
        difficulty=int(stat['difficulty'])
        difficulty=difficulty + (3 * tier_dif)
        stat['difficulty']=f"{difficulty}"

        for feature in stat["features"]:
            feature["description"] = re.sub(
                r'(\d+d\d+[+-]\d+|\d+d\d+)', 
                lambda match: revalue_dice(match.group(0), old_tier, new_tier),
                feature["description"]
            )

    return stat


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


# --- External APIs ---

@app.route('/api/adversaries')
def api_adversaries():
    """Returns a list of all adversaries with basic information."""
    data = load_data()
    adversaries = [
        {
            'name': s.get('name', ''),
            'tier': s.get('tier', ''),
            'type': s.get('type', ''),
            'description': s.get('description', '')
        }
        for s in data if s.get('category') == 'Adversaries'
    ]
    return jsonify(adversaries)


@app.route('/api/environments')
def api_environments():
    """Returns a list of all environments with basic information."""
    data = load_data()
    environments = [
        {key: s.get(key, '') for key in ['name', 'tier', 'type', 'description']}
        for s in data if s.get('category') == 'Environments'
    ]
    return jsonify(environments)

@app.route('/api/stat/<path:name>')
def api_stat(name):
    data = load_data()
    found = find_stat(data, name)
    if not found:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(found)


@app.route('/api/retier', methods=['POST'])
def api_retier():
    """Finds a statblock and returns a modified version for a new tier."""
    payload = request.get_json() or {}
    name = (payload.get('name') or '').strip()
    new_tier = payload.get('new_tier')

    if not name or not new_tier:
        return jsonify({'error': 'Name and new_tier are required'}), 400

    data = load_data()
    stat = find_stat(data, name)
    if not stat:
        return jsonify({'error': 'Not found'}), 404

    modified_stat = retier(stat.copy(), new_tier)
    return jsonify(modified_stat or stat)


@app.route('/api/save', methods=['POST'])
def api_save():
    """Creates a new statblock or updates an existing one."""
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
            'motives_tactics': [m.strip() for m in (payload.get('motives_tactics') or '').split(',') if m.strip()],
            'difficulty': payload.get('difficulty'),
            'thresholds': payload.get('thresholds'),
            'hp': payload.get('hp'),
            'stress': payload.get('stress'),
            'atk': payload.get('atk'),
            'weapon': payload.get('weapon'),
            'range': payload.get('range'),
            'damage_dice': payload.get('damage_dice'),
            'damage_type': payload.get('damage_type'),
            'experience': [e.strip() for e in (payload.get('experience') or '').split(',') if e.strip()],
            'features': payload.get('features', [])
        }
    elif category == 'Environments':
        stat = {
            'name': name,
            'category': category,
            'tier': payload.get('tier'),
            'type': payload.get('type'),
            'description': payload.get('description'),
            'impulses': [i.strip() for i in (payload.get('impulses') or '').split(',') if i.strip()],
            'difficulty': payload.get('difficulty'),
            'potential_adversaries': payload.get('potential_adversaries'),
            'features': payload.get('features', [])
        }

    data.append(stat)
    save_data(data)
    return jsonify({'saved': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8282, debug=True)
