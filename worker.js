const UPGRAD_DOMAINS = [
  'prod-auth-api.upgrad.com',
  'prod-learn-api.upgrad.com',
  'prodapi.upgrad.com',
  'learnerprogress.upgrad.com',
];

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get('Origin') || '*';

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    const url = new URL(request.url);
    const target = url.searchParams.get('url');

    if (!target) {
      return new Response(JSON.stringify({ error: 'Missing ?url= parameter' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) },
      });
    }

    let targetUrl;
    try { targetUrl = new URL(target); }
    catch(e) {
      return new Response(JSON.stringify({ error: 'Invalid URL' }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) },
      });
    }

    const allowed = UPGRAD_DOMAINS.some(d => targetUrl.hostname === d);
    if (!allowed) {
      return new Response(JSON.stringify({ error: 'Domain not allowed: ' + targetUrl.hostname }), {
        status: 403, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) },
      });
    }

    // Build headers that look like a real browser on learn.upgrad.com
    const forwardHeaders = new Headers();

    // Copy safe headers from original request
    for (const [key, value] of request.headers.entries()) {
      const lower = key.toLowerCase();
      if (['host','origin','referer','cf-connecting-ip','cf-ipcountry',
           'cf-ray','cf-visitor','x-forwarded-for','x-forwarded-proto',
           'x-real-ip','true-client-ip'].includes(lower)) continue;
      forwardHeaders.set(key, value);
    }

    // Spoof to look like a real browser from learn.upgrad.com
    forwardHeaders.set('Origin', 'https://learn.upgrad.com');
    forwardHeaders.set('Referer', 'https://learn.upgrad.com/');
    forwardHeaders.set('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36');
    forwardHeaders.set('Accept', 'application/json, text/plain, */*');
    forwardHeaders.set('Accept-Language', 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7');
    forwardHeaders.set('sec-ch-ua', '"Chromium";v="124", "Google Chrome";v="124"');
    forwardHeaders.set('sec-ch-ua-mobile', '?0');
    forwardHeaders.set('sec-ch-ua-platform', '"Windows"');
    forwardHeaders.set('sec-fetch-dest', 'empty');
    forwardHeaders.set('sec-fetch-mode', 'cors');
    forwardHeaders.set('sec-fetch-site', 'same-site');

    const body = ['POST','PUT','PATCH'].includes(request.method)
      ? await request.arrayBuffer() : undefined;

    try {
      const proxiedResponse = await fetch(target, {
        method: request.method,
        headers: forwardHeaders,
        body,
      });

      const responseHeaders = new Headers();
      for (const [key, value] of proxiedResponse.headers.entries()) {
        const lower = key.toLowerCase();
        if (['access-control-allow-origin','access-control-allow-credentials',
             'access-control-expose-headers'].includes(lower)) continue;
        responseHeaders.set(key, value);
      }
      for (const [key, value] of Object.entries(corsHeaders(origin))) {
        responseHeaders.set(key, value);
      }
      responseHeaders.set('access-control-expose-headers',
        'auth-token, Auth-Token, REFRESH_TOKEN, Set-Cookie, COUNT, LINK');

      const responseBody = await proxiedResponse.arrayBuffer();
      return new Response(responseBody, {
        status: proxiedResponse.status,
        headers: responseHeaders,
      });
    } catch(e) {
      return new Response(JSON.stringify({ error: 'Proxy error: ' + e.message }), {
        status: 502, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) },
      });
    }
  },
};

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': origin || '*',
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, auth-token, Auth-Token, sessionid, sessionID, courseid, accept, origin, referer',
  };
}
