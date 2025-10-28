---
name: mobile-react-native-setup
description: Starting a new React Native project for iOS development
---



# React Native Setup

**Scope**: React Native project setup, Expo vs bare workflow, iOS development environment, tooling configuration
**Lines**: ~320
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Starting a new React Native project for iOS development
- Choosing between Expo and bare workflow approaches
- Setting up iOS development environment and dependencies
- Configuring Metro bundler and build tools
- Troubleshooting React Native setup and installation issues
- Migrating from Expo to bare workflow
- Configuring TypeScript and ESLint for React Native projects

## Core Concepts

### Expo vs Bare Workflow

**Expo Managed**:
- Pre-configured development environment
- OTA updates via Expo Go app
- Limited access to native modules
- Best for: MVPs, rapid prototyping, simple apps
- No need for Xcode initially

**Expo Bare**:
- Expo libraries + full native access
- Custom native modules available
- Build with EAS or locally
- Best for: Apps needing custom native code
- Requires Xcode and CocoaPods

**React Native CLI (Bare)**:
- Full control over native code
- Direct access to iOS APIs
- More complex setup
- Best for: Complex apps, existing native code integration
- Requires Xcode, CocoaPods, Ruby environment

### Metro Bundler

**Metro Role**:
- JavaScript bundler for React Native
- Hot reloading and fast refresh
- Module resolution and transformation
- Source maps for debugging

**Key Features**:
- Incremental bundling (fast rebuilds)
- Tree shaking (remove unused code)
- Asset resolution (images, fonts)
- Platform-specific extensions (.ios.ts, .android.ts)

### iOS Development Environment

**Required Tools**:
- **Xcode**: Latest stable version (15.0+)
- **Command Line Tools**: `xcode-select --install`
- **CocoaPods**: `sudo gem install cocoapods`
- **Node.js**: LTS version (18.x or 20.x)
- **Watchman**: `brew install watchman` (file watching)

**Optional Tools**:
- **Ruby Version Manager**: rbenv or rvm
- **iOS Simulator**: Xcode includes multiple iOS versions
- **Physical Device**: For hardware testing

---

## Patterns

### Pattern 1: Expo Managed Setup

```bash
# Create new Expo project
npx create-expo-app@latest MyApp --template blank-typescript
cd MyApp

# Install dependencies
npm install

# Start development server
npx expo start

# Run on iOS simulator
npx expo start --ios

# Install additional Expo packages
npx expo install expo-camera expo-location
```

**When to use**:
- Building simple to moderate complexity apps
- Need OTA updates
- Don't require custom native modules
- Rapid prototyping phase
- Team without iOS development experience

### Pattern 2: React Native CLI Setup

```bash
# Create new React Native project
npx react-native@latest init MyApp --template react-native-template-typescript
cd MyApp

# Install iOS dependencies
cd ios && pod install && cd ..

# Start Metro bundler
npm start

# Run on iOS simulator (separate terminal)
npm run ios

# Run on specific simulator
npm run ios -- --simulator="iPhone 15 Pro"
```

**When to use**:
- Need custom native modules
- Existing native iOS code to integrate
- Full control over native build process
- Complex native functionality requirements
- Performance-critical applications

### Pattern 3: Expo Bare Workflow Setup

```bash
# Create Expo bare workflow project
npx create-expo-app@latest MyApp --template bare-minimum
cd MyApp

# Install dependencies and pods
npm install
cd ios && pod install && cd ..

# Prebuild native projects
npx expo prebuild --clean

# Run on iOS
npx expo run:ios

# Install Expo modules
npx expo install expo-camera expo-notifications
```

**Benefits**:
- Best of both worlds (Expo + native access)
- Use Expo libraries with custom native code
- EAS Build integration
- Easier native module integration than pure RN CLI

### Pattern 4: TypeScript Configuration

```json
// tsconfig.json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "lib": ["ES2022"],
    "jsx": "react-native",
    "moduleResolution": "node",
    "allowSyntheticDefaultImports": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": {
      "@components/*": ["src/components/*"],
      "@screens/*": ["src/screens/*"],
      "@utils/*": ["src/utils/*"],
      "@types/*": ["src/types/*"]
    }
  },
  "include": ["**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules", "ios", "android"]
}
```

**Benefits**:
- Type safety for React Native APIs
- Better IDE support and autocomplete
- Catch errors at compile time
- Path aliases for cleaner imports

### Pattern 5: Metro Configuration

```javascript
// metro.config.js
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Add custom asset extensions
config.resolver.assetExts.push('db', 'json', 'txt');

// Add custom source extensions
config.resolver.sourceExts.push('jsx', 'js', 'ts', 'tsx', 'cjs', 'mjs');

// Platform-specific extensions order
config.resolver.platforms = ['ios', 'android', 'native'];

// Watchman configuration
config.watchFolders = [__dirname];

// Transformer configuration for SVG
config.transformer.babelTransformerPath = require.resolve('react-native-svg-transformer');
config.resolver.assetExts = config.resolver.assetExts.filter((ext) => ext !== 'svg');
config.resolver.sourceExts.push('svg');

module.exports = config;
```

**When to use**:
- Custom asset types (SVG, fonts, etc.)
- Monorepo setup with multiple packages
- Custom module resolution
- Performance optimization (caching)

### Pattern 6: Package.json Scripts

