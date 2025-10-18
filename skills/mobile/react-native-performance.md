---
name: mobile-react-native-performance
description: App animations are dropping frames (not 60fps)
---



# React Native Performance

**Scope**: React Native performance optimization, iOS-specific optimizations, profiling, memory management
**Lines**: ~360
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- App animations are dropping frames (not 60fps)
- Experiencing slow list scrolling or lag
- High memory usage or crashes on iOS devices
- Optimizing app for production release
- JavaScript thread blocking or main thread blocking
- Large bundle size impacting app startup time
- Profiling and identifying performance bottlenecks

## Core Concepts

### React Native Architecture

**Thread Model**:
- **JavaScript Thread**: Runs React code, business logic
- **Main (UI) Thread**: Native iOS UI rendering
- **Shadow Thread**: Layout calculations (Yoga)
- **Bridge**: Serializes data between JS and native (batched async)

**New Architecture (Fabric + TurboModules)**:
- Direct JSI (JavaScript Interface) communication
- Synchronous native calls possible
- Faster bridge, reduced overhead
- Incremental adoption available

### Performance Bottlenecks

**Common Issues**:
- Bridge congestion (too many messages)
- Excessive re-renders in React components
- Heavy JavaScript computations blocking thread
- Large lists without virtualization
- Unoptimized images and assets
- Memory leaks from listeners and timers

**iOS-Specific**:
- UIKit bridging overhead
- CoreGraphics rendering costs
- Allocation pressure (ARC overhead)
- Disk I/O on main thread

### Hermes JavaScript Engine

**Benefits**:
- Ahead-of-time compilation (faster startup)
- Reduced memory footprint
- Optimized bytecode
- Better garbage collection

**Trade-offs**:
- No JIT (slightly slower runtime in some cases)
- Default in React Native 0.70+
- iOS 64-bit only

---

## Patterns

### Pattern 1: FlatList Optimization

```typescript
import React, { useCallback } from 'react';
import { FlatList, View, Text, StyleSheet } from 'react-native';

interface Item {
  id: string;
  title: string;
  description: string;
}

// Memoized item component
const ListItem = React.memo<{ item: Item }>(({ item }) => {
  return (
    <View style={styles.item}>
      <Text style={styles.title}>{item.title}</Text>
      <Text style={styles.description}>{item.description}</Text>
    </View>
  );
});

function OptimizedList({ data }: { data: Item[] }) {
  // Memoize key extractor
  const keyExtractor = useCallback((item: Item) => item.id, []);

  // Memoize render item
  const renderItem = useCallback(
    ({ item }: { item: Item }) => <ListItem item={item} />,
    []
  );

  return (
    <FlatList
      data={data}
      renderItem={renderItem}
      keyExtractor={keyExtractor}

      // Performance optimizations
      removeClippedSubviews={true} // Unmount offscreen items
      maxToRenderPerBatch={10} // Items per render batch
      updateCellsBatchingPeriod={50} // ms between batches
      initialNumToRender={10} // Initial render count
      windowSize={5} // Viewports to render (3 = current + 1 above + 1 below)

      // iOS-specific optimizations
      maintainVisibleContentPosition={{
        minIndexForVisible: 0,
        autoscrollToTopThreshold: 10,
      }}

      // Prevent re-renders
      getItemLayout={(data, index) => ({
        length: 80, // Fixed item height
        offset: 80 * index,
        index,
      })}
    />
  );
}

const styles = StyleSheet.create({
  item: { height: 80, padding: 16 },
  title: { fontSize: 16, fontWeight: 'bold' },
  description: { fontSize: 14, color: '#666' },
});
```

**Benefits**:
- 60fps scrolling on large lists
- Reduced memory usage
- Efficient re-renders
- iOS-optimized viewport handling

### Pattern 2: React.memo and useMemo

