export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Opportunity {
  id: string;
  title: string;
  organization: string;
  description: string | null;
  url: string;
  source: string;
  location: string | null;
  is_remote: boolean;
  stipend: string | null;
  deadline: string | null;
  tags: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Application {
  id: string;
  user_id: string;
  company: string;
  role: string;
  job_link: string | null;
  hr_contact: string | null;
  status: string;
  date_applied: string | null;
  notes: string | null;
  source: string;
  opportunity_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
