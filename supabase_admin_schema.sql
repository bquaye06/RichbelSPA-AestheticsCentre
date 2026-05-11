-- Create admin credentials table
CREATE TABLE IF NOT EXISTS admin_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_admin_credentials_email ON admin_credentials(email);

-- Enable Row Level Security (optional, for security)
ALTER TABLE admin_credentials ENABLE ROW LEVEL SECURITY;
