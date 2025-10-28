/**
 * React Feature Flag Hooks
 *
 * Production-ready React hooks for feature flags with TypeScript support.
 * Includes hooks for boolean flags, variations, A/B tests, and experiments.
 */

import { useState, useEffect, useContext, createContext, useCallback, useMemo } from 'react';

// Types
interface FeatureFlagContext {
  user_id: string;
  email?: string;
  plan?: string;
  attributes?: Record<string, any>;
}

interface FlagVariation {
  key: string;
  value: any;
}

interface FlagClient {
  isEnabled(key: string, context: FeatureFlagContext, defaultValue: boolean): boolean;
  getVariation(key: string, context: FeatureFlagContext, defaultValue: any): any;
  track(event: string, context: FeatureFlagContext, data?: any): void;
}

// Mock client implementation (replace with actual SDK)
class MockFlagClient implements FlagClient {
  private flags: Map<string, any> = new Map();

  isEnabled(key: string, context: FeatureFlagContext, defaultValue: boolean): boolean {
    return this.flags.get(key) ?? defaultValue;
  }

  getVariation(key: string, context: FeatureFlagContext, defaultValue: any): any {
    return this.flags.get(key) ?? defaultValue;
  }

  track(event: string, context: FeatureFlagContext, data?: any): void {
    console.log('Track event:', event, context, data);
  }

  setFlag(key: string, value: any): void {
    this.flags.set(key, value);
  }
}

// Context
const FlagClientContext = createContext<FlagClient | null>(null);
const FlagUserContext = createContext<FeatureFlagContext | null>(null);

// Provider Component
interface FlagProviderProps {
  client: FlagClient;
  user: FeatureFlagContext;
  children: React.ReactNode;
}

export const FlagProvider: React.FC<FlagProviderProps> = ({ client, user, children }) => {
  return (
    <FlagClientContext.Provider value={client}>
      <FlagUserContext.Provider value={user}>
        {children}
      </FlagUserContext.Provider>
    </FlagClientContext.Provider>
  );
};

// Hook: useFeatureFlag (Boolean)
export function useFeatureFlag(
  flagKey: string,
  defaultValue: boolean = false
): boolean {
  const client = useContext(FlagClientContext);
  const user = useContext(FlagUserContext);

  if (!client || !user) {
    throw new Error('useFeatureFlag must be used within FlagProvider');
  }

  const [enabled, setEnabled] = useState<boolean>(() =>
    client.isEnabled(flagKey, user, defaultValue)
  );

  useEffect(() => {
    // Re-evaluate flag when user context changes
    const value = client.isEnabled(flagKey, user, defaultValue);
    setEnabled(value);
  }, [client, flagKey, user, defaultValue]);

  return enabled;
}

// Hook: useFeatureVariation (Multi-variate)
export function useFeatureVariation<T = any>(
  flagKey: string,
  defaultValue: T
): T {
  const client = useContext(FlagClientContext);
  const user = useContext(FlagUserContext);

  if (!client || !user) {
    throw new Error('useFeatureVariation must be used within FlagProvider');
  }

  const [variation, setVariation] = useState<T>(() =>
    client.getVariation(flagKey, user, defaultValue)
  );

  useEffect(() => {
    const value = client.getVariation(flagKey, user, defaultValue);
    setVariation(value);
  }, [client, flagKey, user, defaultValue]);

  return variation;
}

// Hook: useFlags (Multiple flags at once)
export function useFlags(
  flagKeys: string[],
  defaultValues: Record<string, boolean> = {}
): Record<string, boolean> {
  const client = useContext(FlagClientContext);
  const user = useContext(FlagUserContext);

  if (!client || !user) {
    throw new Error('useFlags must be used within FlagProvider');
  }

  const [flags, setFlags] = useState<Record<string, boolean>>(() => {
    const result: Record<string, boolean> = {};
    flagKeys.forEach(key => {
      result[key] = client.isEnabled(key, user, defaultValues[key] ?? false);
    });
    return result;
  });

  useEffect(() => {
    const result: Record<string, boolean> = {};
    flagKeys.forEach(key => {
      result[key] = client.isEnabled(key, user, defaultValues[key] ?? false);
    });
    setFlags(result);
  }, [client, flagKeys, user, defaultValues]);

  return flags;
}

// Hook: useExperiment (A/B Test)
interface ExperimentResult<T> {
  variation: T;
  track: (event: string, data?: any) => void;
}

export function useExperiment<T = string>(
  experimentKey: string,
  defaultVariation: T
): ExperimentResult<T> {
  const client = useContext(FlagClientContext);
  const user = useContext(FlagUserContext);

  if (!client || !user) {
    throw new Error('useExperiment must be used within FlagProvider');
  }

  const variation = useMemo(
    () => client.getVariation(experimentKey, user, defaultVariation),
    [client, experimentKey, user, defaultVariation]
  );

  // Track exposure automatically
  useEffect(() => {
    client.track(`${experimentKey}.exposure`, user, { variation });
  }, [client, experimentKey, user, variation]);

  const track = useCallback(
    (event: string, data?: any) => {
      client.track(`${experimentKey}.${event}`, user, { variation, ...data });
    },
    [client, experimentKey, user, variation]
  );

  return { variation, track };
}

// Hook: useFeatureFlagWithOverride (with local override)
export function useFeatureFlagWithOverride(
  flagKey: string,
  defaultValue: boolean = false
): [boolean, (override: boolean | null) => void] {
  const baseValue = useFeatureFlag(flagKey, defaultValue);
  const [override, setOverride] = useState<boolean | null>(null);

  const enabled = override !== null ? override : baseValue;

  return [enabled, setOverride];
}

