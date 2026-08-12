import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const ALLOWED_MODELS = new Set([
	"openai-codex/gpt-5.6-terra",
	"openai-codex/gpt-5.6-luna",
	"openai-codex/gpt-5.6-sol",
	"xai/grok-4.6",
	"cursor/grok-4.6",
	"opencode/deepseek-v4-flash",
	"synthetic/hf:moonshotai/Kimi-K3",
	"fireworks/accounts/fireworks/models/deepseek-v4-flash-0731",
	"fireworks/accounts/fireworks/models/kimi-k3",
	"deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731",
	"deepinfra/zai-org/GLM-5.2",
]);

type ModelLike = { provider: string; id: string };

function isAllowed(model: ModelLike): boolean {
	return ALLOWED_MODELS.has(`${model.provider}/${model.id}`);
}

/**
 * Pi has no public global model-registry allowlist. The model collection backs
 * both the selector and model lookup, so constrain it before interactive use.
 */
async function installAllowlist(ctx: { modelRegistry: unknown }) {
	const registry = ctx.modelRegistry as any;
	const runtime = registry.runtime;
	const collection = runtime?.models;
	if (!runtime || !collection) {
		throw new Error("Pi model runtime is unavailable; cannot install the model allowlist");
	}
	if (collection.__aiConfigsModelAllowlistVersion === 2) return;

	const getModels = collection.getModels.bind(collection);
	const getModel = collection.getModel.bind(collection);
	const getAvailable = collection.getAvailable.bind(collection);

	collection.getModels = (provider?: string) =>
		getModels(provider).filter((model: ModelLike) => isAllowed(model));
	collection.getModel = (provider: string, modelId: string) => {
		if (!ALLOWED_MODELS.has(`${provider}/${modelId}`)) return undefined;
		return getModel(provider, modelId);
	};
	collection.getAvailable = async (provider?: string, options?: unknown) =>
		(await getAvailable(provider, options)).filter((model: ModelLike) => isAllowed(model));
	collection.__aiConfigsModelAllowlistVersion = 2;

	// Rebuild model and availability snapshots through Pi's public refresh API.
	await registry.refresh({ allowNetwork: false });
}

export default function (pi: ExtensionAPI) {
	pi.on("session_start", async (_event, ctx) => await installAllowlist(ctx));
}
