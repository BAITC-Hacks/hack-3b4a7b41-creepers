export type MessageRole = "assistant" | "user";

export interface ChatMessageData {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: Date;
}