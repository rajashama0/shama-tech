-- Shama Tech backend tables
-- Load this file into MySQL before using the APIs.

CREATE DATABASE IF NOT EXISTS shama_tech
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE shama_tech;

-- Flyton base tables.
-- DROP TABLE IF EXISTS logs;
-- DROP TABLE IF EXISTS ses;
-- DROP TABLE IF EXISTS users;
-- DROP TABLE IF EXISTS gen;

CREATE TABLE IF NOT EXISTS gen (
    id int AUTO_INCREMENT,
    name varchar(255) NOT NULL UNIQUE,
    val1 varchar(255) DEFAULT NULL,
    is_active tinyint DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    data json DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_gen_active_name (is_active, name)
);

CREATE TABLE IF NOT EXISTS users (
    id int AUTO_INCREMENT,
    name varchar(255) NOT NULL,
    username varchar(255) DEFAULT NULL UNIQUE,
    sis varchar(255) DEFAULT NULL,
    is_active tinyint DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    data json DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_users_active_name (is_active, name)
);

CREATE TABLE IF NOT EXISTS ses (
    id varchar(64) NOT NULL,
    name varchar(255) DEFAULT NULL,
    user_id int DEFAULT 0,
    is_active tinyint DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    data json DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_ses_active_updated (is_active, updated_at),
    INDEX idx_ses_user (user_id)
);

CREATE TABLE IF NOT EXISTS logs (
    id int AUTO_INCREMENT,
    name varchar(255) DEFAULT NULL,
    act_type varchar(255) DEFAULT NULL,
    send_text text DEFAULT NULL,
    response text DEFAULT NULL,
    is_active tinyint DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    data json DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_logs_active_created (is_active, created_at),
    INDEX idx_logs_act_type (act_type)
);

INSERT INTO gen
    (id, name, val1, is_active, data)
VALUES
    (101, 'gen_tab', '0', 1, '{"tab_type":"gen"}'),
    (102, 'users_tab', '0', 1, '{"tab_type":"data"}'),
    (103, 'ses_tab', '0', 1, '{"tab_type":"session"}'),
    (104, 'logs_tab', '0', 1, '{"tab_type":"archive"}')
ON DUPLICATE KEY UPDATE
    val1 = VALUES(val1),
    is_active = VALUES(is_active),
    data = VALUES(data);

-- Shama Tech business tables.

CREATE TABLE IF NOT EXISTS services (
    id int AUTO_INCREMENT,
    name varchar(255) NOT NULL,
    slug varchar(255) NOT NULL UNIQUE,
    short_description text NOT NULL,
    long_description text NOT NULL,
    icon_key varchar(100) DEFAULT NULL,
    display_order int DEFAULT 100,
    is_active tinyint DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    data json DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_services_active_order (is_active, display_order)
);

CREATE TABLE IF NOT EXISTS case_studies (
    id int AUTO_INCREMENT,
    title varchar(255) NOT NULL,
    slug varchar(255) NOT NULL UNIQUE,
    client_name varchar(255) DEFAULT NULL,
    industry varchar(255) DEFAULT NULL,
    problem text NOT NULL,
    solution text NOT NULL,
    technologies json DEFAULT NULL,
    outcome text NOT NULL,
    image_url text DEFAULT NULL,
    is_published tinyint DEFAULT 0,
    display_order int DEFAULT 100,
    is_active tinyint DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    data json DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_case_public_order (is_active, is_published, display_order),
    INDEX idx_case_slug (slug)
);

CREATE TABLE IF NOT EXISTS contact_submissions (
    id int AUTO_INCREMENT,
    full_name varchar(255) NOT NULL,
    company_name varchar(255) DEFAULT NULL,
    email varchar(255) NOT NULL,
    phone varchar(100) DEFAULT NULL,
    service_interest varchar(255) NOT NULL,
    budget_range varchar(100) DEFAULT NULL,
    message text NOT NULL,
    source_page varchar(255) DEFAULT NULL,
    status varchar(40) DEFAULT 'new',
    is_active tinyint DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    data json DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_contact_status_created (status, created_at),
    INDEX idx_contact_active_created (is_active, created_at)
);

INSERT INTO services
    (id, name, slug, short_description, long_description, icon_key, display_order, is_active)
VALUES
    (1001, 'Full-stack web apps', 'full-stack-web-apps', 'End-to-end web application delivery.', 'Design and build production-ready web applications with backend APIs, database structure, and frontend integration.', 'web_app', 10, 1),
    (1002, 'Websites', 'websites', 'Credibility and conversion websites.', 'Build fast, clear websites for companies that need trust, lead capture, and maintainable content structure.', 'website', 20, 1),
    (1003, 'Dashboards', 'dashboards', 'Operational dashboards and reporting views.', 'Create business dashboards that make key workflows, metrics, and decisions easier to see and manage.', 'dashboard', 30, 1),
    (1004, 'MVP and SaaS development', 'mvp-saas-development', 'Lean MVP and SaaS product builds.', 'Plan and build the first useful version of a software product with a clean path to future growth.', 'saas', 40, 1),
    (1005, 'Backend and API development', 'backend-api-development', 'Reliable backend services and APIs.', 'Build database-backed Python APIs, integrations, server workflows, and internal business logic.', 'api', 50, 1),
    (1006, 'AI automation consulting', 'ai-automation-consulting', 'Find practical AI automation opportunities.', 'Review operations and identify where AI can save time, reduce manual work, or improve service quality.', 'ai_consulting', 60, 1),
    (1007, 'AI workflow automation', 'ai-workflow-automation', 'Automate repeatable business processes.', 'Connect AI, data, documents, and business tools into dependable automated workflows.', 'workflow', 70, 1),
    (1008, 'Custom internal tools', 'custom-internal-tools', 'Tools for teams and operations.', 'Build focused software for internal teams, approvals, tracking, data entry, and repeatable processes.', 'tools', 80, 1),
    (1009, 'Document and data extraction', 'document-data-extraction', 'Extract useful data from files and forms.', 'Turn documents, emails, PDFs, forms, and messy data into structured records and workflows.', 'extract', 90, 1),
    (1010, 'Chatbot and assistant integrations', 'chatbot-assistant-integrations', 'Useful assistants connected to real workflows.', 'Add AI assistants and chatbots that answer, route, collect, and act using approved business data.', 'assistant', 100, 1),
    (1011, 'CRM, ERP, and process automation', 'crm-erp-process-automation', 'Connect systems and reduce manual handoffs.', 'Automate CRM, ERP, and operational processes with clean integrations and clear business rules.', 'process', 110, 1)
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    short_description = VALUES(short_description),
    long_description = VALUES(long_description),
    icon_key = VALUES(icon_key),
    display_order = VALUES(display_order),
    is_active = VALUES(is_active);
