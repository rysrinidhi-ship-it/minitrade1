import { useEffect, useState } from "react";

/** Returns `value`, but only after it has stopped changing for `delay` ms (used for search boxes). */
export function useDebouncedValue(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}
