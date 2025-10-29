/**
 * Webpack Source Map Configuration for Sentry
 *
 * This configuration generates and uploads source maps to Sentry for
 * readable stack traces in production.
 *
 * Features:
 * - Hidden source maps (not exposed to public)
 * - Automatic upload to Sentry
 * - Release tracking
 * - Clean up after upload
 */

const path = require('path');
const { SentryWebpackPlugin } = require('@sentry/webpack-plugin');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';

  return {
    mode: argv.mode || 'development',

    entry: './src/index.js',

    output: {
      filename: '[name].[contenthash].js',
      sourceMapFilename: '[name].[contenthash].js.map',
      path: path.resolve(__dirname, 'dist'),
      clean: true,
    },

    // Source map configuration
    devtool: isProduction ? 'hidden-source-map' : 'source-map',

    plugins: [
      // Only upload source maps in production
      isProduction && new SentryWebpackPlugin({
        // Authentication
        authToken: process.env.SENTRY_AUTH_TOKEN,
        org: process.env.SENTRY_ORG || 'my-org',
        project: process.env.SENTRY_PROJECT || 'my-project',

        // Source maps
        include: './dist',
        ignore: ['node_modules', 'webpack.config.js'],

        // Release version (must match Sentry.init release)
        release: process.env.RELEASE_VERSION || 'unknown',

        // Upload options
        urlPrefix: '~/static/js',  // Match your CDN/server path

        // Automatically set commit and deploy
        setCommits: {
          auto: true,
          ignoreMissing: true,
        },

        deploy: {
          env: process.env.NODE_ENV || 'production',
        },

        // Clean up source maps after upload
        cleanArtifacts: true,
        filesToDeleteAfterUpload: ['**/*.map'],

        // Silent mode (less noise in build output)
        silent: false,

        // Debugging
        debug: process.env.DEBUG === 'true',
      }),
    ].filter(Boolean),

    module: {
      rules: [
        {
          test: /\.js$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: ['@babel/preset-env'],
            },
          },
        },
      ],
    },

    resolve: {
      extensions: ['.js', '.jsx'],
    },
  };
};
