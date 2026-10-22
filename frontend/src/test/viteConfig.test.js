/**
 * @vitest-environment node
 */
import { describe, it, expect } from 'vitest';
import viteConfig, { getProxyTarget } from '../../vite.config.js';

describe('Vite Proxy Target Configuration', () => {
  it('defaults to http://localhost:8000 when VITE_DEV_PROXY_TARGET is unset', () => {
    const env = {};
    const target = getProxyTarget(env);
    expect(target).toBe('http://localhost:8000');
  });

  it('uses VITE_DEV_PROXY_TARGET when provided (e.g., http://backend:8000 for Docker)', () => {
    const env = { VITE_DEV_PROXY_TARGET: 'http://backend:8000' };
    const target = getProxyTarget(env);
    expect(target).toBe('http://backend:8000');
  });

  it('does not fall back to VITE_API_BASE_URL, keeping browser origin decoupled from container proxy', () => {
    const env = { VITE_API_BASE_URL: 'http://localhost:8000' };
    const target = getProxyTarget(env);
    // Even if VITE_API_BASE_URL is set, proxy target must use its own default localhost:8000 unless VITE_DEV_PROXY_TARGET is set
    expect(target).toBe('http://localhost:8000');
  });

  it('viteConfig includes proxy configuration for /api and /health', () => {
    expect(viteConfig.server?.proxy).toBeDefined();
    expect(viteConfig.server.proxy['/api']).toBeDefined();
    expect(viteConfig.server.proxy['/health']).toBeDefined();
    expect(viteConfig.server.proxy['/api'].changeOrigin).toBe(true);
    expect(viteConfig.server.proxy['/health'].changeOrigin).toBe(true);
  });
});
