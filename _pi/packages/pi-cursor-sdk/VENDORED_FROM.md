# Vendored source provenance

This directory is a source vendor of [`adnichols/pi-cursor-sdk`](https://github.com/adnichols/pi-cursor-sdk) at commit [`a7d56a07b0356b090254d4ccf23b76af73c3f47d`](https://github.com/adnichols/pi-cursor-sdk/commit/a7d56a07b0356b090254d4ccf23b76af73c3f47d).

The installer mirrors this tree to `~/.pi/agent/local-packages/ai-configs/pi-cursor-sdk`, runs `npm ci --omit=dev`, and registers that stable local path with Pi. Do not commit `node_modules/` to this vendor tree.

The fork keeps `cursor_ask_question` disabled unless `PI_CURSOR_ASK_QUESTION=1` and ignores a model-refresh command once its originating Pi session runtime is shut down. This defaults-safe behavior addresses the orchestration-hang concern in upstream issue [#177](https://github.com/fitchmultz/pi-cursor-sdk/issues/177). The fork base had an upstream opt-out flag, but still enabled the tool when the flag was unset; this vendor changes that default for unattended runs.
