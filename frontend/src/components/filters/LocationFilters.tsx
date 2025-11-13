"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

export interface LocationFilterState {
  birthplace_country?: string;
  training_gym?: string;
}

interface LocationFiltersProps {
  filters: LocationFilterState;
  onFilterChange: (filters: LocationFilterState) => void;
  onClear?: () => void;
  availableCountries?: string[];
  availableGyms?: string[];
}

export function LocationFilters({
  filters,
  onFilterChange,
  onClear,
  availableCountries = [],
  availableGyms = [],
}: LocationFiltersProps) {
  const handleClear = () => {
    if (onClear) {
      onClear();
    } else {
      onFilterChange({});
    }
  };

  const hasActiveFilters = filters.birthplace_country || filters.training_gym;

  return (
    <div className="space-y-4 rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Filter by Location</h3>
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={handleClear}>
            <X className="mr-1 h-4 w-4" />
            Clear
          </Button>
        )}
      </div>

      {/* Birthplace Country */}
      <div className="space-y-2">
        <Label htmlFor="birthplace-country">Birthplace Country</Label>
        <Select
          value={filters.birthplace_country || ""}
          onValueChange={(value) =>
            onFilterChange({
              ...filters,
              birthplace_country: value || undefined,
            })
          }
        >
          <SelectTrigger id="birthplace-country">
            <SelectValue placeholder="All countries" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All countries</SelectItem>
            {availableCountries.map((country) => (
              <SelectItem key={country} value={country}>
                {country}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Training Gym */}
      <div className="space-y-2">
        <Label htmlFor="training-gym">Training Gym</Label>
        <Select
          value={filters.training_gym || ""}
          onValueChange={(value) =>
            onFilterChange({ ...filters, training_gym: value || undefined })
          }
        >
          <SelectTrigger id="training-gym">
            <SelectValue placeholder="All gyms" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All gyms</SelectItem>
            {availableGyms.map((gym) => (
              <SelectItem key={gym} value={gym}>
                {gym}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className="border-t border-border/50 pt-2">
          <p className="mb-2 text-xs text-muted-foreground">Active filters:</p>
          <div className="flex flex-wrap gap-1.5">
            {filters.birthplace_country && (
              <span className="inline-flex items-center gap-1 rounded bg-primary/10 px-2 py-1 text-xs text-primary">
                Country: {filters.birthplace_country}
                <button
                  onClick={() =>
                    onFilterChange({
                      ...filters,
                      birthplace_country: undefined,
                    })
                  }
                  className="hover:text-primary/80"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
            {filters.training_gym && (
              <span className="inline-flex items-center gap-1 rounded bg-secondary px-2 py-1 text-xs text-secondary-foreground">
                Gym: {filters.training_gym}
                <button
                  onClick={() =>
                    onFilterChange({ ...filters, training_gym: undefined })
                  }
                  className="hover:opacity-80"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
