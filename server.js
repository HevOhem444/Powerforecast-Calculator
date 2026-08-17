const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = process.env.PORT || 8000;
const PROJECT_DIR = __dirname;

// Simple .env parser to load environment variables if present
const envPath = path.join(PROJECT_DIR, '.env');
if (fs.existsSync(envPath)) {
    try {
        const envContent = fs.readFileSync(envPath, 'utf-8');
        envContent.split(/\r?\n/).forEach(line => {
            const parts = line.split('=');
            if (parts.length >= 2 && parts[0].trim()) {
                const key = parts[0].trim();
                const val = parts.slice(1).join('=').trim();
                if (!process.env[key]) process.env[key] = val;
            }
        });
    } catch (e) {
        console.warn('Could not parse .env file:', e);
    }
}

const DEFAULT_RATES = {
    transmission: 1.4074,
    systemLoss: 0.7994,
    distTier1: 0.9803,
    distTier2: 1.2908,
    distTier3: 1.5837,
    distTier4: 2.0941,
    meteringFixed: 5.0,
    meteringPerKwh: 0.3350,
    supplyFixed: 16.3800,
    supplyPerKwh: 0.4979,
    awatRefund: -0.4278,
    regReset: -0.0023,
    vatGen: 0.0941,
    vatTrans: 0.1126,
    vatSysLoss: 0.0966,
    vatOthers: 0.1200,
    rptRate: 0.0062,
    lftRate: 0.0050,
    universalRate: 0.3216,
    fitAll: 0.2011,
    lifelineRate: 0.0100,
    seniorRate: 0.0001
};

function performCalculation(kwh, genRate, otherCharges) {
    const genCost = Math.round(kwh * genRate * 100) / 100;
    const transCost = Math.round(kwh * DEFAULT_RATES.transmission * 100) / 100;
    const sysLossCost = Math.round(kwh * DEFAULT_RATES.systemLoss * 100) / 100;

    let distRate;
    if (kwh <= 200) distRate = DEFAULT_RATES.distTier1;
    else if (kwh <= 300) distRate = DEFAULT_RATES.distTier2;
    else if (kwh <= 400) distRate = DEFAULT_RATES.distTier3;
    else distRate = DEFAULT_RATES.distTier4;

    const distCost = Math.round(kwh * distRate * 100) / 100;
    const meteringCost = kwh === 0 ? 0 : Math.round(kwh * DEFAULT_RATES.meteringPerKwh * 100) / 100 + DEFAULT_RATES.meteringFixed;
    const supplyCost = kwh === 0 ? 0 : Math.round(kwh * DEFAULT_RATES.supplyPerKwh * 100) / 100 + DEFAULT_RATES.supplyFixed;
    const awatRefund = Math.round(kwh * DEFAULT_RATES.awatRefund * 100) / 100;
    const regReset = Math.round(kwh * DEFAULT_RATES.regReset * 100) / 100;
    const seniorCost = Math.round(kwh * DEFAULT_RATES.seniorRate * 100) / 100;

    const genVat = Math.round(genCost * DEFAULT_RATES.vatGen * 100) / 100;
    const transVat = Math.round(transCost * DEFAULT_RATES.vatTrans * 100) / 100;
    const sysLossVat = Math.round(sysLossCost * DEFAULT_RATES.vatSysLoss * 100) / 100;

    const distTotal = distCost + meteringCost + supplyCost + awatRefund + regReset;
    const distVat = Math.round(distTotal * DEFAULT_RATES.vatOthers * 100) / 100;
    const seniorVat = Math.round(seniorCost * DEFAULT_RATES.vatOthers * 100) / 100;
    const totalVat = genVat + transVat + sysLossVat + distVat + seniorVat;

    const rptCost = Math.round(kwh * DEFAULT_RATES.rptRate * 100) / 100;
    const lftBase = genCost + transCost + sysLossCost + distTotal + seniorCost + rptCost;
    const lftCost = Math.round(lftBase * DEFAULT_RATES.lftRate * 100) / 100;
    const govTaxesTotal = rptCost + lftCost + totalVat;

    const universalChargesTotal = Math.round(kwh * DEFAULT_RATES.universalRate * 100) / 100;
    const fitAllCost = Math.round(kwh * DEFAULT_RATES.fitAll * 100) / 100;
    const lifelineCost = Math.round(kwh * DEFAULT_RATES.lifelineRate * 100) / 100;
    const nonVatSubsidiesTotal = universalChargesTotal + fitAllCost + lifelineCost;

    const energyAmount = genCost + transCost + sysLossCost + distTotal + seniorCost + govTaxesTotal + nonVatSubsidiesTotal;
    const totalBill = energyAmount + otherCharges;

    return {
        success: true,
        input: { kwh, generation_rate: genRate, other_charges: otherCharges },
        summary: {
            total_bill: Math.round(totalBill * 100) / 100,
            energy_cost: Math.round(energyAmount * 100) / 100,
            other_charges: Math.round(otherCharges * 100) / 100
        },
        itemized: {
            generation_charge: genCost,
            transmission_charge: transCost,
            system_loss_charge: sysLossCost,
            distribution_charge: distCost,
            metering_supply_charge: Math.round((meteringCost + supplyCost) * 100) / 100,
            subsidies_and_refunds: Math.round((awatRefund + regReset + seniorCost) * 100) / 100,
            government_taxes_and_vat: Math.round(govTaxesTotal * 100) / 100,
            universal_charges_and_fitall: Math.round(nonVatSubsidiesTotal * 100) / 100
        }
    };
}

const MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
};

function sendCorsHeaders(res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With');
}

const PELP_CATEGORIES = {
    'Air Conditioners': 'air-conditioners',
    'Lighting Products': 'lighting-products',
    'Refrigerating Appliances': 'refrigerating-appliances',
    'Television Sets': 'television-sets',
    'Electric Fans': 'electric-fans',
    'Clothes Washing Machines': 'clothes-washing-machines'
};

const PELP_SLUG_TO_NAME = {};
for (const [k, v] of Object.entries(PELP_CATEGORIES)) {
    PELP_SLUG_TO_NAME[v] = k;
}

let pelpDataCache = null;

function getPelpJsonDir() {
    const candidates = [
        path.join(PROJECT_DIR, 'pelp_data', 'parsed_json'),
        path.join(PROJECT_DIR, 'data', 'parsed_json'),
        path.join(PROJECT_DIR, 'Appliances_PELP', 'data', 'parsed_json'),
        path.join(PROJECT_DIR, '..', 'Appliances_PELP', 'data', 'parsed_json')
    ];
    for (const c of candidates) {
        if (fs.existsSync(c)) return c;
    }
    return candidates[0];
}

function loadPelpData() {
    if (pelpDataCache) return pelpDataCache;
    const jsonDir = getPelpJsonDir();
    pelpDataCache = {};
    for (const slug of Object.values(PELP_CATEGORIES)) {
        const filePath = path.join(jsonDir, `${slug}.json`);
        if (fs.existsSync(filePath)) {
            try {
                const content = fs.readFileSync(filePath, 'utf-8');
                const parsed = JSON.parse(content);
                pelpDataCache[slug] = parsed.products || [];
            } catch (e) {
                pelpDataCache[slug] = [];
            }
        } else {
            pelpDataCache[slug] = [];
        }
    }
    return pelpDataCache;
}

function extractNormalizedProduct(row, categorySlug) {
    let brand = '', model = '', powerWatts = 0, monthlyKwh = 0;
    let energyRatingType = '', energyRatingValue = '', starRating = '', controlNo = '', productName = '', doeLink = '';

    for (const [k, v] of Object.entries(row)) {
        const kl = k.toLowerCase();
        const valStr = String(v || '').trim();

        if ((kl.includes('brand') || kl.includes('manufacturer')) && !brand && valStr) brand = valStr;
        else if ((kl.includes('model') || kl.includes('designation')) && !model && valStr) model = valStr;
        else if (kl.includes('product name') && !productName && valStr) productName = valStr;
        else if (kl.includes('control no') && !controlNo && valStr) controlNo = valStr;
        else if (kl.includes('public product link') && !doeLink && valStr) doeLink = valStr;

        if ((kl.includes('power rating') || kl.includes('rated power') || kl.includes('power (watts)')) && valStr) {
            const clean = valStr.replace(/[^0-9.]/g, '');
            if (clean && !isNaN(parseFloat(clean))) powerWatts = parseFloat(clean);
        }

        if ((kl.includes('monthly') && kl.includes('kwh')) || (kl.includes('monthly') && kl.includes('consumption'))) {
            const clean = valStr.replace(/[^0-9.]/g, '');
            if (clean && !isNaN(parseFloat(clean))) monthlyKwh = parseFloat(clean);
        }

        if (kl.includes('energy efficiency rating') || kl.includes('energy efficiency factor') || kl.includes('cspf') || kl.includes('eef') || kl.includes('eer')) {
            if (!energyRatingValue && valStr) {
                energyRatingValue = valStr;
                if (kl.includes('cspf')) energyRatingType = 'CSPF';
                else if (kl.includes('eef')) energyRatingType = 'EEF';
                else energyRatingType = 'EER';
            }
        }

        if ((kl.includes('performance rating') || kl.includes('star')) && !starRating && valStr) {
            starRating = valStr;
        }
    }

    if (powerWatts <= 0 && monthlyKwh > 0) {
        powerWatts = Math.round((monthlyKwh / 30 / 8) * 1000 * 10) / 10;
    }

    const rawFields = {};
    for (const [k, v] of Object.entries(row)) {
        if (!k.startsWith('_')) rawFields[k] = v;
    }

    return {
        category: categorySlug,
        category_name: PELP_SLUG_TO_NAME[categorySlug] || categorySlug,
        brand: brand || row.COMPANY || 'Unknown Brand',
        model: model || row['MODEL NO./CODE'] || '',
        product_name: productName || row['PRODUCT NAME'] || '',
        control_no: controlNo,
        power_watts: powerWatts,
        monthly_kwh: monthlyKwh,
        energy_rating_type: energyRatingType,
        energy_rating_value: energyRatingValue,
        star_rating: starRating,
        doe_link: doeLink,
        raw_fields: rawFields
    };
}

