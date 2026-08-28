import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'https://frontend-phi-three-52.vercel.app';
const BACKEND_URL = 'https://qa-framework-production.up.railway.app';

test('Debug: Verificar peticiones HTTP', async ({ page, request }) => {
  // 1. Probar login directo al backend
  console.log('\n=== TEST 1: Login directo al backend ===');
  const loginResponse = await request.post(`${BACKEND_URL}/api/v1/auth/login`, {
    headers: { 'Content-Type': 'application/json' },
    data: { username: 'Joker', password: 'Joker123!' }
  });
  console.log(`Status: ${loginResponse.status()}`);
  const loginData = await loginResponse.json();
  console.log(`Response: ${JSON.stringify(loginData).substring(0, 200)}...`);
  
  if (loginData.access_token) {
    console.log('✅ Login API funciona - token recibido');
    
    // 2. Probar getMe con el token
    console.log('\n=== TEST 2: getMe con token ===');
    const meResponse = await request.get(`${BACKEND_URL}/api/v1/me`, {
      headers: { 'Authorization': `Bearer ${loginData.access_token}` }
    });
    console.log(`Status: ${meResponse.status()}`);
    const meData = await meResponse.json();
    console.log(`User: ${JSON.stringify(meData).substring(0, 200)}...`);
    
    if (meData.username) {
      console.log('✅ getMe funciona - usuario recibido');
    } else {
      console.log('❌ getMe falló');
    }
  } else {
    console.log('❌ Login API falló');
  }
  
  // 3. Probar desde el frontend con network monitoring
  console.log('\n=== TEST 3: Login desde frontend ===');
  
  // Capturar todas las peticiones
  const requests: any[] = [];
  page.on('request', req => {
    if (req.url().includes('/api/') || req.url().includes('railway.app')) {
      requests.push({
        url: req.url(),
        method: req.method()
      });
    }
  });
  
  page.on('response', async res => {
    if (res.url().includes('/auth/login') || res.url().includes('/me')) {
      try {
        const text = await res.text();
        console.log(`\n📥 Response from ${res.url()}:`);
        console.log(`   Status: ${res.status()}`);
        console.log(`   Body: ${text.substring(0, 300)}...`);
      } catch {}
    }
  });
  
  // Ir al frontend y hacer login
  await page.goto(`${FRONTEND_URL}/login`);
  await page.waitForLoadState('networkidle');
  
  await page.locator('input').nth(0).fill('Joker');
  await page.locator('input').nth(1).fill('Joker123!');
  await page.click('button:has-text("Login")');
  
  await page.waitForTimeout(5000);
  
  console.log('\n📊 Peticiones capturadas:');
  requests.forEach((r, i) => {
    console.log(`   ${i+1}. ${r.method} ${r.url}`);
  });
  
  // Screenshot final
  await page.screenshot({ path: 'test-results/debug-requests.png' });
});
