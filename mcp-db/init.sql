CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Users
INSERT INTO users (username, email) VALUES 
('alice', 'alice@example.com'),
('bob', 'bob@example.com'),
('charlie', 'charlie@example.com');

-- Seed Notes
INSERT INTO notes (user_id, title, content) VALUES 
(1, 'Project Alpha', 'Meeting notes for Alpha project kickoff. Remember to buy coffee.'),
(1, 'Groceries', 'Milk, Bread, Eggs, and a lot of chocolote.'),
(2, 'Deployment Checklist', '1. Build Docker image\n2. Push to registry\n3. Restart pods'),
(3, 'Ideas', 'Build a bridge to the moon using only duct tape.');
