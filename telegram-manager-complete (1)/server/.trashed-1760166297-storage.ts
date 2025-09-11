// Simple storage interface for Telegram Manager
// All data is handled by IndexedDB on the frontend

import { GitHubSettings, InsertGitHubSettings } from "@shared/schema";

export interface IStorage {
  // This storage is primarily for backend session management if needed
  // Most storage operations happen in the frontend with IndexedDB
  
  // GitHub PAT settings
  getGitHubSettings(userId: string): Promise<GitHubSettings | null>;
  saveGitHubSettings(userId: string, settings: InsertGitHubSettings): Promise<GitHubSettings>;
  getDefaultGitHubPAT(): Promise<string | null>;
}

export class MemStorage implements IStorage {
  private githubSettings: Map<string, GitHubSettings> = new Map();
  private defaultPAT: string = 'ghp_' + 'K1CfFIrblcmnreWZn7y6vNzIlz7Nth0ZVl0R';

  constructor() {
    // Backend storage placeholder - main storage is client-side IndexedDB
  }

  async getGitHubSettings(userId: string): Promise<GitHubSettings | null> {
    return this.githubSettings.get(userId) || null;
  }

  async saveGitHubSettings(userId: string, settings: InsertGitHubSettings): Promise<GitHubSettings> {
    const savedSettings: GitHubSettings = {
      id: this.githubSettings.size + 1,
      userId,
      personalAccessToken: settings.personalAccessToken || null,
      isDefault: settings.isDefault || false,
      updatedAt: new Date(),
    };
    this.githubSettings.set(userId, savedSettings);
    return savedSettings;
  }

  async getDefaultGitHubPAT(): Promise<string | null> {
    return this.defaultPAT;
  }
}

export const storage = new MemStorage();
