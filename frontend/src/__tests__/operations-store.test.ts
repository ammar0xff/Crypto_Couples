import { describe, expect, it, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOperationsStore } from "../store/operations";
import type { OperationSummary, OperationEvent } from "../types";

const base: OperationSummary = {
  id: "abc",
  kind: "split",
  media: "image",
  method: "stack",
  status: "processing",
  progress: 40,
  message: "mid",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
};

describe("operations store", () => {
  beforeEach(() => {
    useOperationsStore.getState().reset();
  });

  it("upsert adds a summary", () => {
    const { result } = renderHook(() => useOperationsStore());
    act(() => result.current.upsert(base));
    expect(result.current.ops["abc"]).toEqual(base);
  });

  it("remove deletes a summary", () => {
    const { result } = renderHook(() => useOperationsStore());
    act(() => {
      result.current.upsert(base);
      result.current.remove("abc");
    });
    expect(result.current.ops["abc"]).toBeUndefined();
  });

  it("applyEvent maps progress snapshot", () => {
    const { result } = renderHook(() => useOperationsStore());
    act(() => result.current.upsert(base));
    const evt: OperationEvent = {
      type: "progress",
      progress: 75,
      message: "doing work",
    };
    act(() => result.current.applyEvent("abc", evt));
    expect(result.current.ops["abc"]).toEqual(
      expect.objectContaining({ progress: 75, message: "doing work" }),
    );
  });

  it("applyEvent maps completed", () => {
    const { result } = renderHook(() => useOperationsStore());
    act(() => result.current.upsert(base));
    act(() =>
      result.current.applyEvent("abc", { type: "completed" } as OperationEvent),
    );
    expect(result.current.ops["abc"].status).toBe("completed");
  });

  it("applyEvent maps cancelled", () => {
    const { result } = renderHook(() => useOperationsStore());
    act(() => result.current.upsert(base));
    act(() =>
      result.current.applyEvent("abc", {
        type: "cancelled",
      } as OperationEvent),
    );
    expect(result.current.ops["abc"].status).toBe("cancelled");
  });

  it("applyEvent maps error to failed and captures error message", () => {
    const { result } = renderHook(() => useOperationsStore());
    act(() => result.current.upsert(base));
    act(() =>
      result.current.applyEvent("abc", {
        type: "error",
        message: "bad input",
        error: { code: "ERR", message: "detail" },
      } as OperationEvent),
    );
    const op = result.current.ops["abc"];
    expect(op.status).toBe("failed");
    expect(op.message).toBe("detail");
  });

  it("applyEvent falls back to base defaults for missing op", () => {
    const { result } = renderHook(() => useOperationsStore());
    act(() =>
      result.current.applyEvent("ghost", {
        type: "progress",
        progress: 10,
      } as OperationEvent),
    );
    const op = result.current.ops["ghost"];
    expect(op.status).toBe("processing");
    expect(op.kind).toBe("split");
    expect(op.media).toBe("file");
  });

  it("reset clears all ops", () => {
    const { result } = renderHook(() => useOperationsStore());
    act(() => {
      result.current.upsert(base);
      result.current.upsert({ ...base, id: "def" });
      result.current.reset();
    });
    expect(Object.keys(result.current.ops)).toHaveLength(0);
  });
});
