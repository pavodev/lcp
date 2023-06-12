const { defineConfig } = require("@vue/cli-service");
const isVian = process.env.APP_TYPE == "vian"
const appType = isVian ? "vian" : "lcp";
const monacoWebpackPlugin = require("monaco-editor-webpack-plugin");

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    open: false,
  },
  configureWebpack: config => {
    config.entry.app = [`./src/main.${appType}.js`]
    config.plugins = [
      ...config.plugins,
      new monacoWebpackPlugin(),
    ]
  },
});
