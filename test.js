import http from 'k6/http';
import { check, sleep } from 'k6';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';

// === CONFIG ===
const config = JSON.parse(open('./test_config.json'));
const baseURL = config.baseURL || '';
const reqConfig = config.request || {};
const requestEndpointsRaw = Array.isArray(config.requestEndpoints) ? config.requestEndpoints : [];
const authConfig = config.auth || {};
const k6cfg = config.k6 || {};
let logConfig = k6cfg.logging || { enabled: false, level: 'off' };

// --- Normalize & validate logging config ---
logConfig.enabled = String(logConfig.enabled).toLowerCase() === 'true' || logConfig.enabled === true;
logConfig.level = (logConfig.level || 'off').toLowerCase();
if (!['off', 'failed', 'all'].includes(logConfig.level)) logConfig.level = 'off';

// --- Validate auth modes ---
(function () {
  const modes = [
    authConfig.useOAuth2 ? 'OAuth2' : null,
    authConfig.basicauth ? 'BasicAuth' : null,
    authConfig.ClientId_Enforcement ? 'ClientId_Enforcement' : null,
  ].filter(Boolean);
  if (modes.length === 0)
    throw new Error('❌ No auth mode enabled! Set one of: useOAuth2, basicauth, ClientId_Enforcement.');
  if (modes.length > 1)
    throw new Error('❌ Multiple auth modes enabled simultaneously: ' + modes.join(', '));
})();

function encodingBase64(str) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
  let out = '', i = 0;
  while (i < str.length) {
    const chr1 = str.charCodeAt(i++), chr2 = str.charCodeAt(i++), chr3 = str.charCodeAt(i++);
    const enc1 = chr1 >> 2;
    const enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
    const enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
    const enc4 = chr3 & 63;
    if (isNaN(chr2)) out += chars.charAt(enc1) + chars.charAt(enc2) + '==';
    else if (isNaN(chr3)) out += chars.charAt(enc1) + chars.charAt(enc2) + chars.charAt(enc3) + '=';
    else out += chars.charAt(enc1) + chars.charAt(enc2) + chars.charAt(enc3) + chars.charAt(enc4);
  }
  return out;
}

function normalizeEndpoints() {
  const source = requestEndpointsRaw.length ? requestEndpointsRaw : [reqConfig];
  return source
    .filter((endpoint) => endpoint && typeof endpoint === 'object')
    .slice(0, 5)
    .map((endpoint, index) => ({
      name: String(endpoint.name || `Endpoint ${index + 1}`),
      method: String(endpoint.method || 'GET').toUpperCase(),
      path: endpoint.path || '',
      headers: endpoint.headers && typeof endpoint.headers === 'object' ? endpoint.headers : {},
      body: endpoint.body,
      query: endpoint.query,
    }));
}

const requestEndpoints = normalizeEndpoints();

function buildQuery(queryConfig) {
  if (!queryConfig) return '';

  if (typeof queryConfig === 'object' && Object.keys(queryConfig).length > 0) {
    const pairs = [];
    for (const k in queryConfig) {
      pairs.push(encodeURIComponent(k) + '=' + encodeURIComponent(queryConfig[k]));
    }
    return '?' + pairs.join('&');
  }

  if (typeof queryConfig === 'string' && queryConfig.trim().length > 0) {
    let qStr = queryConfig.trim();
    qStr = qStr.replace(/^\{|\}$/g, '');
    return '?' + qStr;
  }

  return '';
}

function buildSingleRequest(endpoint, data, correlationId) {
  const headers = {};

  for (const k in endpoint.headers) {
    headers[k] = endpoint.headers[k];
  }
  headers['Correlation-Id'] = correlationId;

  if (data.authType === 'basic' || data.authType === 'clientid_headers') {
    Object.assign(headers, data.authHeaders);
  } else if (data.authType === 'oauth2') {
    headers['Authorization'] = data.authToken;
  }

  const query = buildQuery(endpoint.query);
  const url = baseURL + endpoint.path + query;

  let body = endpoint.body || null;
  if (endpoint.method === 'GET' || endpoint.method === 'HEAD') {
    body = null;
    delete headers['Content-Type'];
    delete headers['Content-Length'];
    delete headers['content-type'];
    delete headers['content-length'];
  } else if (body && typeof body === 'object') {
    body = JSON.stringify(body);
  }

  return {
    name: endpoint.name,
    method: endpoint.method,
    url,
    query,
    body,
    params: { headers },
  };
}

function logRequestResult(req, res, ok, correlationId) {
  if (logConfig.enabled && (logConfig.level === 'all' || (!ok && logConfig.level === 'failed'))) {
    let prettyResBody;
    try {
      prettyResBody = JSON.stringify(JSON.parse(res.body), null, 2);
    } catch (e) {
      prettyResBody = res.body;
    }

    let logReqBody = req.body;
    if (typeof logReqBody === 'object' && logReqBody !== null) logReqBody = JSON.stringify(logReqBody);

    const entry =
      `\n[${new Date().toISOString()}] ${ok ? '✅ SUCCESS' : '❌ FAILED'} (${req.name})\n` +
      `URL: ${req.url}\nMethod: ${req.method}\n` +
      `Request Headers: ${JSON.stringify(req.params.headers, null, 2)}\n` +
      `Request Body: ${logReqBody}\n` +
      `Query Params: ${req.query}\n` +
      `Status: ${res.status}\nResponse Headers: ${JSON.stringify(res.headers, null, 2)}\n` +
      `Response Body: ${prettyResBody}\n` +
      `-----------------------------------\n`;

    console.log(entry);
  }

  if (ok) {
    console.log(`\x1b[1A\x1b[2KProcessed request: ${res.status} ✅`);
  } else {
    console.log(`❌ Non-200 Response (${req.name}) | Correlation-Id: ${correlationId} | Status: ${res.status}`);
  }
}

