import http from 'k6/http';
import { check, sleep } from 'k6';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';

// === CONFIG ===
const config = JSON.parse(open('./test_config.json'));
const baseURL = config.baseURL || '';
const reqConfig = config.request || {};
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

// --- helpers ---
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

// --- options ---
const executionType = k6cfg.executionType || 'external executor';
const spikeStages = Array.isArray(k6cfg.spikeStages) ? k6cfg.spikeStages : [];

function buildScenarios() {
  if (executionType === 'Spike Tests') {
    const stages = spikeStages
      .map((stage) => ({
        duration: String((stage && stage.duration) || '').trim(),
        target: Number(stage && stage.target),
      }))
      .filter((stage) => stage.duration && Number.isFinite(stage.target) && stage.target >= 0)
      .map((stage) => ({ duration: stage.duration, target: Math.floor(stage.target) }));

    return {
      spike_test: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: stages.length ? stages : [{ duration: '30s', target: 10 }],
        gracefulRampDown: '0s',
      },
    };
  }

  return {
    default: {
      executor: 'externally-controlled',
      vus: k6cfg.vus || 1,
      maxVUs: k6cfg.maxVUs || 50,
      duration: k6cfg.duration || '60s',
    },
  };
}

export let options = {
  thresholds: k6cfg.thresholds || { 'http_req_duration': ['p(95)<5000'] },
  scenarios: buildScenarios(),
};

let lastWasError = false;

// --- setup ---
export function setup() {
  let headers = {};
  
  // For Basic Auth
  if (authConfig.basicauth) {
    const encoded = encodingBase64(`${authConfig.client_id}:${authConfig.client_secret}`);
    headers['Authorization'] = `Basic ${encoded}`;
    console.log(`🔐 Using Basic Auth`);
    return { authType: 'basic', authHeaders: headers };
  } 

  // For ClientId_Enforcement (send client_id and client_secret in headers without changing case)
  else if (authConfig.ClientId_Enforcement) {
    headers['client_id'] = authConfig.client_id;
    headers['client_secret'] = authConfig.client_secret;
    console.log(`🔐 Using ClientId_Enforcement (client_id and client_secret in headers)`);
    return { authType: 'clientid_headers', authHeaders: headers };
  } 
  
  // For OAuth2 (Bearer token)
  else if (authConfig.useOAuth2) {
    const resp = http.post(authConfig.token_url, {
      client_id: authConfig.client_id,
      client_secret: authConfig.client_secret,
      scope: authConfig.scope,
      grant_type: 'client_credentials',
    });
    if (resp.status !== 200)
      throw new Error('❌ OAuth2 token request failed: ' + resp.status);
    const token = resp.json()['access_token'];
    console.log(`🔐 Using OAuth2`);
    return { authType: 'oauth2', authToken: `Bearer ${token}` };
  }
}

// --- main ---
export default function (data) {
  const correlationId = uuidv4();

  // build headers (based on auth type)
  const headers = {};
  if (reqConfig.headers)
    for (const k in reqConfig.headers) headers[k] = reqConfig.headers[k];
  headers['Correlation-Id'] = correlationId;

  // Add auth-specific headers (Basic, ClientId_Enforcement, OAuth2)
  if (data.authType === 'basic') {
    Object.assign(headers, data.authHeaders); // Adding Basic Auth headers
  } else if (data.authType === 'clientid_headers') {
    Object.assign(headers, data.authHeaders); // Adding ClientId_Enforcement headers
  } else if (data.authType === 'oauth2') {
    headers['Authorization'] = data.authToken; // Bearer token for OAuth2
  }

  // query parameters
let query = '';
  if (reqConfig.query) {
    if (typeof reqConfig.query === 'object' && Object.keys(reqConfig.query).length > 0) {
      // Если это объект (пришло из валидного JSON в UI)
      const pairs = [];
      for (const k in reqConfig.query) {
        pairs.push(encodeURIComponent(k) + '=' + encodeURIComponent(reqConfig.query[k]));
      }
      query = '?' + pairs.join('&');
    } else if (typeof reqConfig.query === 'string' && reqConfig.query.trim().length > 0) {
      // Если это строка (пришло как обычный текст {x=2} или x=2)
      let qStr = reqConfig.query.trim();
      // Убираем фигурные скобки, если пользователь ввел их по привычке
      qStr = qStr.replace(/^\{|\}$/g, ''); 
      query = '?' + qStr;
    }
  }

  // 1. Формируем финальный URL
  const url = baseURL + (reqConfig.path || '') + query;
  
  // 2. Нормализуем метод (в верхний регистр)
  const method = (reqConfig.method || 'GET').toUpperCase();
  
  // 3. ИСПРАВЛЕНИЕ: Логика Body. 
  // Если метод GET или HEAD, принудительно обнуляем тело запроса.
  let body = reqConfig.body || null;
  if (method === 'GET' || method === 'HEAD') {
    body = null;
    delete headers['Content-Type'];
    delete headers['Content-Length'];
    delete headers['content-type'];
    delete headers['content-length'];
  } else if (body && typeof body === 'object') {
    // Если это объект, k6 сам превратит его в строку, но лучше сделать это явно
    body = JSON.stringify(body);
  }

  // 4. Выполняем запрос
  const res = http.request(method, url, body, { headers });
  
  // Проверка статуса
  const ok = check(res, { 'is status 200': (r) => r.status === 200 });

  // --- log to console based on logConfig ---
  if (logConfig.enabled && (logConfig.level === 'all' || (!ok && logConfig.level === 'failed'))) {
    
    // БЕЗОПАСНЫЙ ПАРСИНГ ТЕЛА ОТВЕТА
    let prettyResBody;
    try {
        prettyResBody = JSON.stringify(JSON.parse(res.body), null, 2);
    } catch (e) {
        prettyResBody = res.body;
    }

    // БЕЗОПАСНЫЙ ВЫВОД ТЕЛА ЗАПРОСА (чтобы в логах не было [object Object])
    let logReqBody = body;
    if (typeof body === 'object' && body !== null) logReqBody = JSON.stringify(body);

    const entry =
      `\n[${new Date().toISOString()}] ${ok ? '✅ SUCCESS' : '❌ FAILED'}\n` +
      `URL: ${url}\nMethod: ${method}\n` +
      `Request Headers: ${JSON.stringify(headers, null, 2)}\n` +
      `Request Body: ${logReqBody}\n` + // Исправлено отображение в логе
      `Query Params: ${query}\n` +
      `Status: ${res.status}\nResponse Headers: ${JSON.stringify(res.headers, null, 2)}\n` +
      `Response Body: ${prettyResBody}\n` + 
      `-----------------------------------\n`;

    console.log(entry);
    // console.log("DEBUG Content-Length:", res.headers['Content-Length']);
  }


  // --- console output ---
  if (ok) {
    if (lastWasError) {
      console.log('\n');
      lastWasError = false;
    }
    console.log(`\x1b[1A\x1b[2KProcessed request: ${res.status} ✅`);
  } else {
    console.log(`❌ Non-200 Response | Correlation-Id: ${correlationId} | Status: ${res.status}`);
    lastWasError = true;
  }

  sleep(Math.random() * 0.4 + 0.1);
}

// --- summary (always executes, Ctrl+C safe) ---
export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data),
  };
}
