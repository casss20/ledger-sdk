import { useSearchParams } from "react-router-dom";

export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const getFilter = (key: string, defaultValue: string = "") => {
    return searchParams.get(key) || defaultValue;
  };

  const setFilter = (key: string, value: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    setSearchParams(newParams);
  };

  const clearFilters = () => {
    setSearchParams(new URLSearchParams());
  };

  return { getFilter, setFilter, clearFilters };
}
