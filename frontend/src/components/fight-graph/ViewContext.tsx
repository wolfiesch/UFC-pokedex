"use client";

import {
  createContext,
  type Dispatch,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
} from "react";

export type FightGraphViewMode = "2d" | "3d";

interface FightGraphViewState {
  mode: FightGraphViewMode;
  depthFactor: number;
}

interface FightGraphViewAction {
  type: "SET_MODE" | "SET_DEPTH";
  mode?: FightGraphViewMode;
  depthFactor?: number;
}

interface FightGraphViewContextValue extends FightGraphViewState {
  setMode: (mode: FightGraphViewMode) => void;
  toggleMode: () => void;
}

const FightGraphViewContext = createContext<FightGraphViewContextValue | null>(
  null,
);

function reducer(
  state: FightGraphViewState,
  action: FightGraphViewAction,
): FightGraphViewState {
  switch (action.type) {
    case "SET_MODE":
      return action.mode && action.mode !== state.mode
        ? { ...state, mode: action.mode }
        : state;
    case "SET_DEPTH":
      return typeof action.depthFactor === "number"
        ? { ...state, depthFactor: action.depthFactor }
        : state;
    default:
      action satisfies never;
      return state;
  }
}

function animateDepth(
  dispatch: Dispatch<FightGraphViewAction>,
  target: number,
  frameRef: React.MutableRefObject<number | null>,
  depthRef: React.MutableRefObject<number>,
): void {
  const step = () => {
    frameRef.current = requestAnimationFrame(() => {
      const delta = target - depthRef.current;
      const next =
        Math.abs(delta) < 0.001 ? target : depthRef.current + delta * 0.12;
      depthRef.current = next;
      dispatch({ type: "SET_DEPTH", depthFactor: next });

      if (Math.abs(target - next) > 0.001) {
        step();
      } else {
        frameRef.current = null;
      }
    });
  };

  step();
}

export function FightGraphViewProvider({
  children,
}: {
  children: ReactNode;
}): ReactNode {
  const [state, dispatch] = useReducer(reducer, { mode: "2d", depthFactor: 0 });
  const frameRef = useRef<number | null>(null);
  const targetRef = useRef<number>(0);
  const depthRef = useRef<number>(0);

  useEffect(() => {
    targetRef.current = state.mode === "3d" ? 1 : 0;
    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current);
    }
    animateDepth(dispatch, targetRef.current, frameRef, depthRef);
    const frameId = frameRef.current;
    return () => {
      if (frameId !== null) {
        cancelAnimationFrame(frameId);
      }
    };
  }, [state.mode]);

  const setMode = useCallback((mode: FightGraphViewMode) => {
    dispatch({ type: "SET_MODE", mode });
  }, []);

  const toggleMode = useCallback(() => {
    dispatch({ type: "SET_MODE", mode: state.mode === "2d" ? "3d" : "2d" });
  }, [state.mode]);

  const value = useMemo<FightGraphViewContextValue>(
    () => ({
      mode: state.mode,
      depthFactor: state.depthFactor,
      setMode,
      toggleMode,
    }),
    [setMode, state.depthFactor, state.mode, toggleMode],
  );

  return (
    <FightGraphViewContext.Provider value={value}>
      {children}
    </FightGraphViewContext.Provider>
  );
}

export function useFightGraphView(): FightGraphViewContextValue {
  const context = useContext(FightGraphViewContext);
  if (!context) {
    throw new Error(
      "useFightGraphView must be used within a FightGraphViewProvider",
    );
  }
  return context;
}
