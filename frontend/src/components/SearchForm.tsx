import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DEFAULT_MAX_RESULTS, DEFAULT_PASSENGERS, DEFAULT_TRAVEL_CLASS, TRAVEL_CLASSES } from "../constants";
import { AirportInput } from "./AirportInput";
import type { AirportOption, ToastType } from "../types";

export type SearchFormProps = {
  compact?: boolean;
  onNotify?: (message: string, type?: ToastType) => void;
  today: string;
  airportOptions: AirportOption[];
};

export function SearchForm({ compact = false, onNotify, today, airportOptions }: SearchFormProps) {
  const navigate = useNavigate();
  const [origin, setOrigin] = useState("HYD");
  const [destination, setDestination] = useState("DXB");
  const [departure, setDeparture] = useState(today);
  const [travelClass, setTravelClass] = useState(DEFAULT_TRAVEL_CLASS);
  const [adults, setAdults] = useState(String(DEFAULT_PASSENGERS.adults));
  const [children, setChildren] = useState(String(DEFAULT_PASSENGERS.children));
  const [infants, setInfants] = useState(String(DEFAULT_PASSENGERS.infants));
  const [nonStop, setNonStop] = useState(false);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const originOption = airportOptions.find((item) => item.code === origin.toUpperCase());
    const destinationOption = airportOptions.find((item) => item.code === destination.toUpperCase());
    if (!originOption || !destinationOption) {
      onNotify?.("Please pick a known airport from the suggestions.", "warning");
      return;
    }
    if (origin.toUpperCase() === destination.toUpperCase()) {
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
      <AirportInput label="From" value={origin} onChange={setOrigin} placeholder="e.g. HYD" airportOptions={airportOptions} />
      <AirportInput label="To" value={destination} onChange={setDestination} placeholder="e.g. DXB" airportOptions={airportOptions} />
      <label className="field">
        <span className="field-label">Departure</span>
        <input aria-label="Departure date" type="date" min={today} value={departure} onChange={(event) => setDeparture(event.target.value)} />
      </label>
      <label className="field">
        <span className="field-label">Travel class</span>
        <select value={travelClass} onChange={(event) => setTravelClass(event.target.value)}>
          {TRAVEL_CLASSES.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
      <label className="field">
        <span className="field-label">Adults</span>
        <input aria-label="Adults" type="number" min="1" max="9" value={adults} onChange={(event) => setAdults(event.target.value)} />
      </label>
      <label className="field">
        <span className="field-label">Children</span>
        <input aria-label="Children" type="number" min="0" max="9" value={children} onChange={(event) => setChildren(event.target.value)} />
      </label>
      <label className="field">
        <span className="field-label">Infants</span>
        <input aria-label="Infants" type="number" min="0" max="9" value={infants} onChange={(event) => setInfants(event.target.value)} />
      </label>
      <label className="checkbox-row compact">
        <input type="checkbox" checked={nonStop} onChange={(event) => setNonStop(event.target.checked)} />
        <span>Non-stop only</span>
      </label>
      <button className="primary-button" type="submit">Search flights</button>
    </form>
  );
}
