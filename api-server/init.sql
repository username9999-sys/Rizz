-- Initialize PostgreSQL database for Rizz API

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    excerpt TEXT,
    cover_image VARCHAR(500),
    published BOOLEAN DEFAULT false,
    views INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_approved BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags table
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL
);

-- Post-Tags relationship
CREATE TABLE IF NOT EXISTS post_tags (
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);

-- API Tokens table
CREATE TABLE IF NOT EXISTS api_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rate limiting table
CREATE TABLE IF NOT EXISTS rate_limits (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL,
    endpoint VARCHAR(100) NOT NULL,
    request_count INTEGER DEFAULT 1,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(identifier, endpoint, window_start)
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_slug ON posts(slug);
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published);
CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_rate_limits_lookup ON rate_limits(identifier, endpoint, window_start);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, password_hash, is_admin) VALUES
    ('admin', 'admin@rizz.dev', sha256('admin123'::text), true)
ON CONFLICT (username) DO NOTHING;

-- Insert sample tags
INSERT INTO tags (name, slug) VALUES
    ('Technology', 'technology'),
    ('Programming', 'programming'),
    ('Python', 'python'),
    ('JavaScript', 'javascript'),
    ('Web Development', 'web-development'),
    ('API', 'api'),
    ('Database', 'database'),
    ('DevOps', 'devops'),
    ('Tutorial', 'tutorial'),
    ('News', 'news')
ON CONFLICT (slug) DO NOTHING;

-- Create view for post statistics
CREATE OR REPLACE VIEW post_stats AS
SELECT 
    p.id,
    p.title,
    p.slug,
    p.views,
    p.published,
    p.created_at,
    COUNT(DISTINCT c.id) as comment_count,
    COUNT(DISTINCT pt.tag_id) as tag_count
FROM posts p
LEFT JOIN comments c ON p.id = c.post_id
LEFT JOIN post_tags pt ON p.id = pt.post_id
GROUP BY p.id, p.title, p.slug, p.views, p.published, p.created_at;

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO rizz_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO rizz_user;