function handlePelpApi(req, res, parsedUrl) {
    const pathname = parsedUrl.pathname.replace(/\/$/, '');
    const query = parsedUrl.query || {};
    const data = loadPelpData();

    if (pathname === '/api/pelp' || pathname === '/api/pelp/health') {
        const summaries = [];
        let total = 0;
        for (const slug of Object.values(PELP_CATEGORIES)) {
            const count = (data[slug] || []).length;
            total += count;
            summaries.push({
                category: slug,
                display_name: PELP_SLUG_TO_NAME[slug] || slug,
                count
            });
        }
        res.end(JSON.stringify({
            status: 'ok',
            service: 'DOE PELP Appliance Data API',
            categories_available: summaries,
            total_products: total
        }));
        return;
    }

    if (pathname === '/api/pelp/categories') {
        const categories = Object.values(PELP_CATEGORIES).map(slug => ({
            category: slug,
            display_name: PELP_SLUG_TO_NAME[slug] || slug,
            count: (data[slug] || []).length
        }));
        res.end(JSON.stringify({ categories }));
        return;
    }

    if (pathname === '/api/pelp/search' || pathname === '/api/pelp/appliances/search') {
        const qStr = (query.q || query.search_query || '').trim().toLowerCase();
        const brand = (query.brand || '').trim().toLowerCase();
        const model = (query.model || '').trim().toLowerCase();
        const category = (query.category || '').trim();
        const limit = parseInt(query.limit || 50, 10);

        const tokens = qStr ? qStr.split(/\s+/) : [];
        const slugs = category && PELP_SLUG_TO_NAME[category] ? [category] : Object.values(PELP_CATEGORIES);
        const results = [];

        for (const slug of slugs) {
            const rows = data[slug] || [];
            const dispName = (PELP_SLUG_TO_NAME[slug] || slug).toLowerCase();

            for (const row of rows) {
                const prod = extractNormalizedProduct(row, slug);

                if (brand && !prod.brand.toLowerCase().includes(brand)) continue;
                if (model && !prod.model.toLowerCase().includes(model)) continue;

                if (tokens.length > 0) {
                    const fullText = [
                        prod.brand.toLowerCase(),
                        prod.model.toLowerCase(),
                        prod.product_name.toLowerCase(),
                        prod.category.toLowerCase(),
                        dispName,
                        prod.control_no.toLowerCase(),
                        ...Object.values(prod.raw_fields).map(v => String(v || '').toLowerCase())
                    ].join(' ');

                    const matchesAll = tokens.every(t => fullText.includes(t));
                    if (!matchesAll) continue;
                }

                results.push(prod);
                if (results.length >= limit) break;
            }
            if (results.length >= limit) break;
        }

        res.end(JSON.stringify({
            success: true,
            query: { search_query: query.q || query.search_query, brand: query.brand, model: query.model, category: query.category },
            total_results: results.length,
            results
        }));
        return;
    }

    if (pathname.startsWith('/api/pelp/category/') || pathname.startsWith('/api/pelp/appliances/')) {
        const parts = pathname.split('/');
        const slug = parts[parts.length - 1];
        const limit = parseInt(query.limit || 100, 10);

        if (!PELP_SLUG_TO_NAME[slug]) {
            res.writeHead(404);
            res.end(JSON.stringify({ error: `Unknown category '${slug}'` }));
            return;
        }

        const rows = (data[slug] || []).slice(0, limit);
        const prods = rows.map(r => extractNormalizedProduct(r, slug));
        res.end(JSON.stringify({
            category: slug,
            display_name: PELP_SLUG_TO_NAME[slug],
            total_count: (data[slug] || []).length,
            limit,
            products: prods
        }));
        return;
    }

    res.end(JSON.stringify({ status: 'ok', service: 'DOE PELP Appliance Data API' }));
}

