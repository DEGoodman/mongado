# Mongado Development Log

## Project Overview
A modern blog application built with Django REST Framework and Vue.js.

## Current Status
- [x] Initial project setup
- [x] Basic Django REST Framework backend
- [x] Vue.js frontend setup
- [x] Security configuration
  - [x] Environment variable management
  - [x] Security headers configuration
  - [x] 1Password integration setup

## Next Steps
- [ ] Set up category and tag management
- [ ] Implement search functionality
- [ ] Review the UI. 
  - [ ] Dark mode toggle doesn't work, and there is dark mode/lightmode inconsistency
  - [ ] clean up and improve things in general



## Recent Changes

### 2024-04-15
- Added comprehensive security settings
- Configured environment variables for development and production
- Set up 1Password integration for secrets management
- Added security headers and HTTPS configuration

## Technical Debt
- Consider adding more comprehensive logging
- Add API documentation
- Consider implementing rate limiting

## Notes
- Keep security settings in mind when deploying to production
- Consider using PostgreSQL for production instead of SQLite
- Remember to update the README with any new features or changes

## Resources
- [Django Documentation](https://docs.djangoproject.com/)
- [Vue.js Documentation](https://vuejs.org/guide/introduction.html)
- [Django REST Framework Documentation](https://www.django-rest-framework.org/)
- [1Password CLI Documentation](https://developer.1password.com/docs/cli) 