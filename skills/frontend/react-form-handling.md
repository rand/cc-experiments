---
name: frontend-react-form-handling
description: Building complex forms
---



# React Form Handling

**Scope**: React Hook Form, Zod validation, Server Actions, multi-step forms, form patterns
**Lines**: ~290
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Building complex forms
- Implementing form validation
- Handling form submission
- Creating multi-step forms
- Optimizing form performance
- Integrating with APIs

## Core Concepts

### Uncontrolled vs Controlled Forms

**Uncontrolled** (refs):
```tsx
function UncontrolledForm() {
  const emailRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log(emailRef.current?.value);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input ref={emailRef} name="email" />
      <button type="submit">Submit</button>
    </form>
  );
}
```

**Controlled** (state):
```tsx
function ControlledForm() {
  const [email, setEmail] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log(email);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={email} onChange={(e) => setEmail(e.target.value)} />
      <button type="submit">Submit</button>
    </form>
  );
}
```

**Trade-offs**:
- Uncontrolled: Better performance, less re-renders
- Controlled: Easier validation, conditional rendering

---

## React Hook Form

### Basic Usage

```tsx
import { useForm } from 'react-hook-form';

interface FormData {
  email: string;
  password: string;
}

function LoginForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>();

  const onSubmit = (data: FormData) => {
    console.log(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input
        {...register('email', {
          required: 'Email is required',
          pattern: {
            value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
            message: 'Invalid email address',
          },
        })}
      />
      {errors.email && <span>{errors.email.message}</span>}

      <input
        type="password"
        {...register('password', {
          required: 'Password is required',
          minLength: {
            value: 8,
            message: 'Password must be at least 8 characters',
          },
        })}
      />
      {errors.password && <span>{errors.password.message}</span>}

      <button type="submit">Login</button>
    </form>
  );
}
```

### Validation Rules

```tsx
const { register } = useForm();

<input
  {...register('username', {
    required: 'Required',
    minLength: { value: 3, message: 'Min 3 characters' },
    maxLength: { value: 20, message: 'Max 20 characters' },
    pattern: { value: /^[a-zA-Z0-9_]+$/, message: 'Alphanumeric only' },
    validate: {
      unique: async (value) => {
        const exists = await checkUsername(value);
        return !exists || 'Username already taken';
      },
    },
  })}
/>
```

### Watch Values

```tsx
function DynamicForm() {
  const { register, watch } = useForm();

  const watchShowAge = watch('showAge', false);
  const watchAllFields = watch(); // Watch all fields

  return (
    <form>
      <input type="checkbox" {...register('showAge')} />
      <label>Show age field</label>

      {watchShowAge && (
        <input type="number" {...register('age')} />
      )}

      <pre>{JSON.stringify(watchAllFields, null, 2)}</pre>
    </form>
  );
}
```

### Controller for Custom Components

```tsx
import { Controller } from 'react-hook-form';
import Select from 'react-select';

function FormWithCustomComponents() {
  const { control, handleSubmit } = useForm();

  return (
    <form onSubmit={handleSubmit(console.log)}>
      <Controller
        name="country"
        control={control}
        rules={{ required: 'Country is required' }}
        render={({ field, fieldState: { error } }) => (
          <>
            <Select
              {...field}
              options={[
                { value: 'us', label: 'United States' },
                { value: 'uk', label: 'United Kingdom' },
              ]}
            />
            {error && <span>{error.message}</span>}
          </>
        )}
      />
    </form>
  );
}
```

---

## Zod Validation

### Schema Definition

```tsx
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Min 8 characters'),
  confirmPassword: z.string(),
  age: z.number().min(18, 'Must be 18+').optional(),
  terms: z.boolean().refine((val) => val === true, {
    message: 'You must accept terms',
  }),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type FormData = z.infer<typeof schema>;

function SignupForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = (data: FormData) => {
    console.log(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}

      <input type="password" {...register('password')} />
      {errors.password && <span>{errors.password.message}</span>}

      <input type="password" {...register('confirmPassword')} />
      {errors.confirmPassword && <span>{errors.confirmPassword.message}</span>}

      <input type="number" {...register('age', { valueAsNumber: true })} />
      {errors.age && <span>{errors.age.message}</span>}

      <input type="checkbox" {...register('terms')} />
      {errors.terms && <span>{errors.terms.message}</span>}

      <button type="submit">Sign Up</button>
    </form>
  );
}
```

### Reusable Schemas

