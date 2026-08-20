/**
 * DOE PELP Appliance Search - Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // -----------------------------------------------------------------------
    // DOM Elements & State
    // -----------------------------------------------------------------------
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const clearBtn = document.getElementById('clearBtn');
    const dropdown = document.getElementById('suggestionsDropdown');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsGrid = document.getElementById('resultsGrid');
    const resultsCount = document.getElementById('resultsCount');
    const categoryPills = document.querySelectorAll('.pill');
    const modalOverlay = document.getElementById('modalOverlay');
    const modalContent = document.getElementById('modalContent');
    const modalClose = document.getElementById('modalClose');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const themeToggle = document.getElementById('themeToggle');

    let API_BASE_URL = 'http://127.0.0.1:8000';
    let currentCategory = '';
    let debounceTimer = null;
    let selectedIndex = -1;
    let suggestionsData = [];

    // Category Slugs Mapping
    const CATEGORY_MAP = {
        'air-conditioners': 'Air Conditioners',
        'lighting-products': 'Lighting Products',
        'refrigerating-appliances': 'Refrigerating Appliances',
        'television-sets': 'Television Sets',
        'electric-fans': 'Electric Fans',
        'clothes-washing-machines': 'Clothes Washing Machines'
    };

    // -----------------------------------------------------------------------
    // API Connectivity Check (Port Auto-Detection)
    // -----------------------------------------------------------------------
    async function initApiConnection() {
        const ports = [8000, 8001, 8080];
        let connected = false;

        for (const port of ports) {
            const candidateUrl = `http://127.0.0.1:${port}`;
            try {
                const res = await fetch(`${candidateUrl}/`, { method: 'GET', signal: AbortSignal.timeout(1500) });
                if (res.ok) {
                    const data = await res.json();
                    API_BASE_URL = candidateUrl;
                    connected = true;
                    statusDot.classList.remove('disconnected');
                    statusText.textContent = `API Connected (${data.total_products.toLocaleString()} items)`;
                    break;
                }
            } catch (err) {
                // continue checking
            }
        }

        if (!connected) {
            statusDot.classList.add('disconnected');
            statusText.textContent = 'API Disconnected';
        }
    }

    initApiConnection();

    // -----------------------------------------------------------------------
    // Theme Switcher
    // -----------------------------------------------------------------------
    const savedTheme = localStorage.getItem('pelp_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    themeToggle.textContent = savedTheme === 'dark' ? '<svg class="w-4 h-4 inline-block text-amber-400 align-middle" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>' : '<svg class="w-4 h-4 inline-block text-indigo-400 align-middle" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>';

    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('pelp_theme', newTheme);
        themeToggle.textContent = newTheme === 'dark' ? '<svg class="w-4 h-4 inline-block text-amber-400 align-middle" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>' : '<svg class="w-4 h-4 inline-block text-indigo-400 align-middle" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>';
    });

    // -----------------------------------------------------------------------
    // Search Autocomplete Logic
    // -----------------------------------------------------------------------
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearBtn.style.display = query ? 'block' : 'none';

        if (!query) {
            hideDropdown();
            return;
        }

        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchSuggestions(query);
        }, 180);
    });

    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearBtn.style.display = 'none';
        hideDropdown();
        searchInput.focus();
    });

    async function fetchSuggestions(query) {
        try {
            const params = new URLSearchParams({ search_query: query, limit: 12 });
            if (currentCategory) params.append('category', currentCategory);

            const res = await fetch(`${API_BASE_URL}/appliances/search?${params.toString()}`);
            if (!res.ok) return;
            const data = await res.json();

            suggestionsData = data.results || [];
            renderDropdown(suggestionsData, query);
        } catch (err) {
            console.error('Failed to fetch suggestions:', err);
        }
    }

    function renderDropdown(items, query) {
        if (!items.length) {
            dropdown.innerHTML = '<div class="no-results" style="padding: 1rem; font-size: 0.9rem;">No matching appliances found</div>';
            dropdown.classList.add('active');
            return;
        }

        selectedIndex = -1;
        dropdown.innerHTML = items.map((item, index) => {
            const categoryName = CATEGORY_MAP[item.category] || item.category;
            const brand = item.brand || 'Generic';
            const model = item.model || 'N/A';

            return `
                <div class="suggestion-item" data-index="${index}">
                    <div class="suggestion-main">
                        <span class="category-tag">[${categoryName}]</span>
                        <span class="suggestion-title">
                            <span class="suggestion-brand">${escapeHtml(brand)}</span> - ${escapeHtml(model)}
                        </span>
                    </div>
                </div>
            `;
        }).join('');

        dropdown.classList.add('active');

        // Click handler for suggestion items
        dropdown.querySelectorAll('.suggestion-item').forEach(el => {
            el.addEventListener('click', () => {
                const idx = parseInt(el.dataset.index);
                selectSuggestion(items[idx]);
            });
        });
    }

    function hideDropdown() {
        dropdown.classList.remove('active');
        dropdown.innerHTML = '';
        selectedIndex = -1;
    }

    function selectSuggestion(product) {
        searchInput.value = `${product.brand} ${product.model}`.trim();
        hideDropdown();
        displaySearchResults([product], 1);
        openProductModal(product);
    }

    // -----------------------------------------------------------------------
    // Keyboard Navigation for Dropdown
    // -----------------------------------------------------------------------
    searchInput.addEventListener('keydown', (e) => {
        const items = dropdown.querySelectorAll('.suggestion-item');
        if (!items.length || !dropdown.classList.contains('active')) {
            if (e.key === 'Enter') {
                e.preventDefault();
                performFullSearch(searchInput.value.trim());
            }
            return;
        }

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
            updateSelectionHighlight(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, -1);
            updateSelectionHighlight(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (selectedIndex >= 0 && suggestionsData[selectedIndex]) {
                selectSuggestion(suggestionsData[selectedIndex]);
            } else {
                performFullSearch(searchInput.value.trim());
            }
        } else if (e.key === 'Escape') {
            hideDropdown();
        }
    });

    function updateSelectionHighlight(items) {
        items.forEach((item, index) => {
            if (index === selectedIndex) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('selected');
            }
        });
    }

    // -----------------------------------------------------------------------
    // Full Search Execution & Card Display
    // -----------------------------------------------------------------------
    searchBtn.addEventListener('click', () => {
        performFullSearch(searchInput.value.trim());
    });

    async function performFullSearch(query) {
        hideDropdown();
        resultsContainer.style.display = 'block';
        resultsGrid.innerHTML = '<div class="no-results"><div class="spinner"></div><p style="margin-top: 1rem;">Searching DOE records...</p></div>';

        try {
            const params = new URLSearchParams({ limit: 100 });
            if (query) params.append('search_query', query);
            if (currentCategory) params.append('category', currentCategory);

            const res = await fetch(`${API_BASE_URL}/appliances/search?${params.toString()}`);
            if (!res.ok) throw new Error('Search failed');

            const data = await res.json();
            displaySearchResults(data.results || [], data.total_results || 0);
        } catch (err) {
            resultsGrid.innerHTML = `<div class="no-results" style="color: var(--accent-rose);">Error connecting to API server at ${API_BASE_URL}</div>`;
        }
    }

    function displaySearchResults(products, totalCount) {
        resultsContainer.style.display = 'block';
        resultsCount.textContent = `Showing ${products.length} of ${totalCount.toLocaleString()} result${totalCount !== 1 ? 's' : ''}`;

        if (!products.length) {
            resultsGrid.innerHTML = '<div class="no-results">No appliances found matching your query.</div>';
            return;
        }

        resultsGrid.innerHTML = products.map((item, idx) => {
            const categoryName = CATEGORY_MAP[item.category] || item.category;
            const fields = item.raw_fields || {};
            
            // Extract prominent spec values depending on available fields
            const spec1 = fields['COOLING CAPACITY (KW)'] || fields['LUMINOUS FLUX (LM)'] || fields['STORAGE VOLUME (L)'] || fields['SCREEN SIZE (INCHES)'] || fields['BLADE SIZE (MM)'] || fields['WASHING CAPACITY (KG)'] || '';
            const spec1Label = fields['COOLING CAPACITY (KW)'] ? 'Cooling Cap.' : fields['LUMINOUS FLUX (LM)'] ? 'Luminous Flux' : fields['STORAGE VOLUME (L)'] ? 'Volume' : fields['SCREEN SIZE (INCHES)'] ? 'Screen Size' : fields['WASHING CAPACITY (KG)'] ? 'Capacity' : 'Capacity';
            
            const spec2 = fields['ENERGY EFFICIENCY RATING (CSPF)'] || fields['ENERGY EFFICIENCY PERFORMANCE RATING'] || fields['EER'] || fields['EER / CSPF'] || '';

            return `
                <div class="product-card" data-card-index="${idx}">
                    <div>
                        <div class="card-top">
                            <span class="card-brand">${escapeHtml(item.brand || 'DOE PELP')}</span>
                            <span class="category-tag">${escapeHtml(categoryName)}</span>
                        </div>
                        <div class="card-model">${escapeHtml(item.model || 'Model N/A')}</div>
                        <div class="card-specs">
                            ${spec1 ? `<div class="spec-row"><span class="spec-label">${spec1Label}</span><span class="spec-value">${escapeHtml(spec1)}</span></div>` : ''}
                            ${spec2 ? `<div class="spec-row"><span class="spec-label">EE Rating / CSPF</span><span class="spec-value">${escapeHtml(spec2)}</span></div>` : ''}
                            <div class="spec-row"><span class="spec-label">Control No.</span><span class="spec-value">${escapeHtml(fields['CONTROL NO.'] || 'N/A')}</span></div>
                        </div>
                    </div>
                    <button class="card-action" onclick="window.viewDetails(${idx})">View Full Technical Specs</button>
                </div>
            `;
        }).join('');

        // Store active products on window for quick access by viewDetails
        window.activeProducts = products;
    }

    window.viewDetails = function(idx) {
        if (window.activeProducts && window.activeProducts[idx]) {
            openProductModal(window.activeProducts[idx]);
        }
    };

    // -----------------------------------------------------------------------
    // Category Pills Filter
    // -----------------------------------------------------------------------
    categoryPills.forEach(pill => {
        pill.addEventListener('click', () => {
            categoryPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            currentCategory = pill.dataset.category || '';
            performFullSearch(searchInput.value.trim());
        });
    });

    // -----------------------------------------------------------------------
    // Product Detail Modal
    // -----------------------------------------------------------------------
    function openProductModal(product) {
        const categoryName = CATEGORY_MAP[product.category] || product.category;
        const fields = product.raw_fields || {};

        let tableRows = Object.entries(fields)
            .map(([key, val]) => `
                <tr>
                    <th>${escapeHtml(key)}</th>
                    <td>${escapeHtml(val || 'N/A')}</td>
                </tr>
            `).join('');

        modalContent.innerHTML = `
            <div class="modal-header">
                <span class="category-tag" style="margin-bottom: 0.5rem; display: inline-block;">${escapeHtml(categoryName)}</span>
                <h2 class="modal-title">${escapeHtml(product.brand)} - ${escapeHtml(product.model)}</h2>
            </div>
            <table class="modal-table">
                <tbody>
                    ${tableRows}
                </tbody>
            </table>
        `;

        modalOverlay.classList.add('active');
    }

    modalClose.addEventListener('click', () => {
        modalOverlay.classList.remove('active');
    });

    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            modalOverlay.classList.remove('active');
        }
    });

    // Close modal on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modalOverlay.classList.contains('active')) {
            modalOverlay.classList.remove('active');
        }
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-wrapper')) {
            hideDropdown();
        }
    });

    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/[&<>"']/g, m => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        })[m]);
    }
});
