const { defineConfig } = require("@vue/cli-service");
const isVian = process.env.APP_TYPE == "vian"
const appType = isVian ? "vian" : "lcp";

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    open: false,
  },
  configureWebpack: config => {
    config.entry.app = [`./src/main.${appType}.js`]
  },

});
