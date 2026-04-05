<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { NodeTemplate } from "./nodeTemplate";
    
    const dispatch = createEventDispatcher();
    
    export let template: NodeTemplate;
    export let config: Record<string, any> = {};

    $: params = (config.params ?? {}) as Record<string, any>;

    function updateParam(name: string, value: any) {
            dispatch('configchange', {...config, params: { ...params, [name]: value}})
    }
</script>

<div class="text-gray-600 dark:text-gray-400 space-y-2">
    {#each template.params as param }
        <div>
            <div class="mb-0.5 text-[10px] text-gray-500 flex items-center gap-1">
                {param.label}
                {#if param.required}<span class="text-red-400">*</span>{/if}
            </div>
            {#if param.type === 'boolean'}
                <label class="flex items-center gap-1.5 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={params[param.name] ?? param.default ?? false}
                        on:change={(e) => updateParam(param.name, e.currentTarget.checked)}
                        class="rounded border-gray-300 dark:border-gray-600"
                    />
                </label>
            {:else if param.type === 'number'}
                <input
                    type="number"
                    value={params[param.name]?? param.default ?? ''}
                    placeholder={param.required ? 'required' : 'optional'}
                    on:input={(e) => {
                        const v = e.currentTarget.value;
                        updateParam(param.name, v === '' ? null : Number(v));
                    }}
                    class="w-full rounded bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-2 py-1 text-[11px] text-gray-700 dark:text-gray-300 outline-none"
                />
            {:else if param.type === 'string_list'}
                <textarea
                    value={(params[param.name] ?? param.default ?? []).join('\n')}
                    placeholder={param.required ? 'required (one per line)' : 'optional (one per line)'}
                    on:input={(e) => updateParam(param.name, e.currentTarget.value.split('\n').filter(s => s.trim() !== ''))}
                    rows="3"
                    class="w-full rounded bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-2 py-1 text-[11px] text-gray-700 dark:text-gray-300 outline-none resize-y"
                />
            {:else if param.type === 'select'}
                <select
                    value={params[param.name] ?? param.default ?? ''}
                    on:change={(e) => updateParam(param.name, e.currentTarget.value)}
                    class="w-full rounded bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-2 py-1 text-[11px] text-gray-700 dark:text-gray-300 outline-none"
                >
                    {#each param.options ?? [] as opt}
                        <option value={opt}>{opt}</option>
                    {/each}
                </select>
            {:else}
                <input
					type="text"
					value={params[param.name] ?? param.default ?? ''}
					placeholder={param.required ? 'required' : 'optional'}
					on:input={(e) => updateParam(param.name, e.currentTarget.value)}
					class="w-full rounded bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-2 py-1 text-[11px] text-gray-700 dark:text-gray-300 outline-none"
				/>
            {/if}
        </div>
    {/each}
</div>