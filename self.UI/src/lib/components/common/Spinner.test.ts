import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import Spinner from './Spinner.svelte';

describe('Spinner', () => {
	it('renders without crashing', () => {
		const { container } = render(Spinner);
		expect(container).toBeTruthy();
	});
});
