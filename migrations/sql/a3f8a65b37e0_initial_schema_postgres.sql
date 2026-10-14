BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> a3f8a65b37e0

CREATE TABLE "user" (
    id SERIAL NOT NULL, 
    username VARCHAR(20) NOT NULL, 
    email VARCHAR(120), 
    password_hash VARCHAR(60) NOT NULL, 
    is_admin BOOLEAN NOT NULL, 
    is_banned BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (email), 
    UNIQUE (username)
);

CREATE TABLE history (
    id SERIAL NOT NULL, 
    crop VARCHAR(100) NOT NULL, 
    disease VARCHAR(100) NOT NULL, 
    advisory_json TEXT NOT NULL, 
    image_url VARCHAR(255) NOT NULL, 
    timestamp TIMESTAMP WITHOUT TIME ZONE, 
    user_id INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES "user" (id)
);

INSERT INTO alembic_version (version_num) VALUES ('a3f8a65b37e0') RETURNING alembic_version.version_num;

COMMIT;