```typescript
import React, { useMemo, useCallback, useState } from 'react';
import { View, Text, Pressable } from 'react-native';

// Expensive computation
function expensiveCalculation(items: number[]): number {
  console.log('Running expensive calculation...');
  return items.reduce((sum, item) => sum + item, 0);
}

// Memoized child component
interface ChildProps {
  count: number;
  onIncrement: () => void;
}

const ChildComponent = React.memo<ChildProps>(({ count, onIncrement }) => {
  console.log('ChildComponent render');
  return (
    <View>
      <Text>Count: {count}</Text>
      <Pressable onPress={onIncrement}>
        <Text>Increment</Text>
      </Pressable>
    </View>
  );
});

function ParentComponent() {
  const [count, setCount] = useState(0);
  const [items] = useState([1, 2, 3, 4, 5]);

  // Memoize expensive computation
  const total = useMemo(() => expensiveCalculation(items), [items]);

  // Memoize callback to prevent child re-renders
  const handleIncrement = useCallback(() => {
    setCount((c) => c + 1);
  }, []);

  return (
    <View>
      <Text>Total: {total}</Text>
      <ChildComponent count={count} onIncrement={handleIncrement} />
    </View>
  );
}
```

**When to use**:
- Expensive computations
- Preventing unnecessary re-renders
- Child components receiving callback props
- Lists with many items

### Pattern 3: React Native Reanimated 2

```typescript
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

function AnimatedBox() {
  const offset = useSharedValue(0);
  const scale = useSharedValue(1);

  // Gesture runs on UI thread (no bridge)
  const pan = Gesture.Pan()
    .onChange((event) => {
      offset.value += event.changeX;
    })
    .onEnd(() => {
      offset.value = withSpring(0);
    });

  const tap = Gesture.Tap()
    .onBegin(() => {
      scale.value = withTiming(1.2, { duration: 100 });
    })
    .onFinalize(() => {
      scale.value = withSpring(1);
    });

  // Animated style runs on UI thread
  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: offset.value },
      { scale: scale.value },
    ],
  }));

  const composed = Gesture.Simultaneous(pan, tap);

  return (
    <GestureDetector gesture={composed}>
      <Animated.View style={[styles.box, animatedStyle]} />
    </GestureDetector>
  );
}
```

**Benefits**:
- 60fps animations (runs on UI thread)
- No bridge communication during animation
- Native iOS spring physics
- Gesture-driven animations

### Pattern 4: Image Optimization

```typescript
import React from 'react';
import { Image, Platform } from 'react-native';
import FastImage from 'react-native-fast-image';

// Use FastImage for better performance
function OptimizedImage({ uri }: { uri: string }) {
  return (
    <FastImage
      source={{
        uri,
        priority: FastImage.priority.high,
        cache: FastImage.cacheControl.immutable,
      }}
      style={{ width: 200, height: 200 }}
      resizeMode={FastImage.resizeMode.cover}
    />
  );
}

// Image size optimization
function ResponsiveImage({ baseUri }: { baseUri: string }) {
  // Use appropriate image size for device
  const scale = Platform.select({
    ios: (Image as any).getSize ? '@3x' : '@2x',
    default: '@2x',
  });

  return (
    <Image
      source={{ uri: `${baseUri}${scale}.jpg` }}
      style={{ width: 200, height: 200 }}
      resizeMode="cover"
      // Load placeholder while loading
      defaultSource={require('./placeholder.png')}
    />
  );
}

// Lazy image loading
function LazyImage({ uri }: { uri: string }) {
  const [loaded, setLoaded] = React.useState(false);

  return (
    <>
      {!loaded && <Image source={require('./placeholder.png')} />}
      <Image
        source={{ uri }}
        style={{ display: loaded ? 'flex' : 'none' }}
        onLoad={() => setLoaded(true)}
      />
    </>
  );
}
```

**When to use**:
- Multiple images on screen
- Remote image loading
- Large image files
- Image-heavy feeds

