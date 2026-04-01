import http from 'k6/http';
import { check, sleep } from 'k6';
import encoding from 'k6/encoding';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';

// === CONFIG ===
const config = JSON.parse(open('./test_config.json'));
const baseURL = config.baseURL || '';
const requestEndpointsRaw = Array.isArray(config.requestEndpoints) ? config.requestEndpoints : [];
const authConfig = config.auth || {};
const k6cfg = config.k6 || {};
let logConfig = k6cfg.logging || { enabled: false, level: 'failed' };

// --- Normalize & validate logging config ---
logConfig.enabled = String(logConfig.enabled).toLowerCase() === 'true' || logConfig.enabled === true;

const LOG_LEVEL_ALL = 'all';
const LOG_LEVEL_FAILED = 'failed';
const LOG_LEVEL_FAILED_WITHOUT_PAYLOADS = 'failed_without_payloads';
const LOGGING_LEVELS = [LOG_LEVEL_ALL, LOG_LEVEL_FAILED, LOG_LEVEL_FAILED_WITHOUT_PAYLOADS];

function normalizeLoggingLevel(rawLevel) {
  return String(rawLevel || '').trim();
}

logConfig.level = normalizeLoggingLevel(logConfig.level);
if (logConfig.enabled && !LOGGING_LEVELS.includes(logConfig.level)) {
  throw new Error(`❌ Unsupported k6.logging.level: ${logConfig.level}`);
}

const AUTH_MODE_NONE = 'none';
const AUTH_MODE_BASIC = 'basic';
const AUTH_MODE_CLIENT_ID_ENFORCEMENT = 'client_id_enforcement';
const AUTH_MODE_OAUTH2_CLIENT_CREDENTIALS = 'oauth2_client_credentials';
const AUTH_MODES = [
  AUTH_MODE_NONE,
  AUTH_MODE_BASIC,
  AUTH_MODE_CLIENT_ID_ENFORCEMENT,
  AUTH_MODE_OAUTH2_CLIENT_CREDENTIALS,
];

function resolveAuthMode(auth) {
  const mode = String(auth.mode || '').trim();
  if (!mode) {
    return AUTH_MODE_NONE;
  }
  if (!AUTH_MODES.includes(mode)) {
    throw new Error(`❌ Unsupported auth.mode: ${mode}`);
  }
  return mode;
}

const authMode = resolveAuthMode(authConfig);

