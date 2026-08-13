import type { ExtensionAPI, ProviderModelConfig } from "@oh-my-pi/pi-coding-agent";
import type { OAuthLoginCallbacks } from "@oh-my-pi/pi-ai/oauth/types";

const catalog = "https://api.deepinfra.com/models/list";

type DeepInfraCatalogEntry = {
	model_name?: unknown;
	type?: unknown;
	private?: unknown;
	deprecated?: unknown;
	tags?: unknown;
	pricing?: unknown;
	max_tokens?: unknown;
};

function isDeprecated(value: unknown) {
	if (value === undefined || value === null || value === false) return false;
	return typeof value === "number" ? value * 1_000 <= Date.now() : true;
}

function price(value: unknown) {
	return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value * 10_000 : 0;
}

function model(value: unknown): ProviderModelConfig | undefined {
	if (typeof value !== "object" || value === null || Array.isArray(value)) return;
	const entry = value as DeepInfraCatalogEntry;
	if (entry.type !== "text-generation" || entry.private || isDeprecated(entry.deprecated)) {
		return;
	}

	const id = entry.model_name;
	if (typeof id !== "string" || !id) return;

	const tags = Array.isArray(entry.tags)
		? new Set(entry.tags.filter((tag): tag is string => typeof tag === "string"))
		: new Set<string>();
	const pricing =
		typeof entry.pricing === "object" && entry.pricing !== null && !Array.isArray(entry.pricing)
			? (entry.pricing as { [key: string]: unknown })
			: {};
	const maxTokens =
		typeof entry.max_tokens === "number" &&
		Number.isSafeInteger(entry.max_tokens) &&
		entry.max_tokens > 0
			? entry.max_tokens
			: 8_192;

	return {
		id,
		name: id.split("/").at(-1) ?? id,
		reasoning: tags.has("reasoning") || tags.has("can-disable-reasoning"),
		input: tags.has("multimodal") ? ["text", "image"] : ["text"],
		cost: {
			input: price(pricing.cents_per_input_token),
			output: price(pricing.cents_per_output_token),
			cacheRead: 0,
			cacheWrite: 0,
		},
		contextWindow: Math.max(128_000, maxTokens),
		maxTokens,
	};
}

// DeepInfra's OpenAI-compatible inference and catalog APIs have separate roots.
export default function (pi: ExtensionAPI) {
	const configuredApiKey = process.env.DEEPINFRA_API_KEY ? "DEEPINFRA_API_KEY" : undefined;

	pi.registerProvider("deepinfra", {
		baseUrl: "https://api.deepinfra.com/v1/openai",
		api: "openai-completions",
		apiKey: configuredApiKey,
		authHeader: true,
		async fetchDynamicModels(apiKey) {
			const response = await fetch(catalog, {
				headers: apiKey === undefined ? undefined : { Authorization: `Bearer ${apiKey}` },
			});
			if (!response.ok) {
				throw new Error(`DeepInfra models request failed: HTTP ${response.status}.`);
			}

			const values = await response.json();
			if (!Array.isArray(values)) {
				throw new Error("DeepInfra models response was not an array.");
			}
			return values.map(model).filter((value): value is ProviderModelConfig => value !== undefined);
		},
		oauth: {
			name: "DeepInfra",
			async login(callbacks: OAuthLoginCallbacks) {
				callbacks.onAuth({
					url: "https://deepinfra.com/dash/api_keys",
					instructions: "Create or copy a DeepInfra API key, then paste it below.",
				});

				const apiKey = (
					await callbacks.onPrompt({
						message: "Paste your DeepInfra API key",
						placeholder: "...",
					})
				).trim();

				if (!apiKey) {
					throw new Error("A DeepInfra API key is required.");
				}

				return apiKey;
			},
		},
	});
}