### Pattern 5: Bundle Size Optimization

```javascript
// metro.config.js
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Enable tree shaking
config.transformer.minifierConfig = {
  keep_classnames: false,
  keep_fnames: false,
  mangle: {
    keep_classnames: false,
    keep_fnames: false,
  },
  compress: {
    drop_console: true, // Remove console.log in production
    dead_code: true,
    collapse_vars: true,
    reduce_vars: true,
  },
};

// Enable inlining for smaller bundle
config.transformer.experimentalImportSupport = true;
config.transformer.inlineRequires = true;

module.exports = config;
```

```typescript
// Dynamic imports for code splitting
import React, { lazy, Suspense } from 'react';

// Lazy load heavy screens
const ProfileScreen = lazy(() => import('./screens/ProfileScreen'));
const SettingsScreen = lazy(() => import('./screens/SettingsScreen'));

function App() {
  return (
    <Suspense fallback={<LoadingScreen />}>
      <ProfileScreen />
    </Suspense>
  );
}
```

**Benefits**:
- Smaller app bundle
- Faster app startup
- Reduced memory footprint
- On-demand feature loading

### Pattern 6: Memory Leak Prevention

```typescript
import React, { useEffect, useRef } from 'react';
import { NativeEventEmitter, NativeModules, AppState } from 'react-native';

function MemorySafeComponent() {
  const isMounted = useRef(true);

  useEffect(() => {
    // Cleanup flag
    return () => {
      isMounted.current = false;
    };
  }, []);

  useEffect(() => {
    // Timer cleanup
    const timer = setTimeout(() => {
      if (isMounted.current) {
        console.log('Timer fired');
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    // Event listener cleanup
    const eventEmitter = new NativeEventEmitter(NativeModules.MyModule);
    const subscription = eventEmitter.addListener('onEvent', (data) => {
      if (isMounted.current) {
        console.log(data);
      }
    });

    return () => subscription.remove();
  }, []);

  useEffect(() => {
    // AppState listener cleanup
    const subscription = AppState.addEventListener('change', (state) => {
      console.log('App state:', state);
    });

    return () => subscription.remove();
  }, []);

  return null;
}
```

**When to use**:
- Components with timers
- Event listeners
- Network requests
- Background tasks

### Pattern 7: iOS Performance Profiling

```typescript
// Using Performance API
import { Performance } from 'react-native-performance';

const perf = new Performance();

// Measure component render time
function MeasuredComponent() {
  useEffect(() => {
    perf.mark('component-mount');
    return () => {
      perf.mark('component-unmount');
      perf.measure('component-lifetime', 'component-mount', 'component-unmount');
    };
  }, []);

  return <View />;
}

// Measure async operations
async function fetchData() {
  perf.mark('fetch-start');
  const data = await fetch('https://api.example.com/data');
  perf.mark('fetch-end');
  perf.measure('fetch-duration', 'fetch-start', 'fetch-end');

  const measures = perf.getEntriesByType('measure');
  console.log('Fetch took:', measures[0].duration, 'ms');
}
```

```bash
# iOS profiling with Xcode Instruments
# 1. Run app in release mode
npm run ios --configuration Release

# 2. Open Xcode → Product → Profile
# 3. Choose Instruments template:
#    - Time Profiler (CPU usage)
#    - Allocations (memory usage)
#    - Leaks (memory leaks)
#    - Core Animation (FPS, rendering)

# 3. Analyze performance bottlenecks
```

**When to use**:
- Production optimization
- Identifying slow operations
- Memory leak detection
- Frame rate analysis

### Pattern 8: Bridge Optimization

