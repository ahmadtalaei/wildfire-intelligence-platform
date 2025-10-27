// Frontend Authentication Configuration
// This file should be generated from environment variables in production

// Default development credentials (override with environment variables)
const FRONTEND_CONFIG = {
    scientist: {
        username: process.env.FRONTEND_SCIENTIST_USER || 'admin@scientist.gov',
        password: process.env.FRONTEND_SCIENTIST_PASSWORD || 'scientist_2025'
    },
    analyst: {
        username: process.env.FRONTEND_ANALYST_USER || 'admin@analyst.gov', 
        password: process.env.FRONTEND_ANALYST_PASSWORD || 'analyst_2025'
    },
    admin: {
        username: process.env.FRONTEND_ADMIN_USER || 'admin@admin.gov',
        password: process.env.FRONTEND_ADMIN_PASSWORD || 'wildfire_admin_2025'
    },
    chief: {
        username: process.env.FRONTEND_CHIEF_USER || 'chief@calfire.gov',
        password: process.env.FRONTEND_CHIEF_PASSWORD || 'chief_2025'
    }
};

// Validation function
function validateCredentials(userType, username, password) {
    const config = FRONTEND_CONFIG[userType];
    if (!config) return false;
    return username === config.username && password === config.password;
}

// Export for use in frontend applications
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FRONTEND_CONFIG, validateCredentials };
}