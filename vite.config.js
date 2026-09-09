import { defineConfig } from 'vite';
export default defineConfig(({mode})=>({server:{proxy:{'/api':mode==='browser'?'http://127.0.0.1:8793':'http://127.0.0.1:8766'}}}));