// Component: FeatureFlag (Conditional Rendering)
interface FeatureFlagProps {
  flag: string;
  defaultValue?: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const FeatureFlag: React.FC<FeatureFlagProps> = ({
  flag,
  defaultValue = false,
  children,
  fallback = null,
}) => {
  const enabled = useFeatureFlag(flag, defaultValue);
  return <>{enabled ? children : fallback}</>;
};

// Component: FeatureVariation (Render based on variation)
interface FeatureVariationProps {
  flag: string;
  defaultValue: string;
  variations: Record<string, React.ReactNode>;
}

export const FeatureVariation: React.FC<FeatureVariationProps> = ({
  flag,
  defaultValue,
  variations,
}) => {
  const variation = useFeatureVariation(flag, defaultValue);
  return <>{variations[variation] || variations[defaultValue] || null}</>;
};

// Example Usage Components

// Example 1: Simple Feature Toggle
export const NewDashboard: React.FC = () => {
  const isEnabled = useFeatureFlag('new-dashboard', false);

  return (
    <div>
      {isEnabled ? (
        <div>New Dashboard UI</div>
      ) : (
        <div>Legacy Dashboard UI</div>
      )}
    </div>
  );
};

// Example 2: Multiple Flags
export const FeaturePanel: React.FC = () => {
  const flags = useFlags(['feature-a', 'feature-b', 'feature-c']);

  return (
    <div>
      {flags['feature-a'] && <div>Feature A</div>}
      {flags['feature-b'] && <div>Feature B</div>}
      {flags['feature-c'] && <div>Feature C</div>}
    </div>
  );
};

// Example 3: A/B Test
export const CheckoutButton: React.FC = () => {
  const { variation, track } = useExperiment<'control' | 'variant-a' | 'variant-b'>(
    'checkout-button-test',
    'control'
  );

  const handleClick = () => {
    track('button_clicked');
    // Handle checkout...
  };

  const buttonStyles = {
    control: { backgroundColor: '#0066cc', text: 'Checkout' },
    'variant-a': { backgroundColor: '#cc0000', text: 'Buy Now' },
    'variant-b': { backgroundColor: '#00cc66', text: 'Complete Purchase' },
  };

  const style = buttonStyles[variation];

  return (
    <button
      onClick={handleClick}
      style={{ backgroundColor: style.backgroundColor }}
    >
      {style.text}
    </button>
  );
};

// Example 4: Configuration Flag
interface ApiConfig {
  rate_limit: number;
  timeout_ms: number;
}

export const ApiConfigExample: React.FC = () => {
  const config = useFeatureVariation<ApiConfig>('api-config', {
    rate_limit: 100,
    timeout_ms: 5000,
  });

  return (
    <div>
      <p>Rate Limit: {config.rate_limit} req/min</p>
      <p>Timeout: {config.timeout_ms} ms</p>
    </div>
  );
};

// Example 5: Conditional Component
export const BetaFeatures: React.FC = () => {
  return (
    <FeatureFlag flag="beta-features" defaultValue={false}>
      <div>
        <h2>Beta Features</h2>
        <p>These features are experimental.</p>
      </div>
    </FeatureFlag>
  );
};

// Example 6: Variation Component
export const PricingPage: React.FC = () => {
  return (
    <FeatureVariation
      flag="pricing-layout"
      defaultValue="vertical"
      variations={{
        vertical: <VerticalPricing />,
        horizontal: <HorizontalPricing />,
        grid: <GridPricing />,
      }}
    />
  );
};

const VerticalPricing = () => <div>Vertical Layout</div>;
const HorizontalPricing = () => <div>Horizontal Layout</div>;
const GridPricing = () => <div>Grid Layout</div>;

// Example 7: Feature with Override (for testing)
export const DevModeFeature: React.FC = () => {
  const [enabled, setOverride] = useFeatureFlagWithOverride('dev-feature', false);

  return (
    <div>
      <label>
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setOverride(e.target.checked ? true : null)}
        />
        Dev Feature (Override)
      </label>
      {enabled && <div>Dev Feature Content</div>}
    </div>
  );
};

// App Setup Example
export const App: React.FC = () => {
  // Initialize client (use actual SDK in production)
  const client = useMemo(() => new MockFlagClient(), []);

  // User context (fetch from auth)
  const user: FeatureFlagContext = {
    user_id: 'user-123',
    email: 'user@example.com',
    plan: 'premium',
    attributes: {
      country: 'US',
      signup_date: '2024-01-01',
    },
  };

  return (
    <FlagProvider client={client} user={user}>
      <div>
        <NewDashboard />
        <FeaturePanel />
        <CheckoutButton />
        <BetaFeatures />
        <PricingPage />
      </div>
    </FlagProvider>
  );
};

// Utility: Flag Testing Component (for development)
export const FlagDebugger: React.FC<{ flags: string[] }> = ({ flags }) => {
  const flagValues = useFlags(flags);

  return (
    <div style={{ position: 'fixed', bottom: 0, right: 0, background: '#f0f0f0', padding: '10px' }}>
      <h4>Feature Flags</h4>
      {Object.entries(flagValues).map(([key, value]) => (
        <div key={key}>
          <code>{key}</code>: {value ? '✅' : '❌'}
        </div>
      ))}
    </div>
  );
};

export default App;
