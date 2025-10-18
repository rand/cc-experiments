---
name: mobile-react-native-navigation
description: Implementing multi-screen navigation in React Native apps
---



# React Native Navigation

**Scope**: React Navigation library, stack/tab/drawer navigation, deep linking, iOS-specific patterns
**Lines**: ~340
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Implementing multi-screen navigation in React Native apps
- Setting up navigation patterns (stack, tabs, drawers)
- Handling deep linking and URL schemes
- Creating iOS-native navigation feel and gestures
- Managing navigation state and params
- Implementing authentication flows with navigation
- Optimizing navigation performance and transitions

## Core Concepts

### React Navigation Architecture

**Navigator Types**:
- **Stack Navigator**: Push/pop navigation (like iOS UINavigationController)
- **Tab Navigator**: Bottom tabs (like iOS UITabBarController)
- **Drawer Navigator**: Side menu navigation
- **Native Stack**: iOS native navigation components (better performance)

**Navigation Container**:
- Top-level wrapper for all navigators
- Manages navigation state
- Handles deep linking configuration
- Provides navigation ref for programmatic navigation

### iOS Navigation Conventions

**Platform Patterns**:
- Stack navigation with header and back button
- Bottom tabs for primary navigation
- Modals for secondary actions
- Swipe gestures for back navigation
- Large titles in navigation bar (iOS 11+)

**Gesture Handling**:
- Edge swipe to go back
- Pan gesture for interactive dismissal
- Pull-to-dismiss for modals
- Native feel and spring animations

### Navigation State Management

**Navigation Params**:
- Pass data between screens
- Type-safe with TypeScript
- Shallow merge on navigate
- Deep linking parameter extraction

**Navigation Lifecycle**:
- Focus/blur events
- Screen mount/unmount
- Route state persistence
- Back button handling

---

## Patterns

### Pattern 1: Type-Safe Navigation Setup

```typescript
// types/navigation.ts
import { NavigationProp, RouteProp } from '@react-navigation/native';

// Define root stack param list
export type RootStackParamList = {
  Home: undefined;
  Profile: { userId: string };
  Settings: undefined;
  Post: { postId: string; title?: string };
};

// Define tab param list
export type TabParamList = {
  Feed: undefined;
  Search: undefined;
  Notifications: undefined;
  Profile: undefined;
};

// Helper types for screen props
export type RootStackNavigation = NavigationProp<RootStackParamList>;
export type ProfileRouteProp = RouteProp<RootStackParamList, 'Profile'>;

// Declare global navigation type
declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
```

**Benefits**:
- Full TypeScript autocomplete
- Compile-time route validation
- Type-safe params
- IntelliSense for navigation methods

### Pattern 2: Native Stack Navigator (iOS)

```typescript
// App.tsx
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { RootStackParamList } from './types/navigation';

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerLargeTitle: true, // iOS large titles
          headerTransparent: false,
          headerBlurEffect: 'regular', // iOS blur
          animation: 'default', // Native iOS animations
          gestureEnabled: true, // Swipe back gesture
          fullScreenGestureEnabled: true,
        }}
      >
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={{ title: 'Home' }}
        />
        <Stack.Screen
          name="Profile"
          component={ProfileScreen}
          options={({ route }) => ({
            title: `User ${route.params.userId}`,
            headerBackTitle: 'Back', // iOS custom back text
          })}
        />
        <Stack.Screen
          name="Settings"
          component={SettingsScreen}
          options={{
            presentation: 'modal', // iOS modal presentation
            headerLargeTitle: false,
          }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

**When to use**:
- iOS-first or iOS-only apps
- Need native navigation performance
- Want platform-specific animations
- Require native header blur effects

### Pattern 3: Bottom Tab Navigation

```typescript
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

const Tab = createBottomTabNavigator<TabParamList>();

function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          const icons: Record<string, string> = {
            Feed: focused ? 'home' : 'home-outline',
            Search: focused ? 'search' : 'search-outline',
            Notifications: focused ? 'notifications' : 'notifications-outline',
            Profile: focused ? 'person' : 'person-outline',
          };
          return <Ionicons name={icons[route.name]} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#007AFF', // iOS blue
        tabBarInactiveTintColor: '#8E8E93', // iOS gray
        tabBarStyle: {
          backgroundColor: '#F2F2F7', // iOS tab bar background
          borderTopWidth: 0,
          elevation: 0,
        },
        headerShown: false, // Headers in nested stacks
      })}
    >
      <Tab.Screen name="Feed" component={FeedStack} />
      <Tab.Screen name="Search" component={SearchStack} />
      <Tab.Screen
        name="Notifications"
        component={NotificationsStack}
        options={{
          tabBarBadge: 3, // iOS badge
        }}
      />
      <Tab.Screen name="Profile" component={ProfileStack} />
    </Tab.Navigator>
  );
}
```

**Benefits**:
- iOS-native tab bar appearance
- Icon state management
- Badge support
- Nested stack navigators per tab

### Pattern 4: Screen Component with Navigation

```typescript
import { useNavigation, useRoute } from '@react-navigation/native';
import { RootStackNavigation, ProfileRouteProp } from '../types/navigation';

