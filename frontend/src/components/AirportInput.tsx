import { useEffect, useRef, useState } from "react";
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
  const containerRef = useRef<HTMLDivElement>(null);

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
  const matches = airportOptions.filter((item) => {
    if (!searchKeyword) return true;
    return (
      item.code.toLowerCase().includes(searchKeyword) ||
      item.city.toLowerCase().includes(searchKeyword) ||
      item.country.toLowerCase().includes(searchKeyword) ||
      item.label.toLowerCase().includes(searchKeyword)
    );
  });

  const popularCodes = ["HYD", "DXB", "DEL", "BOM", "LHR", "SIN", "BKK"];
  const popularChips = airportOptions.filter((item) => popularCodes.includes(item.code));

  const handleSelect = (code: string) => {
    onChange(code);
    setFilterText(code);
    setIsOpen(false);
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
          onChange={(e) => {
            const val = e.target.value;
            setFilterText(val);
            onChange(val.toUpperCase().slice(0, 3));
            setIsOpen(true);
          }}
        />
        {isOpen && (
          <div className="airport-dropdown">
            {matches.length > 0 ? (
              matches.map((item) => (
                <button
                  key={item.code}
                  className="dropdown-item"
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
            ) : (
              <div className="dropdown-no-results">No matching airports</div>
            )}
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
