/**
 * React Hook Form Example
 *
 * Demonstrates:
 * - Basic form with validation
 * - Zod schema validation
 * - Field arrays
 * - Controlled components
 * - Custom validation
 * - Form state management
 * - Submission handling
 */

import React from 'react';
import { useForm, useFieldArray, Controller, SubmitHandler } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// ============================================================================
// Basic Form with Zod Validation
// ============================================================================

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  rememberMe: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function LoginForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  });

  const onSubmit: SubmitHandler<LoginFormData> = async (data) => {
    console.log('Submitting:', data);
    await new Promise((resolve) => setTimeout(resolve, 2000)); // Simulate API call
    alert('Login successful!');
    reset();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" {...register('email')} />
        {errors.email && <span className="error">{errors.email.message}</span>}
      </div>

      <div>
        <label htmlFor="password">Password</label>
        <input id="password" type="password" {...register('password')} />
        {errors.password && <span className="error">{errors.password.message}</span>}
      </div>

      <div>
        <label>
          <input type="checkbox" {...register('rememberMe')} />
          Remember me
        </label>
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
}

// ============================================================================
// Complex Form with Nested Fields
// ============================================================================

const userSchema = z.object({
  firstName: z.string().min(1, 'First name is required'),
  lastName: z.string().min(1, 'Last name is required'),
  email: z.string().email('Invalid email'),
  age: z.number().min(18, 'Must be at least 18').max(120, 'Invalid age'),
  address: z.object({
    street: z.string().min(1, 'Street is required'),
    city: z.string().min(1, 'City is required'),
    state: z.string().length(2, 'State must be 2 characters'),
    zipCode: z.string().regex(/^\d{5}$/, 'Zip code must be 5 digits'),
  }),
  phone: z.string().regex(/^\d{3}-\d{3}-\d{4}$/, 'Phone must be format: 555-555-5555'),
  acceptTerms: z.literal(true, {
    errorMap: () => ({ message: 'You must accept terms' }),
  }),
});

type UserFormData = z.infer<typeof userSchema>;

export function UserRegistrationForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty, isValid },
    watch,
  } = useForm<UserFormData>({
    resolver: zodResolver(userSchema),
    mode: 'onChange', // Validate on change
    defaultValues: {
      firstName: '',
      lastName: '',
      email: '',
      age: 18,
      address: {
        street: '',
        city: '',
        state: '',
        zipCode: '',
      },
      phone: '',
      acceptTerms: false,
    },
  });

  const watchAge = watch('age');

  const onSubmit: SubmitHandler<UserFormData> = async (data) => {
    console.log('User data:', data);
    // API call here
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <h2>User Registration</h2>

      <div>
        <label htmlFor="firstName">First Name</label>
        <input id="firstName" {...register('firstName')} />
        {errors.firstName && <span className="error">{errors.firstName.message}</span>}
      </div>

      <div>
        <label htmlFor="lastName">Last Name</label>
        <input id="lastName" {...register('lastName')} />
        {errors.lastName && <span className="error">{errors.lastName.message}</span>}
      </div>

      <div>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" {...register('email')} />
        {errors.email && <span className="error">{errors.email.message}</span>}
      </div>

      <div>
        <label htmlFor="age">Age: {watchAge}</label>
        <input
          id="age"
          type="number"
          {...register('age', { valueAsNumber: true })}
        />
        {errors.age && <span className="error">{errors.age.message}</span>}
      </div>

      <fieldset>
        <legend>Address</legend>

        <div>
          <label htmlFor="street">Street</label>
          <input id="street" {...register('address.street')} />
          {errors.address?.street && (
            <span className="error">{errors.address.street.message}</span>
          )}
        </div>

        <div>
          <label htmlFor="city">City</label>
          <input id="city" {...register('address.city')} />
          {errors.address?.city && (
            <span className="error">{errors.address.city.message}</span>
          )}
        </div>

        <div>
          <label htmlFor="state">State</label>
          <input id="state" maxLength={2} {...register('address.state')} />
          {errors.address?.state && (
            <span className="error">{errors.address.state.message}</span>
          )}
        </div>

        <div>
          <label htmlFor="zipCode">Zip Code</label>
          <input id="zipCode" {...register('address.zipCode')} />
          {errors.address?.zipCode && (
            <span className="error">{errors.address.zipCode.message}</span>
          )}
        </div>
      </fieldset>

      <div>
        <label htmlFor="phone">Phone</label>
        <input id="phone" placeholder="555-555-5555" {...register('phone')} />
        {errors.phone && <span className="error">{errors.phone.message}</span>}
      </div>

      <div>
        <label>
          <input type="checkbox" {...register('acceptTerms')} />
          I accept the terms and conditions
        </label>
        {errors.acceptTerms && <span className="error">{errors.acceptTerms.message}</span>}
      </div>

      <button type="submit" disabled={isSubmitting || !isDirty || !isValid}>
        {isSubmitting ? 'Submitting...' : 'Register'}
      </button>
    </form>
  );
}

