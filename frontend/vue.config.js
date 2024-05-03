const { defineConfig } = require("@vue/cli-service");
const appTypes = ["lcp", "videoscope", "soundscript", "catchphrase"]
const webpack = require('webpack');
const appType = appTypes.includes(process.env.APP_TYPE) ? process.env.APP_TYPE : "lcp";
const monacoWebpackPlugin = require("monaco-editor-webpack-plugin");
const {gitDescribeSync} = require('git-describe');

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
      new webpack.DefinePlugin({
        'process.env.APP_TYPE': JSON.stringify(appType),
        'process.env.GIT_HASH': JSON.stringify(gitDescribeSync().hash),
      }),
    ]
  },
});
