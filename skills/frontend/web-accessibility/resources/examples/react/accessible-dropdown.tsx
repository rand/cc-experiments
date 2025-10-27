import React, { useState, useRef, useEffect } from 'react';

/**
 * Accessible Dropdown (Combobox) Component
 *
 * Features:
 * - ARIA combobox pattern
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 * - aria-activedescendant for active option
 * - Proper focus management
 * - Search/filter functionality
 * - aria-expanded state
 */

interface Option {
  id: string;
  label: string;
  value: string;
}

interface ComboboxProps {
  label: string;
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function AccessibleCombobox({
  label,
  options,
  value,
  onChange,
  placeholder = 'Select an option',
}: ComboboxProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const comboboxRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listboxRef = useRef<HTMLUListElement>(null);
  const optionRefs = useRef<(HTMLLIElement | null)[]>([]);

  const comboboxId = `combobox-${Math.random().toString(36).substr(2, 9)}`;
  const listboxId = `${comboboxId}-listbox`;

  // Filter options based on input
  const filteredOptions = options.filter(option =>
    option.label.toLowerCase().includes(inputValue.toLowerCase())
  );

  // Get selected option label
  const selectedOption = options.find(opt => opt.value === value);

  useEffect(() => {
    if (selectedOption && !isOpen) {
      setInputValue(selectedOption.label);
    }
  }, [selectedOption, isOpen]);

  useEffect(() => {
    // Scroll highlighted option into view
    if (isOpen && optionRefs.current[highlightedIndex]) {
      optionRefs.current[highlightedIndex]?.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      });
    }
  }, [highlightedIndex, isOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (
        comboboxRef.current &&
        !comboboxRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    setIsOpen(true);
    setHighlightedIndex(0);
  };

  const handleInputFocus = () => {
    setIsOpen(true);
  };

  const selectOption = (option: Option) => {
    onChange(option.value);
    setInputValue(option.label);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (!isOpen) {
          setIsOpen(true);
        } else {
          setHighlightedIndex(prev =>
            Math.min(prev + 1, filteredOptions.length - 1)
          );
        }
        break;

      case 'ArrowUp':
        e.preventDefault();
        if (isOpen) {
          setHighlightedIndex(prev => Math.max(prev - 1, 0));
        }
        break;

      case 'Enter':
        e.preventDefault();
        if (isOpen && filteredOptions[highlightedIndex]) {
          selectOption(filteredOptions[highlightedIndex]);
        }
        break;

      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        if (selectedOption) {
          setInputValue(selectedOption.label);
        }
        break;

      case 'Home':
        e.preventDefault();
        if (isOpen) {
          setHighlightedIndex(0);
        }
        break;

      case 'End':
        e.preventDefault();
        if (isOpen) {
          setHighlightedIndex(filteredOptions.length - 1);
        }
        break;
    }
  };

  return (
    <div ref={comboboxRef} style={{ marginBottom: '1.5rem' }}>
      <label
        htmlFor={comboboxId}
        style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}
      >
        {label}
      </label>

      <div style={{ position: 'relative' }}>
        <input
          ref={inputRef}
          id={comboboxId}
          type="text"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={isOpen}
          aria-controls={listboxId}
          aria-activedescendant={
            isOpen && filteredOptions[highlightedIndex]
              ? `${comboboxId}-option-${highlightedIndex}`
              : undefined
          }
          value={inputValue}
          onChange={handleInputChange}
          onFocus={handleInputFocus}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          style={{
            width: '100%',
            padding: '0.5rem',
            fontSize: '1rem',
            border: '1px solid #ccc',
            borderRadius: '4px',
          }}
        />

        {isOpen && filteredOptions.length > 0 && (
          <ul
            ref={listboxRef}
            id={listboxId}
            role="listbox"
            style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              marginTop: '4px',
              padding: 0,
              listStyle: 'none',
              backgroundColor: 'white',
              border: '1px solid #ccc',
              borderRadius: '4px',
              maxHeight: '200px',
              overflowY: 'auto',
              boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
              zIndex: 1000,
            }}
          >
            {filteredOptions.map((option, index) => (
              <li
                key={option.id}
                ref={el => (optionRefs.current[index] = el)}
                id={`${comboboxId}-option-${index}`}
                role="option"
                aria-selected={index === highlightedIndex}
                onClick={() => selectOption(option)}
                style={{
                  padding: '0.5rem 1rem',
                  cursor: 'pointer',
                  backgroundColor:
                    index === highlightedIndex ? '#e6f2ff' : 'transparent',
                }}
              >
                {option.label}
              </li>
            ))}
          </ul>
        )}

        {isOpen && filteredOptions.length === 0 && (
          <div
            role="status"
            aria-live="polite"
            style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              marginTop: '4px',
              padding: '1rem',
              backgroundColor: 'white',
              border: '1px solid #ccc',
              borderRadius: '4px',
              textAlign: 'center',
              color: '#666',
            }}
          >
            No options found
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Example Usage
 */
export function DropdownExample() {
  const [selectedFruit, setSelectedFruit] = useState('');

  const fruits: Option[] = [
    { id: '1', label: 'Apple', value: 'apple' },
    { id: '2', label: 'Banana', value: 'banana' },
    { id: '3', label: 'Cherry', value: 'cherry' },
    { id: '4', label: 'Date', value: 'date' },
    { id: '5', label: 'Elderberry', value: 'elderberry' },
    { id: '6', label: 'Fig', value: 'fig' },
    { id: '7', label: 'Grape', value: 'grape' },
    { id: '8', label: 'Honeydew', value: 'honeydew' },
  ];

  return (
    <div style={{ maxWidth: '600px', margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Accessible Combobox Example</h1>

      <AccessibleCombobox
        label="Select a fruit"
        options={fruits}
        value={selectedFruit}
        onChange={setSelectedFruit}
        placeholder="Type to search..."
      />

      {selectedFruit && (
        <p>
          Selected: <strong>{fruits.find(f => f.value === selectedFruit)?.label}</strong>
        </p>
      )}

      <div style={{ marginTop: '2rem' }}>
        <h2>Keyboard Navigation</h2>
        <ul>
          <li><kbd>↓</kbd> Arrow Down - Open dropdown or move to next option</li>
          <li><kbd>↑</kbd> Arrow Up - Move to previous option</li>
          <li><kbd>Enter</kbd> - Select highlighted option</li>
          <li><kbd>Escape</kbd> - Close dropdown</li>
          <li><kbd>Home</kbd> - Jump to first option</li>
          <li><kbd>End</kbd> - Jump to last option</li>
          <li>Type to filter options</li>
        </ul>
      </div>
    </div>
  );
}