// ============================================================================
// Field Arrays (Dynamic Forms)
// ============================================================================

const todoSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  todos: z
    .array(
      z.object({
        text: z.string().min(1, 'Todo text is required'),
        priority: z.enum(['low', 'medium', 'high']),
      })
    )
    .min(1, 'At least one todo is required'),
});

type TodoFormData = z.infer<typeof todoSchema>;

export function DynamicTodoForm() {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<TodoFormData>({
    resolver: zodResolver(todoSchema),
    defaultValues: {
      title: '',
      todos: [{ text: '', priority: 'medium' }],
    },
  });

  const { fields, append, remove, move } = useFieldArray({
    control,
    name: 'todos',
  });

  const onSubmit: SubmitHandler<TodoFormData> = (data) => {
    console.log('Todo list:', data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label htmlFor="title">List Title</label>
        <input id="title" {...register('title')} />
        {errors.title && <span className="error">{errors.title.message}</span>}
      </div>

      <h3>Todos</h3>
      {fields.map((field, index) => (
        <div key={field.id} style={{ border: '1px solid #ccc', padding: '10px', marginBottom: '10px' }}>
          <div>
            <label htmlFor={`todos.${index}.text`}>Todo #{index + 1}</label>
            <input id={`todos.${index}.text`} {...register(`todos.${index}.text`)} />
            {errors.todos?.[index]?.text && (
              <span className="error">{errors.todos[index].text.message}</span>
            )}
          </div>

          <div>
            <label htmlFor={`todos.${index}.priority`}>Priority</label>
            <select id={`todos.${index}.priority`} {...register(`todos.${index}.priority`)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div>
            <button type="button" onClick={() => remove(index)}>
              Remove
            </button>
            {index > 0 && (
              <button type="button" onClick={() => move(index, index - 1)}>
                Move Up
              </button>
            )}
            {index < fields.length - 1 && (
              <button type="button" onClick={() => move(index, index + 1)}>
                Move Down
              </button>
            )}
          </div>
        </div>
      ))}

      <button type="button" onClick={() => append({ text: '', priority: 'medium' })}>
        Add Todo
      </button>

      {errors.todos && <span className="error">{errors.todos.message}</span>}

      <div>
        <button type="submit">Submit</button>
      </div>
    </form>
  );
}

// ============================================================================
// Controlled Components (Custom UI Libraries)
// ============================================================================

// Simulated custom date picker component
function DatePicker({ value, onChange }: { value: Date | null; onChange: (date: Date) => void }) {
  return (
    <input
      type="date"
      value={value ? value.toISOString().split('T')[0] : ''}
      onChange={(e) => onChange(new Date(e.target.value))}
    />
  );
}

const eventSchema = z.object({
  name: z.string().min(1, 'Event name is required'),
  date: z.date(),
  attendees: z.number().min(1, 'At least 1 attendee required'),
  notes: z.string().optional(),
});

type EventFormData = z.infer<typeof eventSchema>;

export function EventForm() {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
    setValue,
  } = useForm<EventFormData>({
    resolver: zodResolver(eventSchema),
    defaultValues: {
      name: '',
      date: new Date(),
      attendees: 1,
      notes: '',
    },
  });

  const onSubmit: SubmitHandler<EventFormData> = (data) => {
    console.log('Event:', data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label htmlFor="name">Event Name</label>
        <input id="name" {...register('name')} />
        {errors.name && <span className="error">{errors.name.message}</span>}
      </div>

      <div>
        <label htmlFor="date">Date</label>
        <Controller
          name="date"
          control={control}
          render={({ field }) => (
            <DatePicker
              value={field.value}
              onChange={field.onChange}
            />
          )}
        />
        {errors.date && <span className="error">{errors.date.message}</span>}
      </div>

      <div>
        <label htmlFor="attendees">Attendees</label>
        <input
          id="attendees"
          type="number"
          {...register('attendees', { valueAsNumber: true })}
        />
        {errors.attendees && <span className="error">{errors.attendees.message}</span>}
      </div>

      <div>
        <label htmlFor="notes">Notes</label>
        <textarea id="notes" {...register('notes')} />
      </div>

      <button type="submit">Create Event</button>
    </form>
  );
}

// ============================================================================
// Custom Validation
// ============================================================================

const passwordSchema = z
  .object({
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type PasswordFormData = z.infer<typeof passwordSchema>;

export function PasswordForm() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  const onSubmit: SubmitHandler<PasswordFormData> = (data) => {
    console.log('Password updated:', data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label htmlFor="password">New Password</label>
        <input id="password" type="password" {...register('password')} />
        {errors.password && <span className="error">{errors.password.message}</span>}
      </div>

      <div>
        <label htmlFor="confirmPassword">Confirm Password</label>
        <input id="confirmPassword" type="password" {...register('confirmPassword')} />
        {errors.confirmPassword && <span className="error">{errors.confirmPassword.message}</span>}
      </div>

      <button type="submit">Update Password</button>
    </form>
  );
}

// ============================================================================
// Form with Async Validation
// ============================================================================

const usernameSchema = z.object({
  username: z
    .string()
    .min(3, 'Username must be at least 3 characters')
    .max(20, 'Username must be at most 20 characters')
    .regex(/^[a-zA-Z0-9_]+$/, 'Username can only contain letters, numbers, and underscores'),
});

type UsernameFormData = z.infer<typeof usernameSchema>;

export function UsernameForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isValidating },
    setError,
  } = useForm<UsernameFormData>({
    resolver: zodResolver(usernameSchema),
  });

  const checkUsernameAvailability = async (username: string): Promise<boolean> => {
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    return !['admin', 'root', 'user'].includes(username.toLowerCase());
  };

  const onSubmit: SubmitHandler<UsernameFormData> = async (data) => {
    const isAvailable = await checkUsernameAvailability(data.username);
    if (!isAvailable) {
      setError('username', {
        type: 'manual',
        message: 'Username is already taken',
      });
      return;
    }

    console.log('Username available:', data.username);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label htmlFor="username">Username</label>
        <input id="username" {...register('username')} />
        {isValidating && <span>Checking availability...</span>}
        {errors.username && <span className="error">{errors.username.message}</span>}
      </div>

      <button type="submit">Check and Submit</button>
    </form>
  );
}

// ============================================================================
// Form State Management Utilities
// ============================================================================

export function FormStateDemo() {
  const {
    register,
    formState: { isDirty, dirtyFields, isValid, errors, touchedFields, isSubmitted },
  } = useForm({
    mode: 'all',
    defaultValues: {
      name: '',
      email: '',
    },
  });

  return (
    <div>
      <form>
        <input {...register('name', { required: true })} />
        <input {...register('email', { required: true, pattern: /^\S+@\S+$/i })} />
      </form>

      <div>
        <h3>Form State:</h3>
        <p>isDirty: {isDirty ? 'Yes' : 'No'}</p>
        <p>isValid: {isValid ? 'Yes' : 'No'}</p>
        <p>isSubmitted: {isSubmitted ? 'Yes' : 'No'}</p>
        <p>Dirty fields: {JSON.stringify(dirtyFields)}</p>
        <p>Touched fields: {JSON.stringify(touchedFields)}</p>
        <p>Errors: {JSON.stringify(errors)}</p>
      </div>
    </div>
  );
}