function ProfileScreen() {
  const navigation = useNavigation<RootStackNavigation>();
  const route = useRoute<ProfileRouteProp>();
  const { userId } = route.params;

  const handleEditProfile = () => {
    navigation.navigate('Settings');
  };

  const handleGoBack = () => {
    navigation.goBack();
  };

  const handleViewPost = (postId: string) => {
    navigation.navigate('Post', { postId, title: 'My Post' });
  };

  return (
    <View>
      <Text>Profile: {userId}</Text>
      <Button title="Edit Profile" onPress={handleEditProfile} />
      <Button title="Go Back" onPress={handleGoBack} />
    </View>
  );
}
```

**When to use**:
- Accessing navigation in functional components
- Type-safe navigation and params
- Programmatic navigation
- Extracting route parameters

### Pattern 5: Deep Linking Configuration

```typescript
import { LinkingOptions } from '@react-navigation/native';
import * as Linking from 'expo-linking';

const linking: LinkingOptions<RootStackParamList> = {
  prefixes: [
    'myapp://', // Custom URL scheme
    'https://myapp.com', // Universal links
  ],
  config: {
    screens: {
      Home: '',
      Profile: 'user/:userId',
      Post: {
        path: 'post/:postId',
        parse: {
          postId: (id) => id, // Custom parsing
        },
      },
      Settings: 'settings',
    },
  },
  async getInitialURL() {
    // Check if app was opened from deep link
    const url = await Linking.getInitialURL();
    if (url != null) {
      return url;
    }
    // Handle push notifications
    // const notification = await getInitialNotification();
    // return notification?.data?.url;
  },
  subscribe(listener) {
    // Listen for deep links while app is running
    const subscription = Linking.addEventListener('url', ({ url }) => {
      listener(url);
    });

    return () => subscription.remove();
  },
};

// In NavigationContainer
<NavigationContainer linking={linking}>
  {/* navigators */}
</NavigationContainer>
```

**Benefits**:
- Universal links support
- Custom URL scheme handling
- Push notification navigation
- Type-safe route parsing

### Pattern 6: Authentication Flow

```typescript
import { createNativeStackNavigator } from '@react-native-stack-navigator';

type AuthStackParamList = {
  Login: undefined;
  SignUp: undefined;
  ForgotPassword: undefined;
};

type AppStackParamList = {
  Main: undefined;
  Profile: { userId: string };
};

const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const AppStack = createNativeStackNavigator<AppStackParamList>();

function AuthNavigator() {
  return (
    <AuthStack.Navigator
      screenOptions={{
        headerShown: false,
        presentation: 'modal',
      }}
    >
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="SignUp" component={SignUpScreen} />
      <AuthStack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
    </AuthStack.Navigator>
  );
}

function AppNavigator() {
  return (
    <AppStack.Navigator>
      <AppStack.Screen name="Main" component={TabNavigator} />
      <AppStack.Screen name="Profile" component={ProfileScreen} />
    </AppStack.Navigator>
  );
}

// Root navigator with auth state
export default function RootNavigator() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <SplashScreen />;
  }

  return (
    <NavigationContainer>
      {isAuthenticated ? <AppNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
}
```

**When to use**:
- Apps with login requirements
- Conditional navigation based on auth state
- Separate navigation stacks for auth/app
- Preventing back navigation to auth screens

### Pattern 7: Modal Navigation

```typescript
function RootNavigator() {
  return (
    <Stack.Navigator>
      {/* Main app screens */}
      <Stack.Screen name="Home" component={HomeScreen} />
      <Stack.Screen name="Profile" component={ProfileScreen} />

      {/* Modal screens group */}
      <Stack.Group
        screenOptions={{
          presentation: 'modal',
          headerShown: true,
          headerLeft: () => (
            <Button title="Close" onPress={() => navigation.goBack()} />
          ),
        }}
      >
        <Stack.Screen name="CreatePost" component={CreatePostScreen} />
        <Stack.Screen name="ShareSheet" component={ShareSheetScreen} />
      </Stack.Group>

      {/* Full screen modal */}
      <Stack.Screen
        name="ImageViewer"
        component={ImageViewerScreen}
        options={{
          presentation: 'fullScreenModal',
          headerShown: false,
          animation: 'fade',
        }}
      />
    </Stack.Navigator>
  );
}
```

**Benefits**:
- iOS-native modal presentation
- Grouped modal configuration
- Custom dismiss gestures
- Full screen takeover for media

### Pattern 8: Navigation Options with Header Buttons

```typescript
function PostScreen() {
  const navigation = useNavigation();

  React.useLayoutEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <Button
          title="Share"
          onPress={() => navigation.navigate('ShareSheet')}
        />
      ),
      headerBackTitle: 'Posts', // iOS custom back text
      headerLargeTitle: false,
      headerTransparent: false,
    });
  }, [navigation]);

  return <View>{/* content */}</View>;
}

