import {defineConfig} from '@playwright/test';
const python=process.platform==='win32'?'.venv\\Scripts\\python.exe':'python';
export default defineConfig({
  testDir:'tests/browser',workers:1,use:{headless:true,trace:'retain-on-failure',channel:process.env.PLAYWRIGHT_CHANNEL||undefined},
  webServer:[
    {command:`${python} -m uvicorn backend.main:app --host 127.0.0.1 --port 8790 --no-proxy-headers --no-access-log`,url:'http://127.0.0.1:8790/healthz',env:{EPISTEME_MODE:'public',PUBLIC_SITE_URL:'https://example.org'},reuseExistingServer:false},
    {command:`${python} -m uvicorn backend.main:app --host 127.0.0.1 --port 8791 --no-proxy-headers --no-access-log`,url:'http://127.0.0.1:8791/healthz',env:{EPISTEME_MODE:'local',EPISTEME_DB:'tmp/browser-tests.sqlite3'},reuseExistingServer:false}
  ]
});
