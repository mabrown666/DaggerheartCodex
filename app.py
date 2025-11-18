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

def parse_text_statblock(text):
    """Parses a custom text block format into a statblock dictionary."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return {}

    stat = {
        "features": []
    }

    # First line is usually the name
    stat['name'] = lines.pop(0)
    if not stat['name']: # Name is mandatory
        return {}

    # Second line for Tier, Type, Category
    # Initialize these to empty strings in case they are not found
    stat['tier'] = '1'
    stat['category'] = 'Adversaries'
    stat['type'] = 'Solo'

    # look for Tier, Type, Category information in the line after the name
    if lines[0].startswith('Tier '):
        tier_line = lines.pop(0)
        tier_match = re.search(r'Tier (\d+)', tier_line, re.IGNORECASE)
        if tier_match:
            stat['tier'] = int(tier_match.group(1))
            for cat, types in CATEGORIES.items():
                for t in types:
                    if re.search(r'\b' + re.escape(t) + r'\b', tier_line, re.IGNORECASE):
                        stat['category'] = cat
                        stat['type'] = t
                        break

    # Description: The first non-empty line after name/tier that doesn't look like a key-value pair or "Features"
    description_lines = []
    # Look for description before processing other key-value pairs
    while lines and not re.match(r'^\w+.*?:', lines[0]) and not lines[0].lower().startswith('motives') and not lines[0].lower().startswith('impulses'):
        description_lines.append(lines.pop(0))
    if description_lines:
        stat['description'] = " ".join(description_lines).strip()
    else:
        stat['description'] = ''

    if stat['category']=='Adversaries':
        # load motives_tactics from the next no-blank line
        if lines and lines[0].strip():
            motive_line = lines.pop(0).split(':', 1)[1]
            stat['motives_tactics'] = motive_line.strip().split(',')


        feature_section = False # Flag to indicate if we are in the features section
        current_feature = None # To build multi-line feature descriptions

        for line in lines: # Iterate through the remaining lines
            line_lower = line.lower()

            if line_lower == 'features':
                feature_section = True
                if current_feature:
                    stat['features'].append(current_feature)
                    current_feature = None
                continue

            if feature_section:
                # Regex to capture feature name, type, and description
                # Handles both (Type): and – Type:
                feature_match = re.match(r'^(.*?)\s*(?:\((Action|Reaction|Passive|Evolution|Transformation)\)|–\s*(Action|Reaction|Passive|Evolution|Transformation))\s*:\s*(.*)$', line, re.IGNORECASE)
                if feature_match:
                    if current_feature:
                        stat['features'].append(current_feature)
                    
                    feature_type = (feature_match.group(2) or feature_match.group(3) or '').strip().capitalize()
                    current_feature = { # Store as dict
                        "name": feature_match.group(1).strip(),
                        "type": feature_type,
                        "description": feature_match.group(4).strip()
                    }
                elif current_feature:
                    # Append to the description of the current feature
                    current_feature["description"] += f"\n" + line.strip()
            else:
                # Handle key-value pairs
                Difficulty_line_match = re.match(r"Difficulty: ?(\d+)\s*\|.*?(\d+\s*/\s*\d+)\s*\|.*?(\d+)\s*\|.*?(\d+)", line, re.IGNORECASE)
                if Difficulty_line_match:
                    stat['difficulty'] = Difficulty_line_match.group(1).strip()
                    stat['thresholds'] = Difficulty_line_match.group(2).strip()
                    stat['hp'] = Difficulty_line_match.group(3).strip()
                    stat['stress'] =Difficulty_line_match.group(4).strip()
                    continue # Move to next line after parsing Difficulty

                # Specific parsing for ATK line due to its complex structure
                atk_line_match = re.match(r'ATK:\s*([+-]?\d+)\s*\|\s*(.*?)\s*\|\s*(\S+)\s*(\S+)', line, re.IGNORECASE)
                if atk_line_match:
                    stat['atk'] = atk_line_match.group(1).strip()
                    weapon_and_range_str = atk_line_match.group(2).strip()
                    
                    # Parse weapon and range from the middle part
                    if ':' in weapon_and_range_str:
                        weapon_parts = weapon_and_range_str.split(':', 1)
                        stat['weapon'] = weapon_parts[0].strip()
                        stat['range'] = weapon_parts[1].strip()
                    else:
                        # Assume last word is range, rest is weapon
                        parts = weapon_and_range_str.rsplit(' ', 1)
                        if len(parts) == 2:
                            stat['weapon'] = parts[0].strip()
                            stat['range'] = parts[1].strip()
                        else: # Only one word, assume it's weapon
                            stat['weapon'] = weapon_and_range_str
                            stat['range'] = '' # Default to empty string if no range found

                    stat['damage_dice'] = atk_line_match.group(3).strip()
                    stat['damage_type'] = atk_line_match.group(4).strip()
                    continue # Move to next line after parsing ATK

                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower().replace(' ', '_')
                    value = parts[1].strip()
                    
                    # Mapping for keys that don't directly match the statblock format
                    key_map = {
                        'motives_&_tactics': 'motives_tactics',
                        'difficulty': 'difficulty',
                        'thresholds': 'thresholds',
                        'hp': 'hp',
                        'stress': 'stress',
                        'experience': 'experience',
                        'impulses': 'impulses',
                        'potential_adversaries': 'potential_adversaries',
                    }
                    key = key_map.get(key, key)

                    if key in ['motives_tactics', 'impulses', 'experience']:
                        stat[key] = [item.strip() for item in value.split(',')]
                    elif key in ['difficulty', 'thresholds', 'hp', 'stress']:
                        stat[key] = value # Keep as string
                    else:
                        stat[key] = value

        if current_feature:
            stat['features'].append(current_feature)

        # Post-processing for damage_type if it's "Physical"
        if stat.get('damage_type', '').lower() == 'physical':
            stat['damage_type'] = 'phy'

        # Ensure all expected fields are present, even if empty, for consistent output structure
        default_fields = {
            "atk": "", "category": "", "damage_dice": "", "damage_type": "",
            "description": "", "difficulty": "", "experience": [], "features": [],
            "hp": "", "motives_tactics": [], "name": "", "range": "",
            "stress": "", "thresholds": "", "tier": "", "type": "",
            "weapon": "", "impulses": [], "potential_adversaries": ""
        }
    elif stat['category']=='Environments':
        feature_section = False # Flag to indicate if we are in the features section
        current_feature = None # To build multi-line feature descriptions

        for line in lines: # Iterate through the remaining lines
            line_lower = line.lower()

            if line_lower == 'features':
                feature_section = True
                if current_feature:
                    stat['features'].append(current_feature)
                    current_feature = None
                continue

            if line_lower.startswith('impulses:'):
                motive_line = line.split(':', 1)[1]
                stat['impulses'] = motive_line.strip().split(',')
            elif line_lower.startswith('difficulty:'):
                stat['difficulty'] = line.split(':', 1)[1]
            elif line_lower.startswith('potential adversaries:'):
                stat['potential_adversaries'] = line.split(':', 1)[1]
            elif feature_section:
                # Regex to capture feature name, type, and description
                # Handles both (Type): and – Type:
                feature_match = re.match(r'^(.*?)\s*(?:\((Action|Reaction|Passive|Evolution|Transformation)\)|–\s*(Action|Reaction|Passive|Evolution|Transformation))\s*:\s*(.*)$', line, re.IGNORECASE)
                ick_match = re.match(r'^(.*?)\s*:\s*(.*)$', line, re.IGNORECASE)    
                if feature_match:
                    if current_feature:
                        stat['features'].append(current_feature)
                    
                    feature_type = (feature_match.group(2) or feature_match.group(3) or '').strip().capitalize()
                    current_feature = { # Store as dict
                        "name": feature_match.group(1).strip(),
                        "type": feature_type,
                        "description": feature_match.group(4).strip()
                    }
                elif ick_match:
                    if current_feature:
                        stat['features'].append(current_feature)
                    
                    current_feature = { # Store as dict
                        "name": ick_match.group(1).strip(),
                        "type": 'Action',
                        "description": ick_match.group(2).strip()
                    }

                elif current_feature:
                    # Append to the description of the current feature
                    current_feature["description"] += f"\n" + line.strip()
        default_fields = {
            "category": "Environments",
            "description": "No description available",
            "difficulty": 1,
            "features": [],
            "name": "Unknown",
            "potential_adversaries": "Beasts (Bear, Dire Wolf, Glass Snake), Grove Guardians (Minor Treant, Sylvan Soldier, Young Dryad)",
            "tier": "1",
            "type": "Exploration"
            }
    for key, default_value in default_fields.items():
        if key not in stat:
            stat[key] = default_value

    return stat

def load_statblock(text):
    try:
        statblock = json.loads(text)
        # Transform "attacks" array if it exists
        if 'attacks' in statblock and isinstance(statblock['attacks'], list) and statblock['attacks']:
            attack = statblock['attacks'][0]
            
            statblock['weapon'] = attack.get('name')
            
            attack_bonus = attack.get('attack_bonus', 0)
            if isinstance(attack_bonus, (int, float)):
                 statblock['atk'] = f"{'+' if attack_bonus > 0 else ''}{attack_bonus}"
            else:
                 statblock['atk'] = str(attack_bonus)

            statblock['damage_dice'] = attack.get('damage')
            statblock['damage_type'] = attack.get('damage_type')
            statblock['range'] = attack.get('range')
            del statblock['attacks']

        # Transform "effect" to "description" in features
        if 'features' in statblock and isinstance(statblock['features'], list):
            for feature in statblock['features']:
                if 'effect' in feature:
                    feature['description'] = feature.pop('effect')

        # Transform "experiences" array to "experience"
        if 'experiences' in statblock and isinstance(statblock['experiences'], list):
            new_experience = []
            for exp in statblock['experiences']:
                name = exp.get('name', '')
                value = exp.get('value', '')
                new_experience.append(f"{name} {value}".strip())
            statblock['experience'] = new_experience
            del statblock['experiences']

        return statblock
    except json.JSONDecodeError:
        return parse_text_statblock(text)

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

@app.route('/api/load_statblock', methods=['POST'])
def api_load_statblock():
    """
    Parses raw text from the request and returns a structured statblock object.
    """
    payload = request.get_json() or {}
    text = payload.get('text', '')
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    statblock = load_statblock(text)
    return jsonify(statblock)

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