```tsx
// schemas/user.ts
import { z } from 'zod';

export const emailSchema = z.string().email('Invalid email');
export const passwordSchema = z.string().min(8, 'Min 8 characters');

export const loginSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
});

export const signupSchema = loginSchema.extend({
  confirmPassword: passwordSchema,
  username: z.string().min(3, 'Min 3 characters'),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

export type LoginData = z.infer<typeof loginSchema>;
export type SignupData = z.infer<typeof signupSchema>;
```

---

## Server Actions Integration

### Basic Server Action Form

```tsx
// app/actions.ts
'use server';

import { z } from 'zod';

const schema = z.object({
  email: z.string().email(),
  message: z.string().min(10),
});

export async function submitContactForm(formData: FormData) {
  const rawData = {
    email: formData.get('email'),
    message: formData.get('message'),
  };

  // Validate
  const result = schema.safeParse(rawData);
  if (!result.success) {
    return { error: result.error.flatten().fieldErrors };
  }

  // Process
  await sendEmail(result.data);

  return { success: true };
}

// app/contact/page.tsx
import { submitContactForm } from '@/app/actions';

export default function ContactPage() {
  return (
    <form action={submitContactForm}>
      <input name="email" type="email" required />
      <textarea name="message" required />
      <button type="submit">Submit</button>
    </form>
  );
}
```

### useFormState for Errors

```tsx
// app/components/ContactForm.tsx
'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { submitContactForm } from '@/app/actions';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending}>
      {pending ? 'Submitting...' : 'Submit'}
    </button>
  );
}

export function ContactForm() {
  const [state, formAction] = useFormState(submitContactForm, null);

  return (
    <form action={formAction}>
      <input name="email" type="email" required />
      {state?.error?.email && <span>{state.error.email[0]}</span>}

      <textarea name="message" required />
      {state?.error?.message && <span>{state.error.message[0]}</span>}

      <SubmitButton />

      {state?.success && <p>Message sent successfully!</p>}
    </form>
  );
}
```

### React Hook Form + Server Actions

```tsx
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { createPost } from '@/app/actions';

const schema = z.object({
  title: z.string().min(3),
  content: z.string().min(10),
});

type FormData = z.infer<typeof schema>;

export function CreatePostForm() {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    const formData = new FormData();
    formData.append('title', data.title);
    formData.append('content', data.content);

    const result = await createPost(formData);

    if (result.error) {
      // Handle server errors
      alert(result.error);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('title')} />
      {errors.title && <span>{errors.title.message}</span>}

      <textarea {...register('content')} />
      {errors.content && <span>{errors.content.message}</span>}

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Creating...' : 'Create Post'}
      </button>
    </form>
  );
}
```

---

## Multi-Step Forms

### State-Based Multi-Step

```tsx
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const step1Schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

const step2Schema = z.object({
  firstName: z.string().min(2),
  lastName: z.string().min(2),
});

const step3Schema = z.object({
  bio: z.string().min(10),
  interests: z.array(z.string()),
});

type Step1Data = z.infer<typeof step1Schema>;
type Step2Data = z.infer<typeof step2Schema>;
type Step3Data = z.infer<typeof step3Schema>;

type FormData = Step1Data & Step2Data & Step3Data;

function MultiStepForm() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<Partial<FormData>>({});

  const schema = step === 1 ? step1Schema : step === 2 ? step2Schema : step3Schema;

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: formData,
  });

  const onSubmit = (data: any) => {
    const updatedData = { ...formData, ...data };
    setFormData(updatedData);

    if (step < 3) {
      setStep(step + 1);
    } else {
      // Final submission
      console.log('Complete form data:', updatedData);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {step === 1 && (
        <>
          <input {...register('email')} />
          {errors.email && <span>{errors.email.message}</span>}

          <input type="password" {...register('password')} />
          {errors.password && <span>{errors.password.message}</span>}
        </>
      )}

      {step === 2 && (
        <>
          <input {...register('firstName')} />
          {errors.firstName && <span>{errors.firstName.message}</span>}

          <input {...register('lastName')} />
          {errors.lastName && <span>{errors.lastName.message}</span>}
        </>
      )}

      {step === 3 && (
        <>
          <textarea {...register('bio')} />
          {errors.bio && <span>{errors.bio.message}</span>}
        </>
      )}

      <div>
        {step > 1 && <button type="button" onClick={() => setStep(step - 1)}>Back</button>}
        <button type="submit">{step === 3 ? 'Submit' : 'Next'}</button>
      </div>

      <div>Step {step} of 3</div>
    </form>
  );
}
```

### URL-Based Multi-Step