const executionType = k6cfg.executionType || 'external executor';
const spikeStages = Array.isArray(k6cfg.spikeStages) ? k6cfg.spikeStages : [];

function buildBaseScenario() {
  if (executionType === 'Spike Tests') {
    const stages = spikeStages
      .map((stage) => ({
        duration: String((stage && stage.duration) || '').trim(),
        target: Number(stage && stage.target),
      }))
      .filter((stage) => stage.duration && Number.isFinite(stage.target) && stage.target >= 0)
      .map((stage) => ({ duration: stage.duration, target: Math.floor(stage.target) }));

    return {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: stages.length ? stages : [{ duration: '30s', target: 10 }],
      gracefulRampDown: '0s',
    };
  }

  if (executionType === 'Constant VUs') {
    return {
      executor: 'constant-vus',
      vus: Number(k6cfg.vus) || 1,
      duration: String(k6cfg.duration || '60s'),
    };
  }

  if (executionType === 'Constant Arrival Rate') {
    return {
      executor: 'constant-arrival-rate',
      rate: Number(k6cfg.rate) || 10,
      timeUnit: String(k6cfg.timeUnit || '1s'),
      duration: String(k6cfg.duration || '60s'),
      preAllocatedVUs: Number(k6cfg.preAllocatedVUs) || 10,
      maxVUs: Number(k6cfg.maxVUs) || 50,
    };
  }

  if (executionType === 'Ramping Arrival Rate') {
    const stages = (Array.isArray(k6cfg.rampingArrivalStages) ? k6cfg.rampingArrivalStages : [])
      .map((stage) => ({
        duration: String((stage && stage.duration) || '').trim(),
        target: Number(stage && stage.target),
      }))
      .filter((stage) => stage.duration && Number.isFinite(stage.target) && stage.target >= 0)
      .map((stage) => ({ duration: stage.duration, target: Math.floor(stage.target) }));

    return {
      executor: 'ramping-arrival-rate',
      startRate: Number(k6cfg.startRate) || 1,
      timeUnit: String(k6cfg.timeUnit || '1s'),
      preAllocatedVUs: Number(k6cfg.preAllocatedVUs) || 10,
      maxVUs: Number(k6cfg.maxVUs) || 50,
      stages: stages.length ? stages : [{ duration: '30s', target: 10 }],
    };
  }

  return {
    executor: 'externally-controlled',
    vus: k6cfg.vus || 1,
    maxVUs: k6cfg.maxVUs || 50,
    duration: k6cfg.duration || '60s',
  };
}

export let options = {
  thresholds: k6cfg.thresholds || { 'http_req_duration': ['p(95)<5000'] },
  scenarios: { default: buildBaseScenario() },
};

// --- setup ---
export function setup() {
  const headers = {};

  if (authConfig.basicauth) {
    const encoded = encodingBase64(`${authConfig.client_id}:${authConfig.client_secret}`);
    headers['Authorization'] = `Basic ${encoded}`;
    console.log('🔐 Using Basic Auth');
    return { authType: 'basic', authHeaders: headers };
  }

  if (authConfig.ClientId_Enforcement) {
    headers['client_id'] = authConfig.client_id;
    headers['client_secret'] = authConfig.client_secret;
    console.log('🔐 Using ClientId_Enforcement (client_id and client_secret in headers)');
    return { authType: 'clientid_headers', authHeaders: headers };
  }

  const resp = http.post(authConfig.token_url, {
    client_id: authConfig.client_id,
    client_secret: authConfig.client_secret,
    scope: authConfig.scope,
    grant_type: 'client_credentials',
  });
  if (resp.status !== 200) throw new Error('❌ OAuth2 token request failed: ' + resp.status);
  const token = resp.json()['access_token'];
  console.log('🔐 Using OAuth2');
  return { authType: 'oauth2', authToken: `Bearer ${token}` };
}

export default function (data) {
  const correlationId = uuidv4();
  if (!requestEndpoints.length) throw new Error('❌ No request endpoints configured.');

  const batchRequests = requestEndpoints.map((endpoint) => buildSingleRequest(endpoint, data, correlationId));
  const responses = http.batch(batchRequests.map((req) => ({
    method: req.method,
    url: req.url,
    body: req.body,
    params: req.params,
  })));

  responses.forEach((res, index) => {
    const req = batchRequests[index];
    const ok = check(res, {
      [`${req.name} status 200`]: (r) => r.status === 200,
    });
    logRequestResult(req, res, ok, correlationId);
  });

  sleep(Math.random() * 0.4 + 0.1);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data),
  };
}