const server = http.createServer((req, res) => {
    sendCorsHeaders(res);

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    const parsedUrl = url.parse(req.url, true);
    let pathname = parsedUrl.pathname;

    if (pathname === '/') {
        pathname = '/index.html';
    }

    // API Routes
    if (pathname === '/api/health' || pathname === '/api/health.py') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        const serverHasKey = Boolean(process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY.trim() !== '');
        res.end(JSON.stringify({
            status: 'ok',
            serverHasKey,
            maxImagesSupported: 3,
            defaultModel: 'gemini-3.7-flash',
            supportedModels: ['gemini-3.7-flash', 'gemini-2.5-flash', 'gemini-flash-latest']
        }));
        return;
    }

    if (pathname === '/api/rates' || pathname === '/api/rates.py') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        const ratesPath = path.join(PROJECT_DIR, 'rates.json');
        if (fs.existsSync(ratesPath)) {
            fs.createReadStream(ratesPath).pipe(res);
        } else {
            res.end(JSON.stringify({ rates: DEFAULT_RATES }));
        }
        return;
    }

    if (pathname === '/api/appliances' || pathname === '/api/appliances.py') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        const dbPath = path.join(PROJECT_DIR, 'appliance_db.json');
        if (fs.existsSync(dbPath)) {
            fs.createReadStream(dbPath).pipe(res);
        } else {
            res.end(JSON.stringify({ appliances: [] }));
        }
        return;
    }

    if (pathname.startsWith('/api/pelp')) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        handlePelpApi(req, res, parsedUrl);
        return;
    }

    if (pathname === '/api/calculate' || pathname === '/api/calculate.py') {
        if (req.method === 'GET') {
            const kwh = parseFloat(parsedUrl.query.kwh || 0);
            const genRate = parseFloat(parsedUrl.query.gen_rate || 9.2504);
            const other = parseFloat(parsedUrl.query.other || 0);
            const result = performCalculation(kwh, genRate, other);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result, null, 2));
        } else if (req.method === 'POST') {
            let body = '';
            req.on('data', chunk => { body += chunk.toString(); });
            req.on('end', () => {
                let payload = {};
                try { payload = JSON.parse(body); } catch (e) {}
                const kwh = parseFloat(payload.kwh || 0);
                const genRate = parseFloat(payload.generation_rate || payload.gen_rate || 9.2504);
                const other = parseFloat(payload.other_charges || payload.other || 0);
                const result = performCalculation(kwh, genRate, other);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result, null, 2));
            });
        }
        return;
    }

    if (pathname === '/api/analyze' || pathname === '/api/analyze.py') {
        if (req.method !== 'POST') {
            res.writeHead(405, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Method Not Allowed' }));
            return;
        }

        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', async () => {
            try {
                let payload = {};
                try { payload = JSON.parse(body); } catch (e) {}
                const { images = [], imageBase64, mimeType = 'image/jpeg', prompt, preset = 'specs', model = 'gemini-3.7-flash' } = payload;

                const apiKey = process.env.GEMINI_API_KEY?.trim();
                if (!apiKey) {
                    res.writeHead(401, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        error: 'Missing Gemini API Key',
                        message: 'No GEMINI_API_KEY configured in server environment variables.'
                    }));
                    return;
                }

                let imageList = [];
                if (Array.isArray(images) && images.length > 0) {
                    imageList = images.slice(0, 3);
                } else if (imageBase64) {
                    imageList = [{ imageBase64, mimeType }];
                }

                if (imageList.length === 0) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        error: 'Missing Appliance Images',
                        message: 'No image data received. Please upload at least 1 appliance photo.'
                    }));
                    return;
                }

                const parts = [];
                imageList.forEach(imgObj => {
                    const cleanBase64 = (imgObj.imageBase64 || imgObj.data || '').replace(/^data:image\/[a-zA-Z]+;base64,/, '');
                    const itemMime = imgObj.mimeType || 'image/jpeg';
                    parts.push({
                        inline_data: {
                            mime_type: itemMime,
                            data: cleanBase64
                        }
                    });
                });

                const multiNotice = imageList.length > 1
                    ? `\n\nNOTE: The user provided ${imageList.length} multi-angle photos of this appliance. Cross-reference all ${imageList.length} images to identify exact brand, model, estimated wattage, voltage, and electrical specifications.`
                    : '';

                const systemPromptPrefix = `You are ApplianceSpec AI, an expert mechanical, electrical, and household appliance engineering AI.
Your objective is to identify household, kitchen, commercial, or HVAC appliances from photo(s) and generate technical specifications.${multiNotice}`;

                const presetInstructions = {
                    specs: `${systemPromptPrefix}\nFormat your analysis with clear Markdown sections:\n1. **APPLIANCE IDENTIFICATION** (Appliance Name, Category, Brand & Model, Form Factor)\n2. **ESTIMATED POWER & WATTAGE** (Running Wattage, Voltage/Hz, Estimated Daily Hours, Monthly kWh, Energy Class)\n3. **TECHNICAL SPECIFICATIONS** (Capacity, Motor/Compressor tech, Control Panel)\n4. **MAINTENANCE & CARE GUIDE** (Cleaning schedule, filter replacement, error codes)\n5. **ESTIMATED MARKET PRICE**`,
                    electrical: `${systemPromptPrefix}\nFocus strictly on Electrical & Power specs: Running vs Surge Wattage, Voltage/Amperage, Annual kWh consumption, Safety marks, Breaker requirement.`,
                    maintenance: `${systemPromptPrefix}\nFocus strictly on Routine Cleaning, Filter replacement codes, Descaling procedures, and Error code troubleshooting.`,
                    serial_ocr: `${systemPromptPrefix}\nPerform OCR on physical rating label/tag: Brand, Model Number, Serial Number, Electrical rating (V, Hz, W, A), Safety badges (UL, CE, etc.).`,
                    custom: `${systemPromptPrefix}\n${prompt || 'Provide technical specs for this appliance.'}`
                };

                const finalPrompt = presetInstructions[preset] || `${systemPromptPrefix}\n${prompt || 'Provide full technical specifications.'}`;
                parts.push({ text: finalPrompt });

                const targetModel = model || 'gemini-3.7-flash';
                const postData = JSON.stringify({ contents: [{ parts }] });

                const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${targetModel}:generateContent?key=${apiKey}`;

                const apiReq = https.request(geminiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Content-Length': Buffer.byteLength(postData)
                    }
                }, (apiRes) => {
                    let resBody = '';
                    apiRes.on('data', chunk => { resBody += chunk; });
                    apiRes.on('end', () => {
                        try {
                            const parsedRes = JSON.parse(resBody);
                            if (apiRes.statusCode >= 400 || parsedRes.error) {
                                res.writeHead(apiRes.statusCode || 500, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({
                                    error: 'Appliance Analysis Failed',
                                    message: parsedRes.error?.message || `Gemini API returned status ${apiRes.statusCode}`
                                }));
                                return;
                            }

                            const textResult = parsedRes.candidates?.[0]?.content?.parts?.[0]?.text || '';
                            res.writeHead(200, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({
                                success: true,
                                modelUsed: targetModel,
                                imageCount: imageList.length,
                                preset,
                                analysis: textResult,
                                timestamp: new Date().toISOString()
                            }));
                        } catch (err) {
                            res.writeHead(500, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ error: 'Parse Error', message: err.message }));
                        }
                    });
                });

                apiReq.on('error', (err) => {
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Request Failed', message: err.message }));
                });

                apiReq.write(postData);
                apiReq.end();

            } catch (err) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Server Error', message: err.message }));
            }
        });
        return;
    }

    // Static Files — with path traversal protection
    let filePath = path.resolve(path.join(PROJECT_DIR, pathname));
    if (!filePath.startsWith(path.resolve(PROJECT_DIR))) {
        res.writeHead(403, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Forbidden' }));
        return;
    }
    fs.stat(filePath, (err, stats) => {
        if (err || !stats.isFile()) {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'File not found' }));
            return;
        }

        const ext = path.extname(filePath).toLowerCase();
        const contentType = MIME_TYPES[ext] || 'application/octet-stream';
        res.writeHead(200, { 'Content-Type': contentType });
        fs.createReadStream(filePath).pipe(res);
    });
});

server.listen(PORT, () => {
    console.log(`PowerForecast Local Web & API Server running on http://localhost:${PORT}`);
});