// Or in navigator options
<Stack.Screen
  name="Post"
  component={PostScreen}
  options={({ navigation, route }) => ({
    title: route.params.title ?? 'Post',
    headerRight: () => (
      <Pressable onPress={() => console.log('Share')}>
        <Ionicons name="share-outline" size={24} color="#007AFF" />
      </Pressable>
    ),
  })}
/>
```

**When to use**:
- Dynamic header buttons
- Screen-specific header actions
- iOS-style navigation bar customization
- Context-aware header updates

---

## Quick Reference

### Navigation Methods

```
Method                                    | Purpose                          | Example
------------------------------------------|----------------------------------|------------------
navigation.navigate('Screen', params)     | Navigate to screen               | Navigate with params
navigation.push('Screen', params)         | Push new instance on stack       | Allow duplicates
navigation.goBack()                       | Go back one screen               | Dismiss/pop
navigation.pop()                          | Pop from stack                   | Same as goBack
navigation.popToTop()                     | Pop to first screen in stack     | Reset stack
navigation.replace('Screen', params)      | Replace current screen           | Auth flow
navigation.reset({ routes: [...] })       | Reset entire navigation state    | Deep state change
```

### Screen Options (iOS)

```typescript
{
  // Header
  headerShown: true,
  headerTitle: 'Title',
  headerLargeTitle: true,
  headerTransparent: false,
  headerBlurEffect: 'regular',
  headerBackTitle: 'Back',

  // Presentation
  presentation: 'card' | 'modal' | 'fullScreenModal',
  animation: 'default' | 'fade' | 'slide_from_bottom',

  // Gestures
  gestureEnabled: true,
  fullScreenGestureEnabled: true,
  gestureDirection: 'horizontal' | 'vertical',

  // Status bar
  statusBarStyle: 'auto' | 'dark' | 'light',
  statusBarAnimation: 'fade' | 'slide',
}
```

### Best Practices

```
✅ DO: Use TypeScript for type-safe navigation
✅ DO: Use native stack for iOS-specific apps
✅ DO: Configure deep linking for all screens
✅ DO: Keep navigation state shallow (avoid deep nesting)
✅ DO: Use modals for temporary actions

❌ DON'T: Nest more than 2-3 levels of navigators
❌ DON'T: Pass large objects in route params
❌ DON'T: Ignore deep linking configuration
❌ DON'T: Use stack navigator for everything (tabs exist)
❌ DON'T: Store navigation state in React state
```

---

## Anti-Patterns

❌ **Deep navigator nesting**: Stack → Tabs → Stack → Stack (4+ levels)
✅ Keep nesting to 2-3 levels max, use modal presentation for edge cases

❌ **Passing functions in params**: `navigation.navigate('Screen', { onSave: () => {} })`
✅ Use navigation events or state management (Context, Redux)

❌ **Prop drilling navigation**: Passing navigation prop through many components
✅ Use `useNavigation()` hook in any component

❌ **Ignoring TypeScript types**: Using `any` for navigation
✅ Define and use typed param lists for all navigators

❌ **Not handling deep links**: App doesn't respond to URLs
✅ Configure linking for all screens, test with URL schemes

❌ **Storing navigation reference globally**: `let navRef; navRef = navigation;`
✅ Use `navigationRef` from `@react-navigation/native` with TypeScript

❌ **Rebuilding entire navigation on state change**: Auth state toggles navigator
✅ Use conditional rendering at root level, not deep in tree

❌ **Not using native stack on iOS**: Using regular stack for iOS-only apps
✅ Use `@react-navigation/native-stack` for better performance and native feel

---

## Related Skills

- `react-native-setup.md` - Project initialization and dependencies
- `react-native-performance.md` - Navigation performance optimization
- `react-native-native-modules.md` - Custom native navigation components
- `swiftui-navigation.md` - iOS native navigation patterns
- `react-component-patterns.md` - Component composition with navigation
- `frontend-state-management.md` - Managing app state with navigation

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
