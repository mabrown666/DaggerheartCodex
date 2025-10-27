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
            formattedEl.value = formatStatblock(data);
          });
      });
    });
  }

  function formatStatblock(s) {
    if (!s) return '';
    let out = `${s.name}\nTier ${s.tier} - ${s.category} / ${s.type}\n\n${s.description}\n\nStats:\n${s.stats}\n\nFeatures:\n`;
    (s.features || []).forEach(f => {
      out += `- ${f.name} (${f.type})\n${f.description}\n\n`;
    });
    return out;
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
    const tierField = document.getElementById('tier');
    const descField = document.getElementById('description');
    const statsField = document.getElementById('stats');
    const updateCategoryEl = document.getElementById('category');
    const updateTypeEl = document.getElementById('type');

    function addFeatureRow(feature) {
      const node = featureTpl.content.cloneNode(true);
      const el = node.querySelector('.feature-item');
      if (feature) {
        el.querySelector('.feature-name').value = feature.name || '';
        el.querySelector('.feature-type').value = feature.type || 'Passive';
        el.querySelector('.feature-desc').value = feature.description || '';
      }
      el.querySelector('.remove-feature').addEventListener('click', (ev) => { ev.preventDefault(); el.remove(); });
      featuresDiv.appendChild(el);
    }

    addFeatureBtn.addEventListener('click', (ev) => { ev.preventDefault(); addFeatureRow(); });

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
            tierField.value = data.tier || tierField.value;
            descField.value = data.description || '';
            statsField.value = data.stats || '';
            (data.features || []).forEach(f => addFeatureRow(f));
          }
        });
    } else {
      // initialize types for selected category
      loadTypesForCategory(updateCategoryEl.value, updateTypeEl);
    }

    // when category change, update type list
    updateCategoryEl.addEventListener('change', () => loadTypesForCategory(updateCategoryEl.value, updateTypeEl));

    saveBtn.addEventListener('click', () => {
      const features = [];
      featuresDiv.querySelectorAll('.feature-item').forEach(fi => {
        const name = fi.querySelector('.feature-name').value;
        const type = fi.querySelector('.feature-type').value;
        const desc = fi.querySelector('.feature-desc').value;
        if (name) features.push({name, type, description: desc});
      });

      const payload = {
        name: nameField.value,
        category: updateCategoryEl.value,
        tier: tierField.value,
        type: updateTypeEl.value,
        description: descField.value,
        stats: statsField.value,
        features
      };

      fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
        .then(r => r.json())
        .then(res => { if (res.saved) window.location.href = '/'; else alert('Save failed'); })
        .catch(err => alert('Save failed'));
    });
  }

});
