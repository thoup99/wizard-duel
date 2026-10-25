import {defineConfig} from '@playwright/test';
export default defineConfig({
 testDir:'./browser-tests',workers:1,timeout:30000,retries:0,
 use:{baseURL:'http://127.0.0.1:8765',viewport:{width:1440,height:1000},screenshot:'only-on-failure',launchOptions:{executablePath:process.env.POCKET_CHROMIUM||undefined,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}},
 webServer:{command:'python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765',url:'http://127.0.0.1:8765/api/health',reuseExistingServer:!process.env.CI,timeout:20000}
});
