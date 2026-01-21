// read-truncation-warning-plugin.ts
var ReadTruncationPlugin = async (ctx) => {
  return {
    "tool.execute.after": async (input, output) => {
      if (input.tool !== "read")
        return;
      if (output.metadata?.truncated) {
        const currentOutput = output.output;
        const enhancedOutput = [
          "⚠️  FILE CONTENT TRUNCATED ⚠️",
          "",
          "The file content exceeds OpenCode's limits and has been truncated.",
          "- Individual lines are limited to 2000 characters",
          "- Total output is limited to 2000 lines or 50KB",
          "",
          "If you need to see more content, use the 'offset' parameter with the read tool.",
          "",
          "--- Truncated Content Below ---",
          "",
          currentOutput
        ].join(`
`);
        output.output = enhancedOutput;
      }
    }
  };
};
var read_truncation_warning_plugin_default = ReadTruncationPlugin;
export {
  read_truncation_warning_plugin_default as default,
  ReadTruncationPlugin
};
