import { useEffect, useRef, useState, KeyboardEvent } from "react";
import { searchAirports } from "../api/airports";
import type { AirportOption } from "../types";

type AirportInputProps = {
  label: string;
  value: string;
  onChange: (next: string) => void;
  placeholder: string;
  airportOptions: AirportOption[];
};

export function AirportInput({
  label,
  value,
  onChange,
  placeholder,
  airportOptions,
}: AirportInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [filterText, setFilterText] = useState(value);
  const [remoteResults, setRemoteResults] = useState<AirportOption[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setFilterText(value);
  }, [value]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const searchKeyword = filterText.trim().toLowerCase();

  // Perform debounced live backend airport search
  useEffect(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    if (searchKeyword.length < 2) {
      setRemoteResults([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    timerRef.current = setTimeout(() => {
      searchAirports(searchKeyword)
        .then((results) => {
          setRemoteResults(results);
        })
        .catch(() => {
          setRemoteResults([]);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }, 300);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [searchKeyword]);

  // Combine static options and dynamic search results
  const localMatches = airportOptions.filter((item) => {
    if (!searchKeyword) return true;
    return (
      item.code.toLowerCase().includes(searchKeyword) ||
      item.city.toLowerCase().includes(searchKeyword) ||
      item.country.toLowerCase().includes(searchKeyword) ||
      item.label.toLowerCase().includes(searchKeyword)
    );
  });

  const combinedMap = new Map<string, AirportOption>();
  localMatches.forEach((item) => combinedMap.set(item.code, item));
  remoteResults.forEach((item) => combinedMap.set(item.code, item));

  // Limit display to top 10 matches
  const matches = Array.from(combinedMap.values()).slice(0, 10);

  const popularCodes = ["HYD", "BOM", "DEL", "BLR", "DXB", "LHR", "JFK", "SIN"];
  const popularChips = airportOptions.filter((item) => popularCodes.includes(item.code));

  const handleSelect = (code: string) => {
    onChange(code);
    setFilterText(code);
    setIsOpen(false);
    setSelectedIndex(-1);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        setIsOpen(true);
      }
      return;
    }

    if (e.key === "Escape") {
      setIsOpen(false);
      setSelectedIndex(-1);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < matches.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : matches.length - 1));
    } else if (e.key === "Enter") {
      if (selectedIndex >= 0 && selectedIndex < matches.length) {
        e.preventDefault();
        handleSelect(matches[selectedIndex].code);
      }
    }
  };

  return (
    <div className="field airport-autocomplete-field" ref={containerRef}>
      <span className="field-label">{label}</span>
      <div className="input-wrapper">
        <input
          aria-label={label}
          type="text"
          value={filterText}
          placeholder={placeholder}
          maxLength={50}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          onChange={(e) => {
            const val = e.target.value;
            setFilterText(val);
            onChange(val.toUpperCase().slice(0, 3));
            setIsOpen(true);
            setSelectedIndex(-1);
          }}
        />
        {isOpen && (
          <div className="airport-dropdown">
            {isLoading && <div className="dropdown-no-results">Searching airports...</div>}
            {!isLoading && matches.length > 0 ? (
              matches.map((item, idx) => (
                <button
                  key={item.code}
                  className={`dropdown-item ${idx === selectedIndex ? "selected" : ""}`}
                  type="button"
                  onClick={() => handleSelect(item.code)}
                >
                  <div className="dropdown-item-header">
                    <span className="airport-badge">{item.code}</span>
                    <span className="airport-city">{item.city}</span>
                  </div>
                  <div className="dropdown-item-sub">
                    {item.country} · {item.label}
                  </div>
                </button>
              ))
            ) : !isLoading ? (
              <div className="dropdown-no-results">No matching airports</div>
            ) : null}
          </div>
        )}
      </div>

      <div className="suggestion-row">
        {popularChips.slice(0, 4).map((item) => (
          <button
            key={item.code}
            className="suggestion-chip"
            type="button"
            onClick={() => handleSelect(item.code)}
          >
            {item.code} · {item.city}
          </button>
        ))}
      </div>
    </div>
  );
}
