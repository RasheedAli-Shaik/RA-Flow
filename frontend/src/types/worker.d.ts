declare class Worker extends EventTarget {
  constructor(scriptURL: string | URL, options?: WorkerOptions);
  onmessage: ((this: Worker, ev: MessageEvent) => unknown) | null;
  onerror: ((this: Worker, ev: ErrorEvent) => unknown) | null;
  postMessage(message: unknown, transfer?: Transferable[]): void;
  terminate(): void;
}