```typescript
// ❌ Bad: Too many bridge calls
function BadComponent({ items }: { items: string[] }) {
  return (
    <View>
      {items.map((item) => (
        <NativeModule.processItem key={item} item={item} />
      ))}
    </View>
  );
}

// ✅ Good: Batch bridge calls
function GoodComponent({ items }: { items: string[] }) {
  useEffect(() => {
    // Process all items in one native call
    NativeModule.processItems(items);
  }, [items]);

  return <View>{/* render results */}</View>;
}

// ❌ Bad: Frequent state updates across bridge
const [data, setData] = useState([]);
setInterval(() => {
  NativeModule.getData().then(setData); // Bridge call every interval
}, 100);

// ✅ Good: Use event emitter for frequent updates
useEffect(() => {
  const subscription = NativeModule.subscribeToData((data) => {
    setData(data); // Native pushes updates
  });

  return () => subscription.remove();
}, []);
```

**Benefits**:
- Reduced bridge congestion
- Better batching of operations
- Lower overhead per operation
- Improved responsiveness

---

## Quick Reference

### Performance Checklist

```
✅ DO: Use FlatList/SectionList for long lists
✅ DO: Memoize expensive computations (useMemo)
✅ DO: Memoize callbacks (useCallback)
✅ DO: Use React.memo for pure components
✅ DO: Enable Hermes engine
✅ DO: Use Reanimated 2 for animations
✅ DO: Optimize images (FastImage, lazy loading)
✅ DO: Clean up timers and listeners
✅ DO: Profile with Xcode Instruments
✅ DO: Remove console.log in production

❌ DON'T: Render huge lists without virtualization
❌ DON'T: Use inline functions in render
❌ DON'T: Animate with setState (use Reanimated)
❌ DON'T: Store large objects in state
❌ DON'T: Make frequent bridge calls
❌ DON'T: Block main thread with heavy operations
❌ DON'T: Forget to clean up subscriptions
❌ DON'T: Use development mode for benchmarking
```

### FlatList Props for Performance

```
Prop                           | Value          | Effect
-------------------------------|----------------|------------------
removeClippedSubviews          | true           | Unmount offscreen
maxToRenderPerBatch            | 10             | Items per batch
updateCellsBatchingPeriod      | 50             | ms between batches
initialNumToRender             | 10             | Initial items
windowSize                     | 5              | Viewport multiplier
getItemLayout                  | Function       | Skip measurement
```

### Profiling Commands

```bash
# iOS release build
npm run ios --configuration Release

# Bundle analyzer
npx react-native-bundle-visualizer

# Performance monitor (dev)
# Shake device → Show Performance Monitor

# Xcode Instruments
# Product → Profile → Choose Instrument

# Flipper profiling
# React DevTools → Profiler
```

---

## Anti-Patterns

❌ **Animating with setState**: Causes bridge congestion and dropped frames
✅ Use Reanimated 2 for animations running on UI thread

❌ **Inline functions in FlatList renderItem**: Creates new functions every render
✅ Use useCallback to memoize render functions

❌ **Loading all data at once**: Memory issues with large datasets
✅ Use pagination, infinite scroll, or virtualized lists

❌ **Not cleaning up listeners**: Memory leaks and performance degradation
✅ Return cleanup functions from useEffect hooks

❌ **console.log in production**: Significant performance overhead
✅ Remove or use __DEV__ check, strip in Metro config

❌ **Synchronous bridge calls**: Blocks JavaScript thread
✅ Use async/await with promises, batch operations

❌ **Large bundle with no code splitting**: Slow startup time
✅ Use dynamic imports and lazy loading for heavy features

❌ **Profiling in development mode**: Misleading results (dev warnings, no optimization)
✅ Always profile in release mode with production builds

---

## Related Skills

- `react-native-setup.md` - Hermes configuration and optimization
- `react-native-navigation.md` - Navigation performance patterns
- `react-native-native-modules.md` - Optimizing bridge communication
- `frontend-performance.md` - General React optimization techniques
- `ios-testing.md` - Performance testing on iOS
- `swiftui-architecture.md` - Understanding iOS rendering pipeline

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
