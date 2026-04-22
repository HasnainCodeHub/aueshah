# Aueshah AI Concierge — WordPress Integration Roadmap

**For**: WordPress Developer
**Backend API**: Fully built and deployed (FastAPI)
**Goal**: Connect the Bespoke page chatbot to the backend with login-gated access

---

## Architecture Overview

```
User clicks "Start Bespoke" on /bespoke
        |
        v
Has session token in localStorage?
       / \
     YES   NO
      |      |
      v      v
Verify via   Redirect to /my-account/?redirect_to=/bespoke&action=chat
GET /v1/auth/me
      |            User logs in via WooCommerce
   Valid?          |
    / \            v
  YES  NO      WP JWT plugin issues RS256 token
   |    |          |
   v    v          v
Open  Clear     POST /v1/auth/wp-login { wp_token: "..." }
chat  token,        |
      redirect      v
   |          Backend verifies, creates user in DB,
   v          returns { access_token, expires_in, user }
POST /chat        |
with Bearer       v
token         Store token in localStorage
              Redirect back to /bespoke?chat=open
```

---

## Step 1: Install JWT Authentication Plugin

**What**: Install a WordPress plugin that issues RS256 JWTs and exposes a JWKS endpoint.

**Recommended Plugin**: [JWT Authentication for WP-API](https://wordpress.org/plugins/jwt-authentication-for-wp-rest-api/) or [Simple JWT Login](https://wordpress.org/plugins/simple-jwt-login/)

**After installation, verify these endpoints exist**:

| Endpoint | Method | Purpose |
|---|---|---|
| `/wp-json/jwt-auth/v1/token` | POST | Login with username + password, returns JWT |
| `/wp-json/jwt-auth/v1/jwks` | GET | Public keys (JWKS) for JWT verification |

**Test it works**:
```bash
# Should return a JWT
curl -X POST https://aueshah.com/wp-json/jwt-auth/v1/token \
  -H "Content-Type: application/json" \
  -d '{"username": "test@aueshah.com", "password": "testpass"}'

# Should return public keys
curl https://aueshah.com/wp-json/jwt-auth/v1/jwks
```

**JWT payload must contain these fields** (most WP JWT plugins include them by default):

```json
{
  "sub": 42,
  "email": "client@example.com",
  "display_name": "Client Name",
  "iss": "https://aueshah.com",
  "iat": 1700000000,
  "exp": 1700086400
}
```

If the plugin uses a nested structure like `data.user.id` / `data.user.email`, that also works — our backend handles both formats.

**Important**: The plugin MUST sign with **RS256** (RSA), not HS256. Check the plugin settings.

---

## Step 2: Share Plugin Details with Backend Team

Once the JWT plugin is installed, send us:

1. **JWKS URL** (e.g. `https://aueshah.com/wp-json/jwt-auth/v1/jwks`)
2. **Token endpoint URL** (e.g. `https://aueshah.com/wp-json/jwt-auth/v1/token`)
3. **Issuer value** from the JWT `iss` field (usually `https://aueshah.com`)

We will add these to our backend configuration. No code changes needed on our side.

---

## Step 3: Add the Chat Widget to the Bespoke Page

**Where**: Replace the existing `[openai_chat]` shortcode on `/bespoke` with a custom chat widget.

**Option A — Embed via WP shortcode** (recommended):
Create a custom shortcode `[aueshah_chat]` in your theme's `functions.php` or a custom plugin that loads the chat widget JS.

**Option B — Direct script embed**:
Add this to the bespoke page template.

### 3a. Create the chat container

Add this HTML where the chat should appear on `/bespoke`:

```html
<!-- Chat trigger button -->
<button id="aueshah-chat-btn" class="aueshah-bespoke-cta">
  Start Your Bespoke Journey
</button>

<!-- Chat modal (hidden by default) -->
<div id="aueshah-chat-modal" style="display:none;">
  <div id="aueshah-chat-header">
    <span>Aueshah Concierge</span>
    <button id="aueshah-chat-close">&times;</button>
  </div>
  <div id="aueshah-chat-messages"></div>
  <form id="aueshah-chat-form">
    <input type="text" id="aueshah-chat-input" placeholder="Type your message..." autocomplete="off" />
    <button type="submit">Send</button>
  </form>
</div>
```

### 3b. Add the JavaScript

Create a file `aueshah-chat.js` and enqueue it on the bespoke page:

```javascript
(function () {
  // ── Configuration ──
  const API_BASE = 'https://your-api-domain.com'; // Backend URL — we will provide this
  const LOGIN_URL = '/my-account/';

  // ── Token helpers ──
  function getToken() {
    return localStorage.getItem('aueshah_token');
  }

  function setToken(token) {
    localStorage.setItem('aueshah_token', token);
  }

  function clearToken() {
    localStorage.removeItem('aueshah_token');
    localStorage.removeItem('aueshah_user');
  }

  function getVisitorId() {
    let vid = localStorage.getItem('aueshah_visitor_id');
    if (!vid) {
      vid = crypto.randomUUID();
      localStorage.setItem('aueshah_visitor_id', vid);
    }
    return vid;
  }

  // ── Auth check ──
  async function verifyToken(token) {
    try {
      const res = await fetch(API_BASE + '/v1/auth/me', {
        headers: { 'Authorization': 'Bearer ' + token },
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Token verification failed', e);
    }
    return null;
  }

  // ── Login redirect ──
  function redirectToLogin() {
    const currentPage = window.location.pathname;
    window.location.href = LOGIN_URL + '?redirect_to=' + encodeURIComponent(currentPage) + '&action=chat';
  }

  // ── Chat API ──
  const conversationContext = [];

  async function sendMessage(message) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }

    const body = {
      message: message,
      context: conversationContext.slice(-15), // last 15 messages
      page_context: {
        page_type: 'bespoke',
        product_name: null,
        collection_name: null,
      },
    };

    const res = await fetch(API_BASE + '/chat', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(body),
    });

    if (res.status === 401) {
      clearToken();
      redirectToLogin();
      return null;
    }

    const data = await res.json();

    // Store context for conversation continuity
    conversationContext.push({ role: 'user', content: message });
    conversationContext.push({ role: 'assistant', content: data.reply });

    return data;
  }

  // ── UI helpers ──
  function appendMessage(role, text) {
    const container = document.getElementById('aueshah-chat-messages');
    const div = document.createElement('div');
    div.className = 'aueshah-msg aueshah-msg-' + role;
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  function showChat() {
    document.getElementById('aueshah-chat-modal').style.display = 'flex';
  }

  function hideChat() {
    document.getElementById('aueshah-chat-modal').style.display = 'none';
  }

  // ── Main flow ──
  async function handleChatClick() {
    const token = getToken();

    if (!token) {
      // No token — must log in first
      redirectToLogin();
      return;
    }

    // Verify token is still valid
    const user = await verifyToken(token);
    if (!user) {
      clearToken();
      redirectToLogin();
      return;
    }

    // Token valid — open chat
    showChat();
  }

  // ── Auto-open if redirected back from login ──
  function checkAutoOpen() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('chat') === 'open') {
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
      handleChatClick();
    }
  }

  // ── Bind events ──
  document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('aueshah-chat-btn');
    if (btn) btn.addEventListener('click', handleChatClick);

    const closeBtn = document.getElementById('aueshah-chat-close');
    if (closeBtn) closeBtn.addEventListener('click', hideChat);

    const form = document.getElementById('aueshah-chat-form');
    if (form) {
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const input = document.getElementById('aueshah-chat-input');
        const msg = input.value.trim();
        if (!msg) return;

        input.value = '';
        appendMessage('user', msg);

        // Show typing indicator
        const typing = document.createElement('div');
        typing.className = 'aueshah-msg aueshah-msg-assistant aueshah-typing';
        typing.textContent = '...';
        document.getElementById('aueshah-chat-messages').appendChild(typing);

        const data = await sendMessage(msg);
        typing.remove();

        if (data && data.reply) {
          appendMessage('assistant', data.reply);
        }
      });
    }

    checkAutoOpen();
  });
})();
```

---

## Step 4: Handle Post-Login Token Exchange

**Where**: On the `/my-account/` page (or via a WP hook that fires after login).

After a successful WooCommerce login, check if the user was redirected from the bespoke page and exchange the WP JWT for our session token.

Add this script to the my-account page template (only runs when logged in):

```javascript
(function () {
  const API_BASE = 'https://your-api-domain.com'; // Same as in Step 3

  async function handlePostLoginRedirect() {
    const params = new URLSearchParams(window.location.search);
    const redirectTo = params.get('redirect_to');
    const action = params.get('action');

    // Only proceed if user was redirected from bespoke/chat
    if (!redirectTo || action !== 'chat') return;

    // Check if user is actually logged in (WP sets this cookie)
    if (!document.cookie.includes('wordpress_logged_in_')) return;

    // Step 1: Get WP JWT from the plugin endpoint
    // NOTE: Some plugins use cookie-based auth for this endpoint,
    // so the logged-in session cookie is enough.
    // If your plugin requires username/password, use the alternative approach below.
    let wpToken;
    try {
      const res = await fetch('/wp-json/jwt-auth/v1/token/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!res.ok) {
        // Alternative: If plugin doesn't support cookie-based token generation,
        // you may need to use a custom REST endpoint that mints a JWT
        // for the currently logged-in WP user. See Step 5 below.
        console.error('Could not get WP JWT');
        window.location.href = redirectTo;
        return;
      }

      const data = await res.json();
      wpToken = data.token || data.data?.token;
    } catch (e) {
      console.error('WP JWT fetch failed', e);
      window.location.href = redirectTo;
      return;
    }

    // Step 2: Exchange WP JWT for our backend session token
    try {
      const visitorId = localStorage.getItem('aueshah_visitor_id');
      const res = await fetch(API_BASE + '/v1/auth/wp-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wp_token: wpToken,
          visitor_id: visitorId,
        }),
      });

      if (!res.ok) {
        console.error('Backend token exchange failed');
        window.location.href = redirectTo;
        return;
      }

      const { access_token, user } = await res.json();

      // Step 3: Store our session token
      localStorage.setItem('aueshah_token', access_token);
      localStorage.setItem('aueshah_user', JSON.stringify(user));

      // Step 4: Redirect back to bespoke page with chat open
      window.location.href = redirectTo + '?chat=open';
    } catch (e) {
      console.error('Token exchange error', e);
      window.location.href = redirectTo;
    }
  }

  // Run when page loads
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', handlePostLoginRedirect);
  } else {
    handlePostLoginRedirect();
  }
})();
```

---

## Step 5 (If Needed): Custom WP REST Endpoint for Token Minting

If the JWT plugin doesn't support issuing a token for the currently logged-in user via cookies, add this to your theme's `functions.php`:

```php
<?php
// Custom endpoint: mint a JWT for the currently logged-in WP user
add_action('rest_api_init', function () {
    register_rest_route('aueshah/v1', '/mint-token', array(
        'methods'  => 'POST',
        'callback' => 'aueshah_mint_jwt_for_current_user',
        'permission_callback' => function () {
            return is_user_logged_in();
        },
    ));
});

function aueshah_mint_jwt_for_current_user(WP_REST_Request $request) {
    $user = wp_get_current_user();

    // Use the JWT plugin's internal function to generate a token
    // This varies by plugin. Example for "JWT Authentication for WP-API":
    $token = \Firebase\JWT\JWT::encode(
        array(
            'iss'  => get_bloginfo('url'),
            'iat'  => time(),
            'exp'  => time() + 300, // 5 min — short-lived, just for exchange
            'sub'  => $user->ID,
            'email' => $user->user_email,
            'display_name' => $user->display_name,
        ),
        // Use the same private key the JWT plugin uses
        file_get_contents(ABSPATH . 'wp-content/plugins/jwt-auth/keys/private.pem'),
        'RS256'
    );

    return new WP_REST_Response(array('token' => $token), 200);
}
```

Then in Step 4's JavaScript, replace the `/wp-json/jwt-auth/v1/token/validate` call with:

```javascript
const res = await fetch('/wp-json/aueshah/v1/mint-token', {
  method: 'POST',
  credentials: 'same-origin', // sends WP login cookies
});
```

---

## Step 6: Enqueue Scripts in WordPress

Add to your theme's `functions.php`:

```php
<?php
function aueshah_enqueue_chat_scripts() {
    // Only load on bespoke page
    if (is_page('bespoke')) {
        wp_enqueue_script(
            'aueshah-chat',
            get_template_directory_uri() . '/js/aueshah-chat.js',
            array(),
            '1.0.0',
            true // load in footer
        );
        wp_enqueue_style(
            'aueshah-chat-style',
            get_template_directory_uri() . '/css/aueshah-chat.css',
            array(),
            '1.0.0'
        );
    }

    // Load token exchange on my-account page
    if (is_page('my-account') && is_user_logged_in()) {
        wp_enqueue_script(
            'aueshah-token-exchange',
            get_template_directory_uri() . '/js/aueshah-token-exchange.js',
            array(),
            '1.0.0',
            true
        );
    }
}
add_action('wp_enqueue_scripts', 'aueshah_enqueue_chat_scripts');
```

---

## Step 7: Basic Chat Widget CSS

Create `aueshah-chat.css`:

```css
#aueshah-chat-modal {
  display: none;
  flex-direction: column;
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 380px;
  height: 520px;
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 12px;
  z-index: 99999;
  font-family: 'Georgia', serif;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

#aueshah-chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  background: linear-gradient(135deg, #2a1f0e, #1a1a1a);
  color: #c9a84c;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

#aueshah-chat-close {
  background: none;
  border: none;
  color: #999;
  font-size: 20px;
  cursor: pointer;
}

#aueshah-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.aueshah-msg {
  margin-bottom: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.5;
  max-width: 85%;
}

.aueshah-msg-user {
  background: #2a2a2a;
  color: #e0e0e0;
  margin-left: auto;
  text-align: right;
}

.aueshah-msg-assistant {
  background: #1e1509;
  color: #d4c5a0;
  border: 1px solid #3a2f1a;
}

.aueshah-typing {
  opacity: 0.5;
  font-style: italic;
}

#aueshah-chat-form {
  display: flex;
  padding: 12px;
  border-top: 1px solid #333;
  gap: 8px;
}

#aueshah-chat-input {
  flex: 1;
  padding: 10px 14px;
  background: #2a2a2a;
  border: 1px solid #444;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 14px;
  outline: none;
}

#aueshah-chat-input:focus {
  border-color: #c9a84c;
}

#aueshah-chat-form button[type='submit'] {
  padding: 10px 18px;
  background: #c9a84c;
  color: #1a1a1a;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.aueshah-bespoke-cta {
  padding: 14px 32px;
  background: linear-gradient(135deg, #c9a84c, #a8872a);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-family: 'Georgia', serif;
  letter-spacing: 1px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.aueshah-bespoke-cta:hover {
  opacity: 0.9;
}

/* Mobile responsive */
@media (max-width: 480px) {
  #aueshah-chat-modal {
    width: 100%;
    height: 100%;
    bottom: 0;
    right: 0;
    border-radius: 0;
  }
}
```

---

## Checklist

- [ ] **Step 1**: Install WP JWT plugin (RS256 + JWKS)
- [ ] **Step 1**: Test `POST /wp-json/jwt-auth/v1/token` returns a JWT
- [ ] **Step 1**: Test `GET /wp-json/jwt-auth/v1/jwks` returns public keys
- [ ] **Step 2**: Send us the JWKS URL, token endpoint URL, and issuer value
- [ ] **Step 3**: Add chat widget HTML + JS to `/bespoke` page
- [ ] **Step 4**: Add token exchange script to `/my-account/` page
- [ ] **Step 5**: (If needed) Add custom `/wp-json/aueshah/v1/mint-token` endpoint
- [ ] **Step 6**: Enqueue scripts in `functions.php`
- [ ] **Step 7**: Add chat widget CSS
- [ ] **Test**: Full flow — click bespoke CTA -> login -> redirect back -> chat opens
- [ ] **Test**: Returning user — already logged in -> chat opens immediately
- [ ] **Test**: Token expired -> user is asked to log in again

---

## Backend API Reference (for your reference)

**Base URL**: `https://your-api-domain.com` (we will provide the final URL)

### POST /v1/auth/wp-login
Exchange a WordPress JWT for our session token.

```
Request:
{
  "wp_token": "eyJhbGciOiJSUzI1NiIs...",
  "visitor_id": "optional-uuid-from-localStorage"
}

Response (200):
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid",
    "wp_user_id": 42,
    "email": "client@example.com",
    "display_name": "Client Name",
    "role": "client"
  }
}
```

### GET /v1/auth/me
Verify token and get user profile. Send on every page load to check if session is still valid.

```
Headers: Authorization: Bearer <access_token>

Response (200):
{
  "id": "uuid",
  "wp_user_id": 42,
  "email": "client@example.com",
  "display_name": "Client Name",
  "age_range": null,
  "skin_tone": null,
  "style_preference": null,
  "role": "client"
}

Response (401): Token expired or invalid
```

### POST /chat
Send a message to the AI concierge.

```
Headers: Authorization: Bearer <access_token>  (optional — works without auth too)

Request:
{
  "message": "I'd like a custom ring",
  "context": [
    { "role": "user", "content": "previous message" },
    { "role": "assistant", "content": "previous reply" }
  ],
  "page_context": {
    "page_type": "bespoke",
    "product_name": null,
    "collection_name": null
  }
}

Response (200):
{
  "reply": "I'd love to help you design something truly personal...",
  "metadata": {
    "intent": "bespoke",
    "skill": "bespoke",
    "latency_ms": 1850
  }
}
```

### POST /v1/auth/logout
Client-side logout. Just discard the token from localStorage.

```
Response (200): { "status": "ok" }
```

---

## Questions?

Contact the backend team with:
1. Your JWKS URL after plugin installation
2. A sample JWT from the plugin (we can verify the format)
3. Any issues with CORS (we need to allowlist your domain)
