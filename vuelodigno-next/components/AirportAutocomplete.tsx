"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import airportsData from "@/data/airports.json";

interface Airport {
  code: string;
  city: string;
  name: string;
}

interface AirportAutocompleteProps {
  value: string;
  onChange: (code: string) => void;
  placeholder?: string;
  label: string;
  required?: boolean;
  error?: string;
  onInputFocus?: (e: React.FocusEvent<HTMLInputElement>) => void;
}

const airports: Airport[] = airportsData.airports;

export default function AirportAutocomplete({
  value,
  onChange,
  placeholder = "Buscar aeropuerto...",
  label,
  required = false,
  error,
}: AirportAutocompleteProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [filteredAirports, setFilteredAirports] = useState<Airport[]>([]);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Get display value from code
  const getDisplayValue = (code: string): string => {
    if (!code) return "";
    const airport = airports.find((a) => a.code === code);
    return airport ? `${airport.code} - ${airport.city}` : code;
  };

  // Initialize query with display value when value changes
  useEffect(() => {
    if (value && !isOpen) {
      setQuery(getDisplayValue(value));
    }
  }, [value, isOpen]);

  // Filter airports based on query
  useEffect(() => {
    if (!query.trim()) {
      // Show popular Mexican airports when empty
      setFilteredAirports(airports.slice(0, 8));
      return;
    }

    const lowerQuery = query.toLowerCase();
    const filtered = airports.filter(
      (airport) =>
        airport.code.toLowerCase().includes(lowerQuery) ||
        airport.city.toLowerCase().includes(lowerQuery) ||
        airport.name.toLowerCase().includes(lowerQuery)
    );
    setFilteredAirports(filtered.slice(0, 8));
    setHighlightedIndex(0);
  }, [query]);

  const handleSelect = (airport: Airport) => {
    onChange(airport.code);
    setQuery(`${airport.code} - ${airport.city}`);
    setIsOpen(false);
    inputRef.current?.blur();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value.toUpperCase();
    setQuery(newValue);
    setIsOpen(true);

    // If user types exactly 3 characters, check if it's a valid code
    if (newValue.length === 3) {
      const match = airports.find((a) => a.code === newValue);
      if (match) {
        onChange(match.code);
      }
    } else if (newValue.length === 0) {
      onChange("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "Enter") {
        setIsOpen(true);
        e.preventDefault();
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < filteredAirports.length - 1 ? prev + 1 : prev
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : prev));
        break;
      case "Enter":
        e.preventDefault();
        if (filteredAirports[highlightedIndex]) {
          handleSelect(filteredAirports[highlightedIndex]);
        }
        break;
      case "Escape":
        setIsOpen(false);
        inputRef.current?.blur();
        break;
      case "Tab":
        if (filteredAirports[highlightedIndex]) {
          handleSelect(filteredAirports[highlightedIndex]);
        }
        break;
    }
  };

  // Scroll highlighted item into view
  useEffect(() => {
    if (listRef.current && isOpen) {
      const highlightedEl = listRef.current.children[highlightedIndex] as HTMLElement;
      if (highlightedEl) {
        highlightedEl.scrollIntoView({ block: "nearest" });
      }
    }
  }, [highlightedIndex, isOpen]);

  return (
    <div className="relative">
      <label className="block text-sm text-neutral-400 mb-2">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onFocus={(e) => {
            setIsOpen(true);
            // Mobile keyboard autoscroll
            setTimeout(() => {
              e.target.scrollIntoView({ behavior: "smooth", block: "center" });
            }, 300);
          }}
          onBlur={() => {
            // Delay to allow click on dropdown
            setTimeout(() => setIsOpen(false), 150);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full bg-white/5 border-2 border-white/10 rounded-xl py-3 px-4 text-white uppercase
                   placeholder:text-neutral-500 placeholder:normal-case focus:border-accent-500 focus:outline-none transition-colors"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg
            className={`w-5 h-5 text-neutral-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && filteredAirports.length > 0 && (
          <motion.ul
            ref={listRef}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute z-50 w-full mt-2 bg-obsidian-800 border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-64 overflow-y-auto"
          >
            {filteredAirports.map((airport, index) => (
              <li
                key={airport.code}
                onClick={() => handleSelect(airport)}
                onMouseEnter={() => setHighlightedIndex(index)}
                className={`px-4 py-3 cursor-pointer transition-colors ${
                  index === highlightedIndex
                    ? "bg-accent-500/20 text-white"
                    : "text-neutral-300 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-accent-400">{airport.code}</span>
                    <span className="mx-2 text-neutral-500">•</span>
                    <span>{airport.city}</span>
                  </div>
                </div>
                <div className="text-xs text-neutral-500 mt-0.5 truncate">
                  {airport.name}
                </div>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>

      {/* No results message */}
      <AnimatePresence>
        {isOpen && query.length > 0 && filteredAirports.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute z-50 w-full mt-2 bg-obsidian-800 border border-white/10 rounded-xl shadow-2xl p-4 text-center"
          >
            <p className="text-neutral-400 text-sm">
              No se encontró "{query}"
            </p>
            <p className="text-neutral-500 text-xs mt-1">
              Ingresa el código de 3 letras directamente
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {error && <p className="text-red-400 text-sm mt-1">{error}</p>}
    </div>
  );
}
