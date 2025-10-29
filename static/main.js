document.addEventListener('DOMContentLoaded', function () {
  // Common: category -> types wiring
  const categoryEl = document.getElementById('category');
  const typeEl = document.getElementById('type');

  function loadTypesForCategory(cat, targetTypeEl) {
    targetTypeEl = targetTypeEl || typeEl;
    if (!cat) {
      targetTypeEl.innerHTML = '<option value="">Any</option>';
      return;
    }
    fetch(`/api/types?category=${encodeURIComponent(cat)}`)
      .then(r => r.json())
      .then(data => {
        const types = data.types || [];
        const defaultOpt = targetTypeEl === typeEl ? '<option value="">Any</option>' : '';
        targetTypeEl.innerHTML = defaultOpt + types.map(t => `<option>${t}</option>`).join('');
      });
  }

  if (categoryEl && typeEl) {
    categoryEl.addEventListener('change', () => loadTypesForCategory(categoryEl.value, typeEl));
  }

  // Lookup page wiring
  const searchBtn = document.getElementById('searchBtn');
  const resultsDiv = document.getElementById('results');
  const textEl = document.getElementById('text');
  const formattedEl = document.getElementById('formatted');
  const formattedJsonEl = document.getElementById('formattedJson');
  const lookupTypeEl = document.getElementById('type');

  if (searchBtn) {
    searchBtn.addEventListener('click', () => {
      const payload = {
        category: document.getElementById('category').value,
        tier: document.getElementById('tier').value,
        type: document.getElementById('type').value,
        text: textEl.value
      };

      fetch('/api/search', {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)})
        .then(r => r.json())
        .then(data => renderResults(data.results || []));
    });
  }

  function renderResults(items) {
    if (!resultsDiv) return;
    if (items.length === 0) {
      resultsDiv.innerHTML = '<p>No results.</p>';
      return;
    }
    resultsDiv.innerHTML = items.map(it => {
      return `
        <div class="card mb-2">
          <div class="card-body">
            <div class="row">
              <div class="col-md-8">
                <h5>${escapeHtml(it.name)}</h5>
                <div><strong>Tier:</strong> ${escapeHtml(it.tier)} &nbsp; <strong>Type:</strong> ${escapeHtml(it.type)}</div>
                <p>${escapeHtml(it.description || '')}</p>
              </div>
              <div class="col-md-4 text-end">
                <a class="btn btn-sm btn-outline-primary me-1" href="/update?name=${encodeURIComponent(it.name)}">Update</a>
                <button class="btn btn-sm btn-primary view-btn" data-name="${escapeHtml(it.name)}">View</button>
              </div>
            </div>
          </div>
        </div>`;
    }).join('');

    // wire view buttons
    resultsDiv.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const name = btn.dataset.name;
        fetch(`/api/stat/${encodeURIComponent(name)}`)
          .then(r => r.json())
          .then(data => {
            if (formattedEl) formattedEl.value = formatStatblock(data);
            const outputJson = transformToOutputJson(data);
            if (formattedJsonEl) formattedJsonEl.value = JSON.stringify(outputJson, null, 2);
          });
      });
    });
  }

  function formatStatblock(s) {
    if (!s) return '';
    let out = `**${s.name}**\n*Tier ${s.tier} ${s.type} ${s.category}*\n`;

    if (s.description) {
      out += `${s.description}\n`;
    }

    if (s.category === 'Adversaries') {
      if (s.motives_tactics) out += `**Motives & Tactics:** ${s.motives_tactics}\n`;
      out += `**Difficulty:** ${s.difficulty || ''}\n`;
      out += `**Thresholds:** ${s.thresholds || ''} | **HP:** ${s.hp || ''} | **Stress:** ${s.stress || ''}\n`;
      // Weapon line
      out += `**${s.weapon || 'Weapon'}** (${s.atk || ''}, ${s.range || 'Range'}) - ${s.damage_dice || ''} ${s.damage_type || ''} damage\n`;
      out += `**Experience:** ${s.experience || ''}\n`;
    } else if (s.category === 'Environments') {
      if (s.impulses) out += `**Impulses:** ${s.impulses}\n`;
      out += `**Difficulty:** ${s.difficulty || ''}\n`;
      if (s.potential_adversaries) out += `**Potential Adversaries:** ${s.potential_adversaries}\n`;
    }

    out += `**Features**\n`;
    (s.features || []).forEach(f => {
      out += `* **${f.name} (${f.type}):** ${f.description}\n`;
    });
    return out;
  }

  function transformToOutputJson(s) {
    if (!s) return {};

    if (s.category === 'Environments') {
      const output = {
        name: s.name || '',
        tier: parseInt(s.tier, 10) || 1,
        description: s.description || '',
        impulses: [],
        difficulty: s.difficulty || '',
        adversaries: [],
        features: []
      };

      // Split comma-separated strings into arrays
      if (s.impulses) {
        if (Array.isArray(s.impulses)) {
          output.impulses = s.impulses;
        } else if (typeof s.impulses === 'string') {
          output.impulses = s.impulses.split(',').map(item => item.trim());
        }
      }
      if (s.potential_adversaries) {
        if (Array.isArray(s.potential_adversaries)) {
          output.adversaries = s.potential_adversaries;
        } else if (typeof s.potential_adversaries === 'string') {
          output.adversaries = s.potential_adversaries.split(',').map(item => item.trim());
        }
      }
      output.features = (s.features || []).map(f => ({ name: f.name, effect: f.description }));
      return output;
    } else if (s.category !== 'Adversaries') {
      return s;
    }

    // Transform Adversary to the desired output format
    const output = {
      name: s.name || '',
      hp: s.hp || '',
      stress: s.stress || '',
      thresholds: s.thresholds || '',
      difficulty: s.difficulty || '',
      experiences: [],
      attacks: [],
      features: []
    };

    // Experience
    if (s.experience) {
      s.experience.forEach(item => {
        const trimmedItem = item.trim();
        if (trimmedItem) {
          const lastSpaceIndex = trimmedItem.lastIndexOf(' ');
          if (lastSpaceIndex > -1) {
            const name = trimmedItem.substring(0, lastSpaceIndex).trim();
            const value = trimmedItem.substring(lastSpaceIndex + 1).trim();
            output.experiences.push({ name: name, value: value });
          } else {
            // Handle cases with no value, e.g., "Climbing"
            output.experiences.push({ name: trimmedItem, value: "" });
          }
        }
      });
    }

    // Attacks
    if (s.weapon) {
      output.attacks.push({
        name: s.weapon,
        attack_bonus: parseInt(String(s.atk).replace('+', ''), 10) || 0,
        damage: s.damage_dice || '',
        damage_type: s.damage_type || '',
        range: s.range || ''
      });
    }

    // Features
    output.features = (s.features || []).map(f => ({ name: f.name, effect: f.description }));

    return output;
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/[&<>"']/g, function (c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[c];
    });
  }

  // Update page wiring
  if (window.location.pathname === '/update') {
    const addFeatureBtn = document.getElementById('addFeature');
    const featuresDiv = document.getElementById('features');
    const featureTpl = document.getElementById('featureTpl');
    const saveBtn = document.getElementById('saveBtn');
    const nameField = document.getElementById('name');
    const truecaseBtn = document.getElementById('truecase-name-btn');
    const tierField = document.getElementById('tier');
    const updateCategoryEl = document.getElementById('category');
    const updateTypeEl = document.getElementById('type');

    // Function to replace newlines with spaces
    function handleFormatNewline(event) {
      const button = event.currentTarget;
      const textarea = button.parentElement.querySelector('textarea');
      if (textarea) {
        textarea.value = textarea.value.replace(/(\r\n|\n|\r)/gm, " ").trim().replace(/fi /g, "fi").replace(/fl /g, "fl");
      }
    }

    // Function to convert string to Title Case
    function toTitleCase(str) {
      if (!str) return '';
      return str.replace(/\w\S*/g, (txt) => {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
      });
    }

    // Show/hide fields based on category
    function toggleCategoryFields() {
      const category = updateCategoryEl.value;
      document.getElementById('adversaryFields').style.display = category === 'Adversaries' ? '' : 'none';
      document.getElementById('environmentFields').style.display = category === 'Environments' ? '' : 'none';
    }

    updateCategoryEl.addEventListener('change', () => {
      loadTypesForCategory(updateCategoryEl.value, updateTypeEl);
      toggleCategoryFields();
    });


    function addFeatureRow(feature) {
      const node = featureTpl.content.cloneNode(true);
      const el = node.querySelector('.feature-item');
      if (feature) {
        el.querySelector('.feature-name').value = feature.name || '';
        el.querySelector('.feature-type').value = feature.type || 'Passive';
        el.querySelector('.feature-desc').value = feature.description || '';
      }
      el.querySelector('.remove-feature').addEventListener('click', (ev) => { ev.preventDefault(); el.remove(); });
      el.querySelector('.format-newline-btn').addEventListener('click', handleFormatNewline);
      featuresDiv.appendChild(el);
    }

    addFeatureBtn.addEventListener('click', (ev) => { ev.preventDefault(); addFeatureRow(); });

    document.querySelectorAll('.format-newline-btn').forEach(btn => btn.addEventListener('click', handleFormatNewline));

    if (truecaseBtn && nameField) {
      truecaseBtn.addEventListener('click', () => { nameField.value = toTitleCase(nameField.value); });
    }

    // load when name query param present
    const params = new URLSearchParams(window.location.search);
    const nameParam = params.get('name');
    if (nameParam) {
      fetch(`/api/stat/${encodeURIComponent(nameParam)}`)
        .then(r => r.json())
        .then(data => {
          if (data && data.name) {
            document.getElementById('formTitle').textContent = 'Edit: ' + data.name;
            nameField.value = data.name;
            updateCategoryEl.value = data.category || updateCategoryEl.value;
            loadTypesForCategory(updateCategoryEl.value, updateTypeEl);
            setTimeout(() => { updateTypeEl.value = data.type || ''; }, 100);
            tierField.value = data.tier || '';
            document.getElementById('description').value = data.description || '';

            if (data.category === 'Adversaries') {
              document.getElementById('motives_tactics').value = data.motives_tactics || '';
              document.getElementById('difficulty').value = data.difficulty || '';
              document.getElementById('thresholds').value = data.thresholds || '';
              document.getElementById('hp').value = data.hp || '';
              document.getElementById('stress').value = data.stress || '';
              document.getElementById('atk').value = data.atk || '';
              document.getElementById('weapon').value = data.weapon || '';
              document.getElementById('weapon_range').value = data.range || '';
              document.getElementById('weapon_damage_dice').value = data.damage_dice || '';
              document.getElementById('weapon_damage_type').value = data.damage_type || '';
              document.getElementById('experience').value = data.experience || '';
            } else if (data.category === 'Environments') {
              document.getElementById('impulses').value = data.impulses || '';
              document.getElementById('env_difficulty').value = data.difficulty || '';
              document.getElementById('potential_adversaries').value = data.potential_adversaries || '';
            }

            (data.features || []).forEach(f => addFeatureRow(f));
            toggleCategoryFields();
          }
        });
    } else {
      // initialize types for selected category
      const categoryParam = params.get('category');
      if (categoryParam) {
        updateCategoryEl.value = categoryParam;
      }
      loadTypesForCategory(updateCategoryEl.value, updateTypeEl);
      toggleCategoryFields();
    }

    // Initial call on page load
    loadTypesForCategory(updateCategoryEl.value, updateTypeEl);
    toggleCategoryFields();

    saveBtn.addEventListener('click', () => {
      const features = [];
      featuresDiv.querySelectorAll('.feature-item').forEach(fi => {
        const name = fi.querySelector('.feature-name').value;
        const type = fi.querySelector('.feature-type').value;
        const desc = fi.querySelector('.feature-desc').value;
        if (name) features.push({name, type, description: desc});
      });

      const category = updateCategoryEl.value;
      let payload = {
        name: nameField.value,
        category: category,
        tier: tierField.value,
        type: updateTypeEl.value,
        description: document.getElementById('description').value,
        features
      };

      if (category === 'Adversaries') {
        payload.motives_tactics = document.getElementById('motives_tactics').value;
        payload.difficulty = document.getElementById('difficulty').value;
        payload.thresholds = document.getElementById('thresholds').value;
        payload.hp = document.getElementById('hp').value;
        payload.stress = document.getElementById('stress').value;
        payload.atk = document.getElementById('atk').value;
        payload.weapon = document.getElementById('weapon').value;
        payload.range = document.getElementById('weapon_range').value;
        payload.damage_dice = document.getElementById('weapon_damage_dice').value;
        payload.damage_type = document.getElementById('weapon_damage_type').value;
        payload.experience = document.getElementById('experience').value;
      } else if (category === 'Environments') {
        payload.impulses = document.getElementById('impulses').value;
        payload.difficulty = document.getElementById('env_difficulty').value;
        payload.potential_adversaries = document.getElementById('potential_adversaries').value;
      }


      fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
        .then(r => r.json())
        .then(res => { if (res.saved) window.location.href = '/'; else alert('Save failed'); })
        .catch(err => alert('Save failed'));
    });
  }

});
