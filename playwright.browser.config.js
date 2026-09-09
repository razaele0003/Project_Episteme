import {defineConfig} from '@playwright/test';
const python=process.platform==='win32'?'.venv\\Scripts\\python.exe':'python';
export default defineConfig({
  testDir:'tests/hosted',workers:1,use:{headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||undefined,baseURL:'http://127.0.0.1:8792'},
  webServer:[
    {command:`${python} -m uvicorn api.index:app --host 127.0.0.1 --port 8793`,url:'http://127.0.0.1:8793/api/browser-bootstrap'},
    {command:'npm exec vite -- --mode browser --host 127.0.0.1 --port 8792',url:'http://127.0.0.1:8792'}
  ]
});