```tsx
// app/signup/[step]/page.tsx
'use client';

import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';

export default function SignupStepPage({ params }: { params: { step: string } }) {
  const router = useRouter();
  const step = parseInt(params.step);
  const { register, handleSubmit } = useForm();

  const onSubmit = (data: any) => {
    // Save to state management or API
    if (step < 3) {
      router.push(`/signup/${step + 1}`);
    } else {
      router.push('/dashboard');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* Render appropriate step */}
      <button type="submit">{step === 3 ? 'Submit' : 'Next'}</button>
    </form>
  );
}
```

---

## Form Patterns

### Array Fields (Dynamic Lists)

```tsx
import { useFieldArray } from 'react-hook-form';

function TodoListForm() {
  const { register, control, handleSubmit } = useForm({
    defaultValues: {
      todos: [{ text: '' }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'todos',
  });

  return (
    <form onSubmit={handleSubmit(console.log)}>
      {fields.map((field, index) => (
        <div key={field.id}>
          <input {...register(`todos.${index}.text`)} />
          <button type="button" onClick={() => remove(index)}>Remove</button>
        </div>
      ))}

      <button type="button" onClick={() => append({ text: '' })}>
        Add Todo
      </button>

      <button type="submit">Submit</button>
    </form>
  );
}
```

### File Upload

```tsx
function FileUploadForm() {
  const { register, handleSubmit } = useForm();

  const onSubmit = async (data: any) => {
    const formData = new FormData();
    formData.append('file', data.file[0]);

    await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input
        type="file"
        {...register('file', {
          required: 'File is required',
          validate: {
            fileSize: (files) => files[0]?.size < 5000000 || 'Max 5MB',
            fileType: (files) =>
              ['image/jpeg', 'image/png'].includes(files[0]?.type) ||
              'Only JPEG/PNG',
          },
        })}
      />
      <button type="submit">Upload</button>
    </form>
  );
}
```

### Async Validation

```tsx
function UsernameForm() {
  const { register, formState: { errors } } = useForm();

  return (
    <form>
      <input
        {...register('username', {
          required: 'Username is required',
          validate: {
            checkAvailability: async (value) => {
              const res = await fetch(`/api/check-username?username=${value}`);
              const { available } = await res.json();
              return available || 'Username already taken';
            },
          },
        })}
      />
      {errors.username && <span>{errors.username.message}</span>}
    </form>
  );
}
```

---

## Performance Optimization

### Prevent Unnecessary Re-renders

```tsx
// ❌ Bad: Entire form re-renders on every keystroke
function BadForm() {
  const [formData, setFormData] = useState({ name: '', email: '' });

  return (
    <form>
      <input
        value={formData.name}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
      />
      <input
        value={formData.email}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
      />
    </form>
  );
}

// ✅ Good: React Hook Form uses uncontrolled inputs
function GoodForm() {
  const { register } = useForm();

  return (
    <form>
      <input {...register('name')} />
      <input {...register('email')} />
    </form>
  );
}
```

### Debounce Validation

```tsx
import { useForm } from 'react-hook-form';
import { debounce } from 'lodash';

function SearchForm() {
  const { register } = useForm();

  const debouncedValidate = debounce(async (value: string) => {
    const res = await fetch(`/api/search?q=${value}`);
    return res.json();
  }, 300);

  return (
    <input
      {...register('search', {
        validate: debouncedValidate,
      })}
    />
  );
}
```

---

## Quick Reference

### React Hook Form Setup

```tsx
const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
  resolver: zodResolver(schema),
  defaultValues: { ... },
});

<form onSubmit={handleSubmit(onSubmit)}>
  <input {...register('field')} />
  {errors.field && <span>{errors.field.message}</span>}
</form>
```

### Zod Schema Pattern

```tsx
const schema = z.object({
  email: z.string().email(),
  age: z.number().min(18),
}).refine(...);

type FormData = z.infer<typeof schema>;
```

### Server Action Pattern

```tsx
'use server';
export async function action(formData: FormData) {
  const result = schema.safeParse({...});
  if (!result.success) return { error: ... };
  // Process
  revalidatePath('/path');
}
```

---

## Common Anti-Patterns

❌ **Controlled inputs for every field**: Performance issues
✅ Use React Hook Form (uncontrolled)

❌ **Manual validation logic**: Error-prone, verbose
✅ Use Zod schemas

❌ **Not handling loading states**: Poor UX
✅ Use isSubmitting, pending states

❌ **Client-side only validation**: Security risk
✅ Validate on server too

---

## Related Skills

- `react-component-patterns.md` - Form components, custom hooks
- `react-data-fetching.md` - Mutations, optimistic updates
- `nextjs-app-router.md` - Server Actions, revalidation
- `web-accessibility.md` - Form labels, ARIA, keyboard navigation

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