```json
{
  "name": "MyApp",
  "version": "1.0.0",
  "scripts": {
    "start": "expo start",
    "ios": "expo start --ios",
    "android": "expo start --android",
    "web": "expo start --web",
    "lint": "eslint . --ext .js,.jsx,.ts,.tsx",
    "lint:fix": "eslint . --ext .js,.jsx,.ts,.tsx --fix",
    "type-check": "tsc --noEmit",
    "test": "jest",
    "test:watch": "jest --watch",
    "clean": "rm -rf node_modules ios/Pods ios/build android/build",  # Cleans build artifacts only - safe to run
    "clean:metro": "rm -rf $TMPDIR/metro-* $TMPDIR/haste-*",  # Cleans Metro bundler cache - safe to run
    "pod-install": "cd ios && pod install && cd ..",
    "prebuild": "expo prebuild --clean",
    "build:ios": "eas build --platform ios"
  },
  "dependencies": {
    "expo": "~50.0.0",
    "react": "18.2.0",
    "react-native": "0.73.0"
  },
  "devDependencies": {
    "@babel/core": "^7.23.0",
    "@types/react": "~18.2.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "eslint": "^8.50.0",
    "eslint-config-expo": "^7.0.0",
    "typescript": "^5.2.0"
  }
}
```

**Benefits**:
- Standardized commands across team
- Easy cleanup and rebuilding
- Integrated linting and type checking
- iOS-specific build shortcuts

### Pattern 7: Environment Setup Verification

```bash
#!/bin/bash
# check-setup.sh - Verify React Native environment

echo "Checking React Native iOS setup..."

# Node.js version
echo -n "Node.js: "
node --version

# npm version
echo -n "npm: "
npm --version

# Watchman
echo -n "Watchman: "
watchman --version 2>/dev/null || echo "Not installed"

# CocoaPods
echo -n "CocoaPods: "
pod --version 2>/dev/null || echo "Not installed"

# Xcode
echo -n "Xcode: "
xcodebuild -version | head -n1

# Command Line Tools
echo -n "Command Line Tools: "
xcode-select -p

# iOS Simulators
echo "Available iOS Simulators:"
xcrun simctl list devices available | grep iPhone

# Ruby version
echo -n "Ruby: "
ruby --version

echo "Setup check complete!"
```

**When to use**:
- Onboarding new developers
- Troubleshooting setup issues
- CI/CD environment validation
- Before major version upgrades

---

## Quick Reference

### Common Commands

```
Command                              | Purpose                        | When to Use
-------------------------------------|--------------------------------|------------------
npx create-expo-app MyApp            | Create Expo project            | New Expo app
npx react-native init MyApp          | Create RN CLI project          | New bare workflow
cd ios && pod install                | Install iOS dependencies       | After adding packages
npx expo start --ios                 | Run Expo on iOS                | Development
npm run ios                          | Run RN CLI on iOS              | Development
npm run clean:metro                  | Clear Metro cache              | Bundler issues
npx expo prebuild --clean            | Regenerate native folders      | Config changes
xcodebuild clean                     | Clean Xcode build              | Build issues
xcrun simctl list devices            | List iOS simulators            | Check available devices
```

### Troubleshooting Guide

```
✅ DO: Keep Node.js on LTS version (18.x or 20.x)
✅ DO: Run pod install after every package addition
✅ DO: Clear Metro cache when seeing stale code
✅ DO: Use Watchman to improve file watching performance
✅ DO: Keep Xcode and Command Line Tools updated

❌ DON'T: Mix package managers (npm/yarn/pnpm)
❌ DON'T: Skip pod install after dependency changes
❌ DON'T: Use outdated Node.js versions
❌ DON'T: Ignore Xcode update prompts
❌ DON'T: Commit ios/Pods directory to git
```

### Node Version Requirements

```
React Native Version | Node.js Version    | Notes
---------------------|--------------------|-----------------------
0.73.x               | 18.x LTS           | Latest stable
0.72.x               | 16.x - 18.x        | Expo SDK 49
0.71.x               | 16.x - 18.x        | Expo SDK 48
0.70.x               | 14.x - 18.x        | Legacy support
```

---

## Anti-Patterns

❌ **Using wrong Node.js version**: Breaks native modules and build tools
✅ Use nvm or fnm to manage Node versions, stick to LTS releases

❌ **Skipping pod install**: Leads to missing native dependencies and runtime crashes
✅ Run `cd ios && pod install` after every package addition or removal

❌ **Committing Pods directory**: Bloats repository with thousands of files
✅ Add `ios/Pods/` to .gitignore, commit Podfile.lock instead

❌ **Mixing Expo and bare workflow randomly**: Confusion and broken builds
✅ Choose workflow upfront, migrate deliberately with `expo prebuild`

❌ **Ignoring Metro cache issues**: Stale bundler state causes mysterious bugs
✅ Clear cache with `npm run clean:metro` or `rm -rf $TMPDIR/metro-*`  (safe - cleans Metro cache)

❌ **Not using Watchman on macOS**: Slow file watching and reload issues
✅ Install Watchman with Homebrew: `brew install watchman`

❌ **Running npm install in ios/ folder**: Breaks CocoaPods dependency resolution
✅ Only run npm install at project root, use pod install for iOS dependencies

❌ **Using deprecated react-native-cli globally**: Old CLI causes compatibility issues
✅ Use npx with latest version: `npx react-native@latest init MyApp`

---

## Related Skills

- `react-native-navigation.md` - Multi-screen navigation and routing
- `react-native-native-modules.md` - Bridging to native iOS code
- `react-native-performance.md` - Optimization and profiling
- `swiftui-architecture.md` - Understanding iOS app structure
- `swift-concurrency.md` - Native async patterns for bridging
- `ios-testing.md` - Testing React Native apps on iOS

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
