import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DEFAULT_MAX_RESULTS, DEFAULT_PASSENGERS, DEFAULT_TRAVEL_CLASS, TRAVEL_CLASSES } from "../constants";
import { AirportInput } from "./AirportInput";
import type { AirportOption, ToastType } from "../types";

export type SearchFormProps = {
  compact?: boolean;
  onNotify?: (message: string, type?: ToastType) => void;
  onFormChange?: () => void;
  today: string;
  airportOptions: AirportOption[];
};

export function SearchForm({ compact = false, onNotify, onFormChange, today, airportOptions }: SearchFormProps) {
  const navigate = useNavigate();
  const [origin, setOrigin] = useState("HYD");
  const [destination, setDestination] = useState("DXB");
  const [departure, setDeparture] = useState(today);
  const [travelClass, setTravelClass] = useState(DEFAULT_TRAVEL_CLASS);
  const [adults, setAdults] = useState(String(DEFAULT_PASSENGERS.adults));
  const [children, setChildren] = useState(String(DEFAULT_PASSENGERS.children));
  const [infants, setInfants] = useState(String(DEFAULT_PASSENGERS.infants));
  const [nonStop, setNonStop] = useState(false);

  const handleOriginChange = (val: string) => { setOrigin(val); onFormChange?.(); };
  const handleDestinationChange = (val: string) => { setDestination(val); onFormChange?.(); };
  const handleDepartureChange = (val: string) => { setDeparture(val); onFormChange?.(); };
  const handleClassChange = (val: string) => { setTravelClass(val); onFormChange?.(); };
  const handleAdultsChange = (val: string) => { setAdults(val); onFormChange?.(); };
  const handleChildrenChange = (val: string) => { setChildren(val); onFormChange?.(); };
  const handleInfantsChange = (val: string) => { setInfants(val); onFormChange?.(); };
  const handleNonStopChange = (val: boolean) => { setNonStop(val); onFormChange?.(); };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const iataRegex = /^[A-Z]{3}$/;
    const origUpper = origin.trim().toUpperCase();
    const destUpper = destination.trim().toUpperCase();
    if (!iataRegex.test(origUpper) || !iataRegex.test(destUpper)) {
      onNotify?.("Please enter valid 3-letter airport IATA codes (e.g. HYD, BOM, DEL, DXB).", "warning");
      return;
    }
    if (origUpper === destUpper) {
      onNotify?.("Origin and destination must be different.", "warning");
      return;
    }

    if (typeof window !== "undefined") {
      const current = Number(window.localStorage.getItem("ai-flight-analytics-searches") ?? "0");
      window.localStorage.setItem("ai-flight-analytics-searches", String(current + 1));
    }
    const params = new URLSearchParams({
      origin: origin.toUpperCase(),
      destination: destination.toUpperCase(),
      departure_date: departure,
      travel_class: travelClass,
      adults,
      children,
      infants,
      non_stop: String(nonStop),
      max_results: String(DEFAULT_MAX_RESULTS),
    });
    navigate(`/search?${params.toString()}`);
    onNotify?.("Search submitted", "info");
  };

  return (
    <form className={compact ? "search compact" : "search"} onSubmit={submit}>
      <AirportInput label="From" value={origin} onChange={handleOriginChange} placeholder="e.g. HYD" airportOptions={airportOptions} />
      <AirportInput label="To" value={destination} onChange={handleDestinationChange} placeholder="e.g. DXB" airportOptions={airportOptions} />
      <label className="field">
        <span className="field-label">Departure</span>
        <input aria-label="Departure date" type="date" min={today} value={departure} onChange={(event) => handleDepartureChange(event.target.value)} />
      </label>
      <label className="field">
        <span className="field-label">Travel class</span>
        <select value={travelClass} onChange={(event) => handleClassChange(event.target.value)}>
          {TRAVEL_CLASSES.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
      <label className="field">
        <span className="field-label">Adults</span>
        <input aria-label="Adults" type="number" min="1" max="9" value={adults} onChange={(event) => handleAdultsChange(event.target.value)} />
      </label>
      <label className="field">
        <span className="field-label">Children</span>
        <input aria-label="Children" type="number" min="0" max="9" value={children} onChange={(event) => handleChildrenChange(event.target.value)} />
      </label>
      <label className="field">
        <span className="field-label">Infants</span>
        <input aria-label="Infants" type="number" min="0" max="9" value={infants} onChange={(event) => handleInfantsChange(event.target.value)} />
      </label>
      <label className="checkbox-row compact">
        <input type="checkbox" checked={nonStop} onChange={(event) => handleNonStopChange(event.target.checked)} />
        <span>Non-stop only</span>
      </label>
      <button className="primary-button" type="submit">Search flights</button>
    </form>
  );
}
