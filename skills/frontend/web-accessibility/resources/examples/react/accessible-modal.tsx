import React, { useEffect, useRef } from 'react';

/**
 * Accessible Modal Component
 *
 * Features:
 * - Focus trap (Tab/Shift+Tab cycle within modal)
 * - Escape key to close
 * - Focus management (save/restore focus)
 * - ARIA attributes (role="dialog", aria-modal, aria-labelledby)
 * - Backdrop click to close
 * - Prevents body scroll when open
 */

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  /**
   * Optional ID for the title element.
   * If not provided, a random ID will be generated.
   */
  titleId?: string;
}

export function AccessibleModal({
  isOpen,
  onClose,
  title,
  children,
  titleId = `modal-title-${Math.random().toString(36).substr(2, 9)}`,
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    // Save element that had focus before modal opened
    previousFocusRef.current = document.activeElement as HTMLElement;

    const dialog = dialogRef.current;
    if (!dialog) return;

    // Get all focusable elements
    const focusableElements = dialog.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Focus first element
    firstElement.focus();

    // Handle Tab key for focus trap
    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        // Shift + Tab: moving backwards
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab: moving forwards
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    // Handle Escape key
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    // Prevent body scroll
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // Add event listeners
    dialog.addEventListener('keydown', handleTabKey);
    dialog.addEventListener('keydown', handleEscape);

    // Cleanup
    return () => {
      dialog.removeEventListener('keydown', handleTabKey);
      dialog.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = originalOverflow;

      // Restore focus to element that opened the modal
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="modal-backdrop"
        onClick={onClose}
        aria-hidden="true"
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          zIndex: 999,
        }}
      />

      {/* Modal Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          backgroundColor: 'white',
          padding: '2rem',
          borderRadius: '8px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          maxWidth: '500px',
          width: '90%',
          maxHeight: '90vh',
          overflow: 'auto',
          zIndex: 1000,
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
          }}
        >
          <h2
            id={titleId}
            style={{
              margin: 0,
              fontSize: '1.5rem',
            }}
          >
            {title}
          </h2>

          <button
            onClick={onClose}
            aria-label="Close dialog"
            style={{
              background: 'none',
              border: 'none',
              fontSize: '1.5rem',
              cursor: 'pointer',
              padding: '0.25rem',
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        {/* Modal Content */}
        <div>{children}</div>
      </div>
    </>
  );
}

/**
 * Example Usage
 */
export function ModalExample() {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <div>
      <h1>Accessible Modal Example</h1>

      <button onClick={() => setIsOpen(true)}>Open Modal</button>

      <AccessibleModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Example Modal"
      >
        <p>
          This is an accessible modal dialog. It demonstrates:
        </p>
        <ul>
          <li>Focus trap (try pressing Tab)</li>
          <li>Escape key to close</li>
          <li>Focus restoration when closed</li>
          <li>ARIA attributes</li>
        </ul>

        <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem' }}>
          <button onClick={() => setIsOpen(false)}>Close</button>
          <button onClick={() => alert('Saved!')}>Save</button>
        </div>
      </AccessibleModal>

      <p>
        Try opening the modal and navigating with your keyboard:
      </p>
      <ul>
        <li><kbd>Tab</kbd> - Move forward through focusable elements</li>
        <li><kbd>Shift+Tab</kbd> - Move backward</li>
        <li><kbd>Escape</kbd> - Close modal</li>
      </ul>
    </div>
  );
}
