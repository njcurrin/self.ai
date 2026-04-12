import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [sveltekit()],
	define: {
		APP_VERSION: JSON.stringify('test'),
		APP_BUILD_HASH: JSON.stringify('test-build')
	},
	test: {
		environment: 'jsdom',
		include: ['src/**/*.{test,spec}.{js,ts}'],
		globals: true,
		setupFiles: ['./vitest-setup.ts'],
		alias: {
			'$app/navigation': './src/test-mocks/app-navigation.ts',
			'$app/stores': './src/test-mocks/app-stores.ts',
			'$app/environment': './src/test-mocks/app-environment.ts'
		}
	}
});
