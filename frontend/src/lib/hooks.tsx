import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

interface AppContextValue {
  refreshToken: number;
  refresh: () => void;
}

const AppContext = createContext<AppContextValue>({ refreshToken: 0, refresh: () => {} });

export function AppProvider({ children }: { children: ReactNode }) {
  const [refreshToken, setRefreshToken] = useState(0);
  const refresh = useCallback(() => setRefreshToken((t) => t + 1), []);
  return <AppContext.Provider value={{ refreshToken, refresh }}>{children}</AppContext.Provider>;
}

export function useApp() {
  return useContext(AppContext);
}

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useFetch<T>(fn: () => Promise<T>, deps: unknown[] = []): FetchState<T> {
  const { refreshToken } = useApp();
  const [state, setState] = useState<FetchState<T>>({ data: null, loading: true, error: null });
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    let active = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    fnRef
      .current()
      .then((data) => {
        if (active) setState({ data, loading: false, error: null });
      })
      .catch((err: Error) => {
        if (active) setState({ data: null, loading: false, error: err.message });
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshToken, ...deps]);

  return state;
}
