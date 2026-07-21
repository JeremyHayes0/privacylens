import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Registers jest-dom's matchers (toBeInTheDocument, toHaveTextContent,
// etc.) on Vitest's `expect` and provides their TS types -- the
// dedicated /vitest entry point does both in one import, rather than
// needing a separate type-augmentation step.
import "@testing-library/jest-dom/vitest";

// React Testing Library doesn't unmount components between tests on
// its own outside of a test-runner integration; without this, a
// component rendered in one test can still be attached to the DOM
// when the next test's queries run.
afterEach(() => {
  cleanup();
});
