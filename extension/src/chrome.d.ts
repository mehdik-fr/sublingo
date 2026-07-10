declare namespace chrome {
  namespace runtime {
    type MessageSender = {
      tab?: tabs.Tab;
    };

    type MessageListener = (
      message: unknown,
      sender: MessageSender,
      sendResponse: (response: unknown) => void
    ) => boolean | void;

    const onMessage: {
      addListener(listener: MessageListener): void;
    };
  }

  namespace storage {
    type StorageChange = {
      oldValue?: unknown;
      newValue?: unknown;
    };

    type StorageChanges = Record<string, StorageChange>;

    interface StorageArea {
      get(keys?: string | string[] | Record<string, unknown>): Promise<Record<string, unknown>>;
      set(items: Record<string, unknown>): Promise<void>;
    }

    const sync: StorageArea;

    const onChanged: {
      addListener(listener: (changes: StorageChanges, areaName: string) => void): void;
    };
  }

  namespace tabs {
    type Tab = {
      id?: number;
      url?: string;
    };

    type QueryInfo = {
      active?: boolean;
      currentWindow?: boolean;
    };

    function query(queryInfo: QueryInfo): Promise<Tab[]>;
    function sendMessage(tabId: number, message: unknown): Promise<unknown>;
  }
}
