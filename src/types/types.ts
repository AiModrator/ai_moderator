import axios, { AxiosInstance } from 'axios';




export type User = {
	id: string;
	username: string;
	name: string;
	bio: string | null;
	profile_picture_url: string | null;
	created_at: Date;
	companies?: Company[];
	posts?: Post[];
};

export type Company = {
	id: string;
	title: string;
	description: string | null;
	verified: boolean;
	business_type: string | null;
	industry_type: string | null;
	send_customer_emails: boolean;
	created_at: Date;
	updated_at: Date;
	member_count: number;
	route: string | null;
	logo_url: string | null;
	user_id: string;
	user?: User;
	forums?: Forum[];
};

export type Forum = {
	id: string;
	experience_id: string;
	experience_name: string;
	company_id: string;
	who_can_post: string | null;
	who_can_comment: string | null;
	email_notification_preference: string | null;
	company?: Company;
	posts?: Post[];
};

export type Post = {
	id: string;
	forum_id: string;
	title: string | null;
	content: string | null;
	created_at: Date;
	updated_at: Date;
	is_edited: boolean;
	is_poster_admin: boolean;
	is_pinned: boolean;
	parent_id: string | null;
	user_id: string;
	view_count: number;
	like_count: number;
	comment_count: number;
	forum?: Forum;
	user?: User;
	parent?: Post | null;
	children?: Post[];
};

export interface ChatChannel {
  id: string;
  experience_id: string;
  experience_name: string;
  ban_media: boolean;
  ban_urls: boolean;
  company ?: Company
  who_can_post: string | null;
  who_can_react: string | null;
  user_posts_cooldown_seconds: number | null;
  banned_words: string[];
  
}


export type Scan = {
	id: string;
	last_scan_at: Date;
};

export interface PageInfo {
  end_cursor: string | null;
  start_cursor: string | null;
  has_next_page: boolean;
  has_previous_page: boolean;
}

export interface ListPostResponse {
  data: Post[];
  page_info: PageInfo;
}

export type UserData = {
  user: User;
  company: Company;
  forums: Forum[];
  chats: ChatChannel[];
};

/**
 * Interface pour les clients de modération IA (sans AxiosInstance)
 * Utilisée principalement pour les mocks et les tests
 */
export interface IModerationClient {
  getModeration: (text: string) => Promise<{ risk: number }>;
  risks: string[];
  getName?: () => string;
  setConfig?: (config: any) => void;
}

/**
 * Interface pour la collection de clients de modération IA
 */
export interface IModerationClients {
  moderators: IModerationClient[];
  getModerator?: (index: number) => IModerationClient;
  moderateContent?: (text: string) => Promise<{ moderator: string; risk: number }[]>;
}

/**
 * Interfaces originales pour rétro-compatibilité
 */
export interface AiModerationClient extends AxiosInstance {
  getModeration: (text: string) => Promise<any>;
  risks: string[];
}

export interface AiModerationClients {
  moderators: AiModerationClient[];
}