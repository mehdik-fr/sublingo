import type { AnalyzeSubtitlesRequest, AnalyzeSubtitlesResponse, CueAnalysis } from "./backend-client";

export type SubtitleLanguagePair = {
  sourceLanguage: string;
  targetLanguage: string;
};

export type SubtitleAnalysisInput = {
  text: string;
  contextBefore?: string;
  contextAfter?: string;
};

export type SubtitleAnalysisResult = {
  cue: CueAnalysis;
  provider: AnalyzeSubtitlesResponse["provider"];
  sourceLanguage: string;
  targetLanguage: string;
};

type BatchAnalyzer = (request: AnalyzeSubtitlesRequest) => Promise<AnalyzeSubtitlesResponse>;

type PendingRequest = {
  cueId: string;
  input: SubtitleAnalysisInput;
  languages: SubtitleLanguagePair;
  resolve: (result: SubtitleAnalysisResult) => void;
  reject: (error: unknown) => void;
};

type CacheEntry = {
  result: SubtitleAnalysisResult;
  expiresAt: number;
};

export class SubtitleAnalysisQueue {
  private readonly analyzer: BatchAnalyzer;
  private readonly batchDelayMs: number;
  private readonly cacheTtlMs: number;
  private readonly maxBatchSize: number;
  private readonly maxCacheEntries: number;
  private readonly maxPendingEntries: number;
  private readonly now: () => number;
  private cache = new Map<string, CacheEntry>();
  private pending = new Map<string, PendingRequest[]>();
  private flushTimer: ReturnType<typeof setTimeout> | null = null;
  private isFlushing = false;
  private cueSequence = 0;

  constructor(
    analyzer: BatchAnalyzer,
    options: {
      batchDelayMs?: number;
      cacheTtlMs?: number;
      maxBatchSize?: number;
      maxCacheEntries?: number;
      maxPendingEntries?: number;
      now?: () => number;
    } = {}
  ) {
    this.analyzer = analyzer;
    this.batchDelayMs = options.batchDelayMs ?? 40;
    this.cacheTtlMs = options.cacheTtlMs ?? 30 * 60 * 1000;
    this.maxBatchSize = options.maxBatchSize ?? 2;
    this.maxCacheEntries = options.maxCacheEntries ?? 500;
    this.maxPendingEntries = options.maxPendingEntries ?? 4;
    this.now = options.now ?? Date.now;
  }

  request(
    input: SubtitleAnalysisInput,
    languages: SubtitleLanguagePair
  ): Promise<SubtitleAnalysisResult> {
    const key = this.createKey(input, languages);
    const cached = this.cache.get(key);

    if (cached && cached.expiresAt > this.now()) {
      this.cache.delete(key);
      this.cache.set(key, cached);
      return Promise.resolve(cached.result);
    }

    if (cached) {
      this.cache.delete(key);
    }

    return new Promise<SubtitleAnalysisResult>((resolve, reject) => {
      if (!this.pending.has(key)) {
        this.evictStalePendingEntries();
      }

      const pendingForKey = this.pending.get(key) ?? [];
      pendingForKey.push({
        cueId: `cue-${this.cueSequence += 1}`,
        input,
        languages,
        resolve,
        reject
      });
      this.pending.set(key, pendingForKey);
      this.scheduleFlush();
    });
  }

  clear(): void {
    this.cache.clear();

    if (this.flushTimer !== null) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }

    const error = new Error("Subtitle analysis queue cleared");
    this.pending.forEach((waiters) => waiters.forEach((waiter) => waiter.reject(error)));
    this.pending.clear();
  }

  private scheduleFlush(): void {
    if (this.flushTimer !== null || this.isFlushing) {
      return;
    }

    this.flushTimer = setTimeout(() => {
      this.flushTimer = null;
      void this.flush();
    }, this.batchDelayMs);
  }

  private async flush(): Promise<void> {
    if (this.isFlushing) {
      return;
    }

    const firstPending = this.pending.values().next().value?.[0] as PendingRequest | undefined;

    if (!firstPending) {
      return;
    }

    this.isFlushing = true;

    const languages = firstPending.languages;
    const entries = Array.from(this.pending.entries())
      .filter(([, requests]) => {
        const pair = requests[0].languages;
        return (
          pair.sourceLanguage === languages.sourceLanguage &&
          pair.targetLanguage === languages.targetLanguage
        );
      })
      .slice(0, this.maxBatchSize);

    for (const [key] of entries) {
      this.pending.delete(key);
    }

    const primaryRequests = entries.map(([, requests]) => requests[0]);
    const request: AnalyzeSubtitlesRequest = {
      schemaVersion: "1.0",
      sourceLanguage: languages.sourceLanguage,
      targetLanguage: languages.targetLanguage,
      cues: primaryRequests.map((pending) => ({
        cueId: pending.cueId,
        text: pending.input.text,
        contextBefore: pending.input.contextBefore,
        contextAfter: pending.input.contextAfter
      }))
    };

    try {
      const response = await this.analyzer(request);
      const cuesById = new Map(response.cues.map((cue) => [cue.cueId, cue]));

      for (let index = 0; index < entries.length; index += 1) {
        const [key, waiters] = entries[index];
        const cue = cuesById.get(primaryRequests[index].cueId);

        if (!cue) {
          throw new Error(`Analysis response omitted cue ${primaryRequests[index].cueId}`);
        }

        const result: SubtitleAnalysisResult = {
          cue,
          provider: response.provider,
          sourceLanguage: response.sourceLanguage,
          targetLanguage: response.targetLanguage
        };
        this.setCache(key, result);
        waiters.forEach((waiter) => waiter.resolve(result));
      }
    } catch (error) {
      entries.forEach(([, waiters]) => waiters.forEach((waiter) => waiter.reject(error)));
    }

    this.isFlushing = false;

    if (this.pending.size > 0) {
      this.scheduleFlush();
    }
  }

  private evictStalePendingEntries(): void {
    while (this.pending.size >= this.maxPendingEntries) {
      const oldestEntry = this.pending.entries().next().value as
        | [string, PendingRequest[]]
        | undefined;

      if (!oldestEntry) {
        return;
      }

      const [key, waiters] = oldestEntry;
      this.pending.delete(key);
      const error = new Error("Subtitle analysis request superseded by newer captions");
      waiters.forEach((waiter) => waiter.reject(error));
    }
  }

  private setCache(key: string, result: SubtitleAnalysisResult): void {
    this.cache.set(key, {
      result,
      expiresAt: this.now() + this.cacheTtlMs
    });

    while (this.cache.size > this.maxCacheEntries) {
      const oldestKey = this.cache.keys().next().value as string | undefined;

      if (!oldestKey) {
        break;
      }

      this.cache.delete(oldestKey);
    }
  }

  private createKey(input: SubtitleAnalysisInput, languages: SubtitleLanguagePair): string {
    return [
      languages.sourceLanguage,
      languages.targetLanguage,
      input.contextBefore?.trim() ?? "",
      input.text.trim(),
      input.contextAfter?.trim() ?? ""
    ].join("\u0000");
  }
}
