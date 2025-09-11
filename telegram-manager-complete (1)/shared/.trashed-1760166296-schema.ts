import { pgTable, serial, varchar, text, integer, timestamp, boolean, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Database tables
export const downloads = pgTable("downloads", {
  id: serial("id").primaryKey(),
  userId: varchar("user_id").notNull(),
  messageId: integer("message_id").notNull(),
  originalFilename: varchar("original_filename").notNull(),
  filePath: varchar("file_path"),
  url: text("url"),
  fileType: varchar("file_type").notNull(),
  fileSize: integer("file_size"),
  status: varchar("status").notNull().default("pending"), // pending, downloading, completed, failed
  progress: integer("progress").default(0),
  error: text("error"),
  downloadDate: timestamp("download_date").defaultNow(),
  updateDate: timestamp("update_date"),
});

export const pendingMessages = pgTable("pending_messages", {
  id: serial("id").primaryKey(),
  userId: varchar("user_id").notNull(),
  messageId: integer("message_id").notNull(),
  messageType: varchar("message_type").notNull(), // download, command, youtube
  content: text("content").notNull(),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const botSessions = pgTable("bot_sessions", {
  id: serial("id").primaryKey(),
  botId: varchar("bot_id").notNull().unique(),
  sessionString: text("session_string").notNull(),
  config: jsonb("config").notNull(),
  status: varchar("status").notNull().default("inactive"), // active, inactive, error
  lastError: text("last_error"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const githubSettings = pgTable("github_settings", {
  id: serial("id").primaryKey(),
  userId: varchar("user_id").notNull().unique(),
  personalAccessToken: text("personal_access_token"),
  isDefault: boolean("is_default").default(false),
  updatedAt: timestamp("updated_at").defaultNow(),
});

// Zod schemas for validation
export const telegramSessionSchema = z.object({
  sessionString: z.string(),
  apiId: z.number(),
  apiHash: z.string(),
  phoneNumber: z.string(),
  userId: z.string().optional(),
  firstName: z.string().optional(),
  lastName: z.string().optional(),
});

export const chatSchema = z.object({
  id: z.string(),
  title: z.string(),
  type: z.enum(['channel', 'group', 'private']),
  participantCount: z.number().optional(),
  username: z.string().optional(),
  accessHash: z.string().optional(),
});

export const messageSchema = z.object({
  id: z.number(),
  chatId: z.string(),
  text: z.string().optional(),
  date: z.string(),
  senderId: z.string().optional(),
  senderName: z.string().optional(),
  hasMedia: z.boolean(),
  mediaType: z.string().optional(),
  mediaSize: z.number().optional(),
  mediaFileName: z.string().optional(),
});

export const downloadItemSchema = z.object({
  id: z.string(),
  messageId: z.number(),
  chatId: z.string(),
  fileName: z.string(),
  fileSize: z.number(),
  progress: z.number(),
  status: z.enum(['pending', 'downloading', 'completed', 'failed', 'cancelled', 'paused']),
  downloadPath: z.string().optional(),
  speed: z.number().optional(),
});

export const searchParamsSchema = z.object({
  chatId: z.string().optional(),
  query: z.string().optional(),
  messageId: z.number().optional(),
  dateFrom: z.string().optional(),
  dateTo: z.string().optional(),
  similarityThreshold: z.number().min(0).max(100).default(70),
  hasMedia: z.boolean().optional(),
  searchInWholeMessage: z.boolean().optional(),
});

export const forwardConfigSchema = z.object({
  name: z.string().min(1, "Configuration name is required"),
  fromChatId: z.string().min(1, "Source chat is required"),
  toChatId: z.string().min(1, "Destination chat is required"),
  offsetFrom: z.number().min(0).default(0),
  offsetTo: z.number().min(0).default(0),
});

export const forwardJobSchema = z.object({
  id: z.string(),
  config: forwardConfigSchema,
  status: z.enum(['idle', 'running', 'paused', 'completed', 'error']),
  currentOffset: z.number(),
  progress: z.number().min(0).max(100),
  logs: z.array(z.string()),
  error: z.string().optional(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

// Create insert schemas
export const insertDownloadSchema = createInsertSchema(downloads);
export const insertPendingMessageSchema = createInsertSchema(pendingMessages);
export const insertBotSessionSchema = createInsertSchema(botSessions);
export const insertGithubSettingsSchema = createInsertSchema(githubSettings).omit({ id: true, updatedAt: true });

// Types
export type Download = typeof downloads.$inferSelect;
export type PendingMessage = typeof pendingMessages.$inferSelect;
export type BotSession = typeof botSessions.$inferSelect;
export type GitHubSettings = typeof githubSettings.$inferSelect;
export type InsertDownload = z.infer<typeof insertDownloadSchema>;
export type InsertPendingMessage = z.infer<typeof insertPendingMessageSchema>;
export type InsertBotSession = z.infer<typeof insertBotSessionSchema>;
export type InsertGitHubSettings = z.infer<typeof insertGithubSettingsSchema>;

export type TelegramSession = z.infer<typeof telegramSessionSchema>;
export type Chat = z.infer<typeof chatSchema>;
export type Message = z.infer<typeof messageSchema>;
export type DownloadItem = z.infer<typeof downloadItemSchema>;
export type SearchParams = z.infer<typeof searchParamsSchema>;
export type ForwardConfig = z.infer<typeof forwardConfigSchema>;
export type ForwardJob = z.infer<typeof forwardJobSchema>;
