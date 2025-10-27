import React, { useState, useRef } from 'react';

/**
 * Accessible Form Component
 *
 * Features:
 * - Proper labels associated with inputs
 * - Error messages announced to screen readers
 * - aria-invalid for fields with errors
 * - aria-describedby for hints and errors
 * - Error summary with focus management
 * - Client-side validation
 * - Required field indicators
 */

interface FormData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
  agree: boolean;
}

interface FormErrors {
  [key: string]: string | undefined;
}

export function AccessibleForm() {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    agree: false,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<{ [key: string]: boolean }>({});
  const [submitted, setSubmitted] = useState(false);
  const errorSummaryRef = useRef<HTMLDivElement>(null);

  // Validation rules
  const validate = (name: string, value: string | boolean): string | undefined => {
    switch (name) {
      case 'name':
        if (typeof value === 'string' && !value.trim()) {
          return 'Name is required';
        }
        if (typeof value === 'string' && value.trim().length < 2) {
          return 'Name must be at least 2 characters';
        }
        break;

      case 'email':
        if (typeof value === 'string' && !value.trim()) {
          return 'Email is required';
        }
        if (typeof value === 'string' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
          return 'Please enter a valid email address';
        }
        break;

      case 'password':
        if (typeof value === 'string' && !value) {
          return 'Password is required';
        }
        if (typeof value === 'string' && value.length < 8) {
          return 'Password must be at least 8 characters';
        }
        if (typeof value === 'string' && !/[A-Z]/.test(value)) {
          return 'Password must contain at least one uppercase letter';
        }
        if (typeof value === 'string' && !/[a-z]/.test(value)) {
          return 'Password must contain at least one lowercase letter';
        }
        if (typeof value === 'string' && !/[0-9]/.test(value)) {
          return 'Password must contain at least one number';
        }
        break;

      case 'confirmPassword':
        if (typeof value === 'string' && value !== formData.password) {
          return 'Passwords do not match';
        }
        break;

      case 'agree':
        if (!value) {
          return 'You must agree to the terms';
        }
        break;
    }

    return undefined;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;

    setFormData(prev => ({
      ...prev,
      [name]: newValue,
    }));

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: undefined,
      }));
    }
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    const fieldValue = type === 'checkbox' ? checked : value;

    setTouched(prev => ({
      ...prev,
      [name]: true,
    }));

    const error = validate(name, fieldValue);
    if (error) {
      setErrors(prev => ({
        ...prev,
        [name]: error,
      }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate all fields
    const newErrors: FormErrors = {};
    Object.keys(formData).forEach(key => {
      const error = validate(key, formData[key as keyof FormData]);
      if (error) {
        newErrors[key] = error;
      }
    });

    setErrors(newErrors);
    setTouched(
      Object.keys(formData).reduce((acc, key) => ({ ...acc, [key]: true }), {})
    );

    // If there are errors, focus error summary
    if (Object.keys(newErrors).length > 0) {
      setSubmitted(true);
      setTimeout(() => {
        errorSummaryRef.current?.focus();
      }, 0);
      return;
    }

    // Success
    alert('Form submitted successfully!');
    console.log('Form data:', formData);
  };

  // Get list of errors for error summary
  const errorList = Object.entries(errors)
    .filter(([, error]) => error)
    .map(([field, error]) => ({
      field,
      message: error!,
    }));

  return (
    <div style={{ maxWidth: '600px', margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Accessible Form Example</h1>

      {/* Error Summary */}
      {submitted && errorList.length > 0 && (
        <div
          ref={errorSummaryRef}
          role="alert"
          aria-labelledby="error-summary-title"
          tabIndex={-1}
          style={{
            backgroundColor: '#fff5f5',
            border: '2px solid #dc3545',
            borderRadius: '4px',
            padding: '1rem',
            marginBottom: '1.5rem',
          }}
        >
          <h2 id="error-summary-title" style={{ marginTop: 0, color: '#dc3545' }}>
            There {errorList.length === 1 ? 'is' : 'are'} {errorList.length}{' '}
            error{errorList.length === 1 ? '' : 's'} in the form
          </h2>
          <ul style={{ marginBottom: 0 }}>
            {errorList.map(({ field, message }) => (
              <li key={field}>
                <a href={`#${field}`} style={{ color: '#dc3545' }}>
                  {message}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        {/* Name Field */}
        <div style={{ marginBottom: '1.5rem' }}>
          <label
            htmlFor="name"
            style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}
          >
            Full Name <span style={{ color: '#dc3545' }} aria-label="required">*</span>
          </label>
          <input
            id="name"
            name="name"
            type="text"
            value={formData.name}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            aria-required="true"
            aria-invalid={!!(touched.name && errors.name)}
            aria-describedby={
              errors.name ? 'name-error name-hint' : 'name-hint'
            }
            autoComplete="name"
            style={{
              width: '100%',
              padding: '0.5rem',
              fontSize: '1rem',
              border: touched.name && errors.name ? '2px solid #dc3545' : '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
          <p
            id="name-hint"
            style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}
          >
            Your first and last name
          </p>
          {touched.name && errors.name && (
            <p
              id="name-error"
              role="alert"
              style={{ color: '#dc3545', fontSize: '0.875rem', marginTop: '0.25rem' }}
            >
              Error: {errors.name}
            </p>
          )}
        </div>

        {/* Email Field */}
        <div style={{ marginBottom: '1.5rem' }}>
          <label
            htmlFor="email"
            style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}
          >
            Email Address <span style={{ color: '#dc3545' }} aria-label="required">*</span>
          </label>
          <input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            aria-required="true"
            aria-invalid={!!(touched.email && errors.email)}
            aria-describedby={
              errors.email ? 'email-error email-hint' : 'email-hint'
            }
            autoComplete="email"
            style={{
              width: '100%',
              padding: '0.5rem',
              fontSize: '1rem',
              border: touched.email && errors.email ? '2px solid #dc3545' : '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
          <p
            id="email-hint"
            style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}
          >
            We'll never share your email with anyone else
          </p>
          {touched.email && errors.email && (
            <p
              id="email-error"
              role="alert"
              style={{ color: '#dc3545', fontSize: '0.875rem', marginTop: '0.25rem' }}
            >
              Error: {errors.email}
            </p>
          )}
        </div>

        {/* Password Field */}
        <div style={{ marginBottom: '1.5rem' }}>
          <label
            htmlFor="password"
            style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}
          >
            Password <span style={{ color: '#dc3545' }} aria-label="required">*</span>
          </label>
          <input
            id="password"
            name="password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            aria-required="true"
            aria-invalid={!!(touched.password && errors.password)}
            aria-describedby={
              errors.password ? 'password-error password-hint' : 'password-hint'
            }
            autoComplete="new-password"
            style={{
              width: '100%',
              padding: '0.5rem',
              fontSize: '1rem',
              border: touched.password && errors.password ? '2px solid #dc3545' : '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
          <p
            id="password-hint"
            style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}
          >
            Must be at least 8 characters with one uppercase, one lowercase, and one number
          </p>
          {touched.password && errors.password && (
            <p
              id="password-error"
              role="alert"
              style={{ color: '#dc3545', fontSize: '0.875rem', marginTop: '0.25rem' }}
            >
              Error: {errors.password}
            </p>
          )}
        </div>

        {/* Confirm Password Field */}
        <div style={{ marginBottom: '1.5rem' }}>
          <label
            htmlFor="confirmPassword"
            style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}
          >
            Confirm Password <span style={{ color: '#dc3545' }} aria-label="required">*</span>
          </label>
          <input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            value={formData.confirmPassword}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            aria-required="true"
            aria-invalid={!!(touched.confirmPassword && errors.confirmPassword)}
            aria-describedby={
              errors.confirmPassword ? 'confirmPassword-error' : undefined
            }
            autoComplete="new-password"
            style={{
              width: '100%',
              padding: '0.5rem',
              fontSize: '1rem',
              border: touched.confirmPassword && errors.confirmPassword ? '2px solid #dc3545' : '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
          {touched.confirmPassword && errors.confirmPassword && (
            <p
              id="confirmPassword-error"
              role="alert"
              style={{ color: '#dc3545', fontSize: '0.875rem', marginTop: '0.25rem' }}
            >
              Error: {errors.confirmPassword}
            </p>
          )}
        </div>

        {/* Checkbox */}
        <div style={{ marginBottom: '1.5rem' }}>
          <input
            id="agree"
            name="agree"
            type="checkbox"
            checked={formData.agree}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            aria-required="true"
            aria-invalid={!!(touched.agree && errors.agree)}
            aria-describedby={errors.agree ? 'agree-error' : undefined}
            style={{ marginRight: '0.5rem' }}
          />
          <label htmlFor="agree">
            I agree to the <a href="/terms">Terms of Service</a>{' '}
            <span style={{ color: '#dc3545' }} aria-label="required">*</span>
          </label>
          {touched.agree && errors.agree && (
            <p
              id="agree-error"
              role="alert"
              style={{ color: '#dc3545', fontSize: '0.875rem', marginTop: '0.25rem' }}
            >
              Error: {errors.agree}
            </p>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          style={{
            padding: '0.75rem 1.5rem',
            fontSize: '1rem',
            backgroundColor: '#0066cc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Create Account
        </button>
      </form>
    </div>
  );
}