function normalizeEndpoints() {
  return requestEndpointsRaw
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
if (requestEndpoints.length === 0) {
  throw new Error('❌ config.requestEndpoints must contain at least one valid endpoint object.');
}
const REQUEST_MODE_BATCH = 'batch';
const REQUEST_MODE_SCENARIOS = 'scenarios';
const requestMode = String(k6cfg.requestMode || REQUEST_MODE_BATCH).trim().toLowerCase();
if (![REQUEST_MODE_BATCH, REQUEST_MODE_SCENARIOS].includes(requestMode)) {
  throw new Error(`❌ Unsupported k6.requestMode: ${requestMode}`);
}

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

  if (data.authType === AUTH_MODE_BASIC || data.authType === AUTH_MODE_CLIENT_ID_ENFORCEMENT) {
    Object.assign(headers, data.authHeaders);
  } else if (data.authType === AUTH_MODE_OAUTH2_CLIENT_CREDENTIALS) {
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
  const failedWithoutPayloads = logConfig.enabled && logConfig.level === LOG_LEVEL_FAILED_WITHOUT_PAYLOADS;

  if (logConfig.enabled && (logConfig.level === LOG_LEVEL_ALL || (!ok && logConfig.level === LOG_LEVEL_FAILED))) {
    let prettyResBody;
    try {
      prettyResBody = JSON.stringify(JSON.parse(res.body), null, 2);
    } catch (e) {
      prettyResBody = res.body;
    }

    let logReqBody = req.body;
    if (typeof logReqBody === 'object' && logReqBody !== null) logReqBody = JSON.stringify(logReqBody);

    const entry =
      `
[${new Date().toISOString()}] ${ok ? '✅ SUCCESS' : '❌ FAILED'} (${req.name})
` +
      `URL: ${req.url}
Method: ${req.method}
` +
      `Request Headers: ${JSON.stringify(req.params.headers, null, 2)}
` +
      `Request Body: ${logReqBody}
` +
      `Query Params: ${req.query}
` +
      `Status: ${res.status}
Response Headers: ${JSON.stringify(res.headers, null, 2)}
` +
      `Response Body: ${prettyResBody}
` +
      `-----------------------------------
`;

    console.log(entry);
  }

  if (failedWithoutPayloads && !ok) {
    console.log(`❌ Correlation-Id: ${correlationId} | Status: ${res.status}`);
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
  scenarios: buildScenarios(),
};

function buildScenarios() {
  const baseScenario = buildBaseScenario();
  if (requestMode === REQUEST_MODE_BATCH) {
    return { default: { ...baseScenario, exec: 'runBatchScenario' } };
  }

  const scenarios = {};
  requestEndpoints.forEach((endpoint, index) => {
    const safeName = `endpoint_${index + 1}`;
    scenarios[safeName] = {
      ...baseScenario,
      exec: `runScenarioEndpoint${index + 1}`,
      tags: { endpoint: endpoint.name || `Endpoint ${index + 1}` },
    };
  });

  return scenarios;
}

// --- setup ---
export function setup() {
  const headers = {};

  if (authMode === AUTH_MODE_NONE) {
    console.log('🔓 Using no auth');
    return { authType: AUTH_MODE_NONE };
  }

  if (authMode === AUTH_MODE_BASIC) {
    const encoded = encoding.b64encode(`${authConfig.client_id}:${authConfig.client_secret}`);
    headers['Authorization'] = `Basic ${encoded}`;
    console.log('🔐 Using Basic Auth');
    return { authType: AUTH_MODE_BASIC, authHeaders: headers };
  }

  if (authMode === AUTH_MODE_CLIENT_ID_ENFORCEMENT) {
    headers['client_id'] = authConfig.client_id;
    headers['client_secret'] = authConfig.client_secret;
    console.log('🔐 Using client_id_enforcement (client_id and client_secret in headers)');
    return { authType: AUTH_MODE_CLIENT_ID_ENFORCEMENT, authHeaders: headers };
  }

  if (authMode !== AUTH_MODE_OAUTH2_CLIENT_CREDENTIALS) {
    throw new Error(`❌ Unsupported auth.mode: ${authMode}`);
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
  return { authType: AUTH_MODE_OAUTH2_CLIENT_CREDENTIALS, authToken: `Bearer ${token}` };
}

export function runBatchScenario(data) {
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

function runSingleEndpoint(data, endpointIndex) {
  const endpoint = requestEndpoints[endpointIndex];
  if (!endpoint) {
    throw new Error(`❌ Missing endpoint for scenario index: ${endpointIndex}`);
  }
  const correlationId = uuidv4();
  const req = buildSingleRequest(endpoint, data, correlationId);
  const res = http.request(req.method, req.url, req.body, req.params);
  const ok = check(res, {
    [`${req.name} status 200`]: (r) => r.status === 200,
  });
  logRequestResult(req, res, ok, correlationId);
  sleep(Math.random() * 0.4 + 0.1);
}

export function runScenarioEndpoint1(data) { runSingleEndpoint(data, 0); }
export function runScenarioEndpoint2(data) { runSingleEndpoint(data, 1); }
export function runScenarioEndpoint3(data) { runSingleEndpoint(data, 2); }
export function runScenarioEndpoint4(data) { runSingleEndpoint(data, 3); }
export function runScenarioEndpoint5(data) { runSingleEndpoint(data, 4); }

export default runBatchScenario;

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data),
  };
}
